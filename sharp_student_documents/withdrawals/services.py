import stripe
import paypalrestsdk
from django.conf import settings
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.db import IntegrityError, transaction
from django.db.models import Q
from decimal import Decimal
from datetime import date, datetime, timedelta
import logging

from .models import WithdrawalMethod, WithdrawalRequest, WithdrawalTransaction, WithdrawalSchedule
from sales.models import Wallet
from sales.utils import release_held_earnings_for_seller
try:
    from security.models import TwoFactorAuth
except ImportError:
    TwoFactorAuth = None

logger = logging.getLogger(__name__)

class WithdrawalService:
    """Service for handling withdrawal operations with commission and 2FA integration"""

    PAYOUT_DAYS = (14, 28)
    HOLD_DAYS = 14

    @staticmethod
    def hold_days() -> int:
        return int(getattr(settings, "WITHDRAWALS_HOLD_DAYS", WithdrawalService.HOLD_DAYS))

    @staticmethod
    def force_payout_day_for_testing() -> bool:
        return bool(getattr(settings, "WITHDRAWALS_TEST_FORCE_PAYOUT_DAY", False))

    @staticmethod
    def next_payout_date(today=None):
        today = today or timezone.localdate()
        if WithdrawalService.force_payout_day_for_testing():
            return today
        year = today.year
        month = today.month

        if today.day <= 14:
            return date(year, month, 14)
        if today.day <= 28:
            return date(year, month, 28)

        # next month 14th
        if month == 12:
            return date(year + 1, 1, 14)
        return date(year, month + 1, 14)
    
    @staticmethod
    def create_withdrawal_request(user, withdrawal_method, amount, payout_type='weekly'):
        """Create a new withdrawal request with automatic processing and fraud detection"""
        withdrawal_request = None
        try:
            # Release held earnings first so balance reflects the 14-day hold.
            release_held_earnings_for_seller(user, hold_days=WithdrawalService.hold_days())
             
            # Get user wallet
            wallet = Wallet.objects.get(user=user)

            if Decimal(str(getattr(wallet, "debt_balance", 0) or 0)) > 0:
                return {
                    'success': False,
                    'error': f"You have an outstanding refund debt of ${wallet.debt_balance}. Withdrawals are disabled until it is repaid from future earnings.",
                }
            
            # Validate amount
            if amount < Decimal('10.00'):
                return {
                    'success': False,
                    'error': 'Minimum withdrawal amount is $10.00'
                }
            
            if wallet.balance < amount:
                return {
                    'success': False,
                    'error': 'Insufficient balance'
                }
            
            # Calculate fees (no commission on withdrawals - commission already taken from sales)
            # No transaction fee is charged to sellers on withdrawal.
            transaction_fee = Decimal("0.00")
             
            # Net amount after transaction fee only (commission already deducted from sales)
            final_amount = amount
            
            # Instant payouts are disabled; always schedule for the next payout date.
            payout_type = "weekly"
            scheduled_for = WithdrawalService.next_payout_date()

            # Create withdrawal request
            withdrawal_request = WithdrawalRequest.objects.create(
                user=user,
                withdrawal_method=withdrawal_method,
                amount=amount,
                fee=transaction_fee,  # Only store transaction fee
                net_amount=final_amount,
                payout_type=payout_type,
                status='pending',
                scheduled_for=scheduled_for,
            )
             
            # Check if 2FA is required
            if withdrawal_request.requires_two_factor_auth():
                withdrawal_request.status = '2fa_required'
                withdrawal_request.save()
                return {
                    'success': True,
                    'withdrawal_request': withdrawal_request,
                    'requires_2fa': True,
                    'message': '2FA verification required for withdrawal',
                    'fraud_alerts': 0,
                }
             
            # Reserve funds now (prevents over-withdrawal while awaiting payout day)
            wallet.reserve_withdrawal(amount=amount, reason="Withdrawal request reserved")
            withdrawal_request.wallet_debited = True
            withdrawal_request.save(update_fields=["wallet_debited"])
             
            # Create admin notification
            from .models import AdminNotification
            AdminNotification.create_withdrawal_notification(withdrawal_request)
             
            # Always schedule for payout day.
            success = WithdrawalService._schedule_weekly_withdrawal(withdrawal_request)
             
            # Create notification for failed withdrawal if needed
            if not success and withdrawal_request.status == 'failed':
                AdminNotification.create_failed_withdrawal_notification(withdrawal_request)
            
            return {
                'success': True,
                'withdrawal_request': withdrawal_request,
                'requires_2fa': False,
                'transaction_fee': transaction_fee,
                'net_amount': final_amount,
                'fraud_alerts': 0,
            }
             
        except Exception as e:
            logger.error(f"Create withdrawal request failed: {str(e)}")
            # Best-effort rollback if we already reserved funds but failed later.
            if withdrawal_request and getattr(withdrawal_request, "wallet_debited", False):
                try:
                    WithdrawalService._release_reserved_funds(
                        withdrawal_request,
                        reason=f"Withdrawal failed: {str(e)}",
                    )
                except Exception:
                    logger.exception("Failed to rollback reserved funds for withdrawal %s", getattr(withdrawal_request, "id", None))
            return {
                'success': False,
                'error': str(e)
            }

    @staticmethod
    def auto_create_withdrawals_for_payout_day(*, today=None) -> int:
        """
        Auto-withdraw on payout days (14th & 28th).

        If enabled, this creates a withdrawal request for each seller who:
        - has a verified active withdrawal method
        - has no open withdrawal request
        - has matured (available) balance >= minimum withdrawal amount

        The request is then picked up by `process_weekly_withdrawals()` in the same run.
        """
        if not bool(getattr(settings, "WITHDRAWALS_AUTO_WITHDRAW_ON_PAYOUT_DAYS", True)):
            return 0

        today = today or timezone.localdate()
        min_amount = Decimal(str(getattr(settings, "WITHDRAWALS_MIN_WITHDRAWAL_AMOUNT", "10.00")))

        User = get_user_model()
        sellers = User.objects.filter(is_seller=True, is_active=True).only("id", "username")

        created_count = 0
        for seller in sellers.iterator():
            # Skip if there's already an open request (manual or auto).
            if WithdrawalRequest.objects.filter(
                user=seller,
                status__in=["pending", "processing", "2fa_required"],
            ).exists():
                continue

            # Prefer PayPal; fallback to any verified method.
            method = WithdrawalMethod.objects.filter(
                user=seller,
                is_active=True,
                is_verified=True,
                method_type="paypal",
            ).first()
            if not method:
                method = WithdrawalMethod.objects.filter(
                    user=seller,
                    is_active=True,
                    is_verified=True,
                ).order_by("-created_at").first()
            if not method:
                continue

            available = WithdrawalService.get_user_balance(seller)
            if available < min_amount:
                continue

            result = WithdrawalService.create_withdrawal_request(
                user=seller,
                withdrawal_method=method,
                amount=available,
                payout_type="weekly",
            )
            if result.get("success"):
                created_count += 1

        return created_count
    
    @staticmethod
    def verify_2fa_for_withdrawal(withdrawal_request, token):
        """Verify 2FA token for withdrawal"""
        try:
            if not TwoFactorAuth:
                return False, "2FA not available"
            
            two_fa = withdrawal_request.user.two_factor
            if not two_fa.is_enabled:
                return False, "2FA not enabled"
            
            if not WithdrawalService.verify_2fa_token(withdrawal_request.user, token):
                return False, "Invalid 2FA token"

            # Release held earnings and reserve funds (post-2FA)
            release_held_earnings_for_seller(withdrawal_request.user, hold_days=WithdrawalService.hold_days())
            wallet = Wallet.objects.get(user=withdrawal_request.user)
            if not withdrawal_request.wallet_debited:
                wallet.reserve_withdrawal(amount=withdrawal_request.amount, reason="Withdrawal reserved (2FA verified)")
                withdrawal_request.wallet_debited = True

            withdrawal_request.two_fa_verified = True
            withdrawal_request.status = 'pending'
            withdrawal_request.save(update_fields=["two_fa_verified", "status", "wallet_debited"])

            return True, "2FA verified successfully"
                 
        except TwoFactorAuth.DoesNotExist:
            return False, "2FA not set up"
        except Exception as e:
            logger.error(f"2FA verification failed: {str(e)}")
            return False, str(e)
    
    @staticmethod
    def process_withdrawal(withdrawal_request):
        """Process withdrawal after 2FA verification"""
        try:
            if withdrawal_request.requires_two_factor_auth() and not withdrawal_request.two_fa_verified:
                return False, "2FA verification required"

            success = WithdrawalService._schedule_weekly_withdrawal(withdrawal_request)
            return success, "Withdrawal scheduled successfully" if success else "Withdrawal scheduling failed"
            
        except Exception as e:
            logger.error(f"Process withdrawal failed: {str(e)}")
            return False, str(e)
    
    @staticmethod
    def process_instant_withdrawal(withdrawal_request):
        """Process instant withdrawal"""
        try:
            withdrawal_request.status = 'processing'
            withdrawal_request.processed_at = timezone.now()
            withdrawal_request.save()
            
            # Process based on method
            if withdrawal_request.withdrawal_method.method_type == 'stripe':
                success = WithdrawalService._process_stripe_instant(withdrawal_request)
            elif withdrawal_request.withdrawal_method.method_type == 'paypal':
                success = WithdrawalService._process_paypal_instant(withdrawal_request)
            else:
                success = False
            
            if success:
                withdrawal_request.status = 'completed'
                withdrawal_request.completed_at = timezone.now()
                # Finalize reserved funds
                if withdrawal_request.wallet_debited:
                    wallet = Wallet.objects.get(user=withdrawal_request.user)
                    wallet.finalize_reserved_withdrawal(withdrawal_request.amount)
                # Notify seller
                try:
                    from notifications.models import UserNotification
                    UserNotification.create_notification(
                        user=withdrawal_request.user, notification_type='withdrawal_completed',
                        title='Withdrawal Completed',
                        message=f'Your withdrawal of ${withdrawal_request.amount} has been completed successfully.',
                        link='/withdrawals/dashboard/'
                    )
                except Exception:
                    logger.exception("Failed to create withdrawal completed notification")
            else:
                withdrawal_request.status = 'failed'
                withdrawal_request.failure_reason = "Payment processing failed"
                # Release reserved funds back to seller
                if withdrawal_request.wallet_debited:
                    wallet = Wallet.objects.get(user=withdrawal_request.user)
                    wallet.release_reserved_withdrawal(
                        withdrawal_request.amount,
                        reason=f"Withdrawal failed: {withdrawal_request.failure_reason}",
                    )
                    withdrawal_request.wallet_debited = False
                # Notify seller
                try:
                    from notifications.models import UserNotification
                    UserNotification.create_notification(
                        user=withdrawal_request.user, notification_type='withdrawal_failed',
                        title='Withdrawal Failed',
                        message=f'Your withdrawal of ${withdrawal_request.amount} failed. Funds have been returned to your wallet.',
                        link='/withdrawals/dashboard/'
                    )
                except Exception:
                    logger.exception("Failed to create withdrawal failed notification")

            withdrawal_request.save()
            return success
             
        except Exception as e:
            logger.error(f"Instant withdrawal failed: {str(e)}")
            withdrawal_request.status = 'failed'
            withdrawal_request.failure_reason = str(e)
            if withdrawal_request.wallet_debited:
                try:
                    wallet = Wallet.objects.get(user=withdrawal_request.user)
                    wallet.release_reserved_withdrawal(
                        withdrawal_request.amount,
                        reason=f"Withdrawal failed: {withdrawal_request.failure_reason}",
                    )
                    withdrawal_request.wallet_debited = False
                except Exception:
                    logger.exception("Failed to release reserved funds for withdrawal %s", withdrawal_request.id)
            withdrawal_request.save()
            # Notify seller
            try:
                from notifications.models import UserNotification
                UserNotification.create_notification(
                    user=withdrawal_request.user, notification_type='withdrawal_failed',
                    title='Withdrawal Failed',
                    message=f'Your withdrawal of ${withdrawal_request.amount} failed due to an error. Funds have been returned to your wallet.',
                    link='/withdrawals/dashboard/'
                )
            except Exception:
                logger.exception("Failed to create withdrawal failed notification")
            return False
    
    @staticmethod
    def _process_stripe_instant(withdrawal_request):
        """Process instant Stripe transfer"""
        try:
            stripe.api_key = settings.STRIPE_SECRET_KEY
            
            # Create transfer to connected account
            transfer = stripe.Transfer.create(
                amount=int(withdrawal_request.net_amount * 100),  # Convert to cents
                currency='usd',
                destination=withdrawal_request.withdrawal_method.stripe_account_id,
                transfer_group=f"withdrawal_{withdrawal_request.id}",
                description=f"Instant withdrawal - {withdrawal_request.user.email}"
            )
            
            # Create transaction record
            transaction = WithdrawalTransaction.objects.create(
                withdrawal_request=withdrawal_request,
                transaction_id=transfer.id,
                stripe_transfer_id=transfer.id,
                status='completed',
                processed_at=timezone.now(),
                response_data=transfer.to_dict()
            )
            
            withdrawal_request.stripe_transfer_id = transfer.id
            return True
            
        except stripe.error.StripeError as e:
            logger.error(f"Stripe instant transfer failed: {str(e)}")
            withdrawal_request.failure_reason = f"Stripe error: {str(e)}"
            return False
    
    @staticmethod
    def _process_paypal_instant(withdrawal_request):
        """Process instant PayPal payout"""
        try:
            # Generate unique batch ID to avoid duplicates
            import uuid
            unique_id = str(uuid.uuid4())[:8]
            sender_batch_id = f"withdrawal_{withdrawal_request.id}_{unique_id}"
            
            payout = paypalrestsdk.Payout({
                "sender_batch_header": {
                    "sender_batch_id": sender_batch_id,
                    "email_subject": "You have a withdrawal from SharpDocs"
                },
                "items": [{
                    "recipient_type": "EMAIL",
                    "receiver": withdrawal_request.withdrawal_method.paypal_email,
                    "amount": {
                        "value": str(withdrawal_request.net_amount),
                        "currency": "USD"
                    },
                    "note": "Instant withdrawal from SharpDocs",
                    "sender_item_id": f"item_{withdrawal_request.id}_{unique_id}"
                }]
            })
            
            if payout.create():
                # Create transaction record
                transaction = WithdrawalTransaction.objects.create(
                    withdrawal_request=withdrawal_request,
                    transaction_id=payout.batch_header.payout_batch_id,
                    paypal_payout_item_id=payout.items[0].payout_item_id,
                    status='completed',
                    processed_at=timezone.now(),
                    response_data=payout.to_dict()
                )
                
                withdrawal_request.paypal_payout_id = payout.batch_header.payout_batch_id
                return True
            else:
                withdrawal_request.failure_reason = f"PayPal error: {payout.error}"
                return False
                
        except Exception as e:
            error_text = str(e)
            if "invalid_client" in error_text or "Client Authentication failed" in error_text:
                withdrawal_request.failure_reason = (
                    "PayPal credentials invalid. Check PAYPAL_MODE, PAYPAL_CLIENT_ID, and PAYPAL_CLIENT_SECRET."
                )
            elif "WinError 10060" in error_text or "Timeout" in error_text:
                withdrawal_request.failure_reason = (
                    "Network timeout connecting to PayPal. Check your internet/firewall and try again."
                )
            else:
                withdrawal_request.failure_reason = f"PayPal error: {error_text}"

            logger.error(f"PayPal instant payout failed: {withdrawal_request.failure_reason}")
            return False
    
    @staticmethod
    def _schedule_weekly_withdrawal(withdrawal_request):
        """Schedule withdrawal for the next payout date (14th/28th)."""
        try:
            if not withdrawal_request.scheduled_for:
                withdrawal_request.scheduled_for = WithdrawalService.next_payout_date()
                withdrawal_request.save(update_fields=["scheduled_for"])

            # Only normalize to pending when the request is actually pending.
            # Never overwrite a final state (failed/cancelled/completed) or a 2FA gating state.
            if withdrawal_request.status == "pending":
                withdrawal_request.save(update_fields=["status"])
            return True
               
        except Exception as e:
            logger.error(f"Weekly withdrawal processing failed: {str(e)}")
            withdrawal_request.status = 'failed'
            withdrawal_request.failure_reason = f"Processing error: {str(e)}"
            withdrawal_request.save()
            # If we already reserved funds, release them so the seller can re-request.
            if getattr(withdrawal_request, "wallet_debited", False):
                try:
                    WithdrawalService._release_reserved_funds(
                        withdrawal_request,
                        reason=f"Withdrawal failed: {withdrawal_request.failure_reason}",
                    )
                except Exception:
                    logger.exception("Failed to release reserved funds for withdrawal %s", getattr(withdrawal_request, "id", None))
            return False
    
    @staticmethod
    def process_weekly_withdrawals(*, force: bool = False, ignore_scheduled_date: bool = False, today=None):
        """
        Process all pending scheduled withdrawals (runs on 14th and 28th).

        Testing helpers:
        - force=True: process regardless of payout day.
        - ignore_scheduled_date=True: include pending withdrawals even if scheduled_for is in the future.
        - today=<date>: deterministic date for tests.
        """
        try:
            today = today or timezone.localdate()
            if (
                today.day not in WithdrawalService.PAYOUT_DAYS
                and not WithdrawalService.force_payout_day_for_testing()
                and not force
            ):
                logger.info("Not a payout day (%s). Skipping scheduled withdrawals.", today)
                return

            # Auto-withdraw step: create requests for sellers with matured available balances.
            try:
                created = WithdrawalService.auto_create_withdrawals_for_payout_day(today=today)
                if created:
                    logger.info("Auto-created %s withdrawal request(s) for payout day %s.", created, today)
            except Exception:
                logger.exception("Auto-withdraw creation step failed; continuing with existing pending withdrawals.")
               
            # Get pending weekly withdrawals
            base_qs = WithdrawalRequest.objects.filter(
                payout_type='weekly',
                status='pending',
            ).select_related('user', 'withdrawal_method')

            if ignore_scheduled_date or WithdrawalService.force_payout_day_for_testing():
                pending_withdrawals = list(base_qs)
            else:
                pending_withdrawals = list(
                    base_qs.filter(
                        Q(scheduled_for__isnull=True) | Q(scheduled_for__lte=today)
                    )
                )

            if (force or ignore_scheduled_date or WithdrawalService.force_payout_day_for_testing()) and pending_withdrawals:
                # Keep audit consistent: anything we force-process is treated as scheduled for 'today'.
                for w in pending_withdrawals:
                    if not w.scheduled_for or w.scheduled_for > today:
                        w.scheduled_for = today
                        w.save(update_fields=["scheduled_for"])

            # Filter in Python for 2FA requirement (model method hits related objects)
            pending_withdrawals = [w for w in pending_withdrawals if (not w.requires_two_factor_auth() or w.two_fa_verified)]
            if not pending_withdrawals:
                logger.info("No pending scheduled withdrawals to process")
                return

            # Ensure wallet holds have been released before processing payouts
            for withdrawal in pending_withdrawals:
                release_held_earnings_for_seller(withdrawal.user, hold_days=WithdrawalService.hold_days())

            # Process by payment method
            stripe_withdrawals = [w for w in pending_withdrawals if w.withdrawal_method and w.withdrawal_method.method_type == 'stripe']
            paypal_withdrawals = [w for w in pending_withdrawals if w.withdrawal_method and w.withdrawal_method.method_type == 'paypal']

            if stripe_withdrawals:
                WithdrawalService._process_stripe_batch(stripe_withdrawals)
            if paypal_withdrawals:
                WithdrawalService._process_paypal_batch(paypal_withdrawals)

            logger.info("Scheduled withdrawal processing completed")
            return
        except Exception as e:
            logger.exception("Weekly withdrawal processing failed: %s", str(e))
            # In testing/admin forced runs, surface the error so the command output is accurate.
            if force or ignore_scheduled_date or WithdrawalService.force_payout_day_for_testing():
                raise
    
    @staticmethod
    def _process_stripe_batch(withdrawals):
        """Process batch of Stripe withdrawals"""
        try:
            stripe.api_key = settings.STRIPE_SECRET_KEY
              
            for withdrawal in withdrawals:
                try:
                    withdrawal.status = 'processing'
                    withdrawal.processed_at = timezone.now()
                    withdrawal.save()
                     
                    transfer = stripe.Transfer.create(
                        amount=int(withdrawal.net_amount * 100),
                        currency='usd',
                        destination=withdrawal.withdrawal_method.stripe_account_id,
                        transfer_group=f"weekly_{timezone.now().strftime('%Y%m%d')}",
                        description=f"Scheduled withdrawal - {withdrawal.user.email}"
                    )
                     
                    # Create transaction record
                    WithdrawalTransaction.objects.create(
                        withdrawal_request=withdrawal,
                        transaction_id=transfer.id,
                        stripe_transfer_id=transfer.id,
                        status='completed',
                        processed_at=timezone.now(),
                        response_data=transfer.to_dict()
                    )
                     
                    withdrawal.status = 'completed'
                    withdrawal.completed_at = timezone.now()
                    withdrawal.stripe_transfer_id = transfer.id
                    withdrawal.save()

                    if withdrawal.wallet_debited:
                        wallet = Wallet.objects.get(user=withdrawal.user)
                        finalize_amount = min(Decimal(withdrawal.amount), Decimal(wallet.reserved_balance))
                        if finalize_amount > 0:
                            wallet.finalize_reserved_withdrawal(finalize_amount)
                        withdrawal.wallet_debited = False
                        withdrawal.save(update_fields=["wallet_debited"])
                      
                except stripe.error.StripeError as e:
                    logger.error(f"Stripe transfer failed for {withdrawal.id}: {str(e)}")
                    withdrawal.status = 'failed'
                    withdrawal.failure_reason = f"Stripe error: {str(e)}"
                    withdrawal.save()

                    if withdrawal.wallet_debited:
                        wallet = Wallet.objects.get(user=withdrawal.user)
                        wallet.release_reserved_withdrawal(withdrawal.amount, reason=f"Withdrawal failed: {withdrawal.failure_reason}")
                        withdrawal.wallet_debited = False
                        withdrawal.save(update_fields=["wallet_debited"])
                      
        except Exception as e:
            logger.error(f"Stripe batch processing failed: {str(e)}")
    
    @staticmethod
    def _process_paypal_batch(withdrawals):
        """Process batch of PayPal withdrawals"""
        try:
            # Create payout items
            payout_items = []
            for withdrawal in withdrawals:
                withdrawal.status = 'processing'
                withdrawal.processed_at = timezone.now()
                withdrawal.save()
                 
                payout_items.append({
                    "recipient_type": "EMAIL",
                    "receiver": withdrawal.withdrawal_method.paypal_email,
                    "amount": {
                        "value": str(withdrawal.net_amount),
                        "currency": "USD"
                    },
                    "note": "Scheduled withdrawal from SharpDocs",
                    "sender_item_id": f"item_{withdrawal.id}"
                })
            
            # Create batch payout
            payout = paypalrestsdk.Payout({
                "sender_batch_header": {
                    "sender_batch_id": f"scheduled_{timezone.now().strftime('%Y%m%d_%H%M%S')}",
                    "email_subject": "Your withdrawal from SharpDocs"
                },
                "items": payout_items
            })
            
            if payout.create():
                # Update withdrawals with transaction IDs
                for i, withdrawal in enumerate(withdrawals):
                    try:
                        payout_item_id = None
                        try:
                            payout_item_id = payout.items[i].payout_item_id
                        except Exception:
                            payout_item_id = None

                        # `transaction_id` must be unique per withdrawal (batch id is shared).
                        transaction_id = payout_item_id or f"{payout.batch_header.payout_batch_id}:{withdrawal.id}"

                        # Create transaction record
                        try:
                            with transaction.atomic():
                                tx, created = WithdrawalTransaction.objects.get_or_create(
                                    transaction_id=transaction_id,
                                    defaults={
                                        "withdrawal_request": withdrawal,
                                        "paypal_payout_item_id": payout_item_id,
                                        "status": "completed",
                                        "processed_at": timezone.now(),
                                        "response_data": payout.to_dict(),
                                    },
                                )
                                if not created:
                                    if tx.withdrawal_request_id != withdrawal.id:
                                        raise IntegrityError("transaction_id already used for another withdrawal")
                                    tx.status = "completed"
                                    tx.processed_at = timezone.now()
                                    tx.response_data = payout.to_dict()
                                    if payout_item_id and not tx.paypal_payout_item_id:
                                        tx.paypal_payout_item_id = payout_item_id
                                    tx.save(update_fields=["status", "processed_at", "response_data", "paypal_payout_item_id"])
                        except IntegrityError:
                            # If re-running the job, the transaction may already exist; treat as idempotent.
                            tx = WithdrawalTransaction.objects.filter(transaction_id=transaction_id).first()
                            if not tx or tx.withdrawal_request_id != withdrawal.id:
                                raise

                        withdrawal.status = 'completed'
                        withdrawal.completed_at = timezone.now()
                        withdrawal.paypal_payout_id = payout.batch_header.payout_batch_id
                        withdrawal.save()

                        if withdrawal.wallet_debited:
                            wallet = Wallet.objects.get(user=withdrawal.user)
                            finalize_amount = min(Decimal(withdrawal.amount), Decimal(wallet.reserved_balance))
                            if finalize_amount > 0:
                                wallet.finalize_reserved_withdrawal(finalize_amount)
                            withdrawal.wallet_debited = False
                            withdrawal.save(update_fields=["wallet_debited"])
                          
                    except Exception as e:
                        logger.error(f"Failed to update withdrawal {withdrawal.id}: {str(e)}")
                        withdrawal.status = 'failed'
                        withdrawal.failure_reason = f"Update error: {str(e)}"
                        withdrawal.save()
                        if withdrawal.wallet_debited:
                            try:
                                wallet = Wallet.objects.get(user=withdrawal.user)
                                wallet.release_reserved_withdrawal(
                                    withdrawal.amount,
                                    reason=f"Withdrawal failed: {withdrawal.failure_reason}",
                                )
                                withdrawal.wallet_debited = False
                                withdrawal.save(update_fields=["wallet_debited"])
                            except Exception:
                                logger.exception("Failed to release reserved funds for withdrawal %s", withdrawal.id)
            else:
                logger.error(f"PayPal batch payout failed: {payout.error}")
                for withdrawal in withdrawals:
                    withdrawal.status = 'failed'
                    withdrawal.failure_reason = f"PayPal error: {payout.error}"
                    withdrawal.save()

                    if withdrawal.wallet_debited:
                        wallet = Wallet.objects.get(user=withdrawal.user)
                        wallet.release_reserved_withdrawal(withdrawal.amount, reason=f"Withdrawal failed: {withdrawal.failure_reason}")
                        withdrawal.wallet_debited = False
                        withdrawal.save(update_fields=["wallet_debited"])
                      
        except Exception as e:
            error_text = str(e)
            logger.error(f"PayPal batch processing failed: {error_text}")
            for withdrawal in withdrawals:
                withdrawal.status = 'failed'
                if "invalid_client" in error_text or "Client Authentication failed" in error_text:
                    withdrawal.failure_reason = (
                        "PayPal credentials invalid. Check PAYPAL_MODE, PAYPAL_CLIENT_ID, and PAYPAL_CLIENT_SECRET."
                    )
                elif "WinError 10060" in error_text or "Timeout" in error_text:
                    withdrawal.failure_reason = (
                        "Network timeout connecting to PayPal. Check your internet/firewall and try again."
                    )
                else:
                    withdrawal.failure_reason = f"Batch error: {error_text}"
                withdrawal.save()

                if withdrawal.wallet_debited:
                    try:
                        wallet = Wallet.objects.get(user=withdrawal.user)
                        wallet.release_reserved_withdrawal(withdrawal.amount, reason=f"Withdrawal failed: {withdrawal.failure_reason}")
                        withdrawal.wallet_debited = False
                        withdrawal.save(update_fields=["wallet_debited"])
                    except Exception:
                        logger.exception("Failed to release reserved funds for withdrawal %s", withdrawal.id)
    
    @staticmethod
    def verify_2fa_token(user, token):
        """Verify 2FA token for withdrawal"""
        try:
            two_fa = user.two_factor
            if not two_fa.is_enabled:
                return True
            
            # Check TOTP token
            if two_fa.verify_token(token):
                two_fa.last_used = timezone.now()
                two_fa.save()
                return True
            
            # Check backup codes
            if two_fa.verify_backup_code(token):
                two_fa.last_used = timezone.now()
                two_fa.save()
                return True
            
            return False
            
        except TwoFactorAuth.DoesNotExist:
            return True
    
    @staticmethod
    def get_user_balance(user):
        """Get user's available balance for withdrawal"""
        from django.db.models import Sum

        try:
            release_held_earnings_for_seller(user, hold_days=WithdrawalService.hold_days())
            with transaction.atomic():
                wallet = Wallet.objects.select_for_update().get(user=user)

                # Self-heal reserved funds in a deterministic way (no per-row loop):
                # - finalize reserved funds for any completed withdrawals still marked debited
                # - release reserved funds for any failed/cancelled withdrawals still marked debited
                debited_qs = WithdrawalRequest.objects.filter(user=user, wallet_debited=True)

                completed_qs = debited_qs.filter(status="completed")
                completed_total = completed_qs.aggregate(total=Sum("amount"))["total"] or Decimal("0.00")
                if completed_total > 0 and wallet.reserved_balance > 0:
                    wallet.finalize_reserved_withdrawal(min(Decimal(completed_total), Decimal(wallet.reserved_balance)))
                if completed_total > 0:
                    # Always clear the flag to avoid leaving completed withdrawals "stuck debited"
                    # even if reserved funds were already finalized by the payout processor.
                    completed_qs.update(wallet_debited=False)

                failed_qs = debited_qs.filter(status__in=["failed", "cancelled"])
                failed_total = failed_qs.aggregate(total=Sum("amount"))["total"] or Decimal("0.00")
                if failed_total > 0:
                    release_amount = min(Decimal(failed_total), Decimal(wallet.reserved_balance))
                    if release_amount > 0:
                        wallet.release_reserved_withdrawal(
                            release_amount,
                            reason="Withdrawal failed/cancelled (reserved funds released)",
                        )
                    failed_qs.update(wallet_debited=False)

                # Fallback: if there is still reserved money but no active *debited* withdrawals,
                # release the remainder to avoid trapping funds.
                has_active_debited = WithdrawalRequest.objects.filter(
                    user=user,
                    wallet_debited=True,
                    status__in=["pending", "processing", "2fa_required"],
                ).exists()
                if not has_active_debited and wallet.reserved_balance > 0:
                    logger.warning(
                        "Releasing orphaned reserved funds for user %s: %s",
                        getattr(user, "username", user),
                        wallet.reserved_balance,
                    )
                    wallet.release_reserved_withdrawal(
                        wallet.reserved_balance,
                        reason="Reserved funds released (no active debited withdrawals)",
                    )
                    WithdrawalRequest.objects.filter(user=user, wallet_debited=True).update(wallet_debited=False)

                wallet.refresh_from_db(fields=["balance", "reserved_balance"])
                return wallet.balance
        except Wallet.DoesNotExist:
            return Decimal('0.00')

    @staticmethod
    def _release_reserved_funds(withdrawal_request, *, reason: str, wallet=None):
        """
        Release reserved funds for a withdrawal safely.

        Uses `min(amount, wallet.reserved_balance)` to avoid over-crediting if data is inconsistent.
        """
        if not getattr(withdrawal_request, "wallet_debited", False):
            return

        wallet = wallet or Wallet.objects.get(user=withdrawal_request.user)
        release_amount = min(Decimal(withdrawal_request.amount), Decimal(wallet.reserved_balance))
        if release_amount <= 0:
            withdrawal_request.wallet_debited = False
            withdrawal_request.save(update_fields=["wallet_debited"])
            logger.warning(
                "Withdrawal %s marked debited but wallet has no reserved funds; cleared wallet_debited flag.",
                getattr(withdrawal_request, "id", None),
            )
            return

        wallet.release_reserved_withdrawal(release_amount, reason=reason)
        withdrawal_request.wallet_debited = False
        withdrawal_request.save(update_fields=["wallet_debited"])
    
    @staticmethod
    def can_withdraw(user, amount):
        """Check if user can withdraw specified amount"""
        min_amount = Decimal(str(getattr(settings, "WITHDRAWALS_MIN_WITHDRAWAL_AMOUNT", "10.00")))
        balance = WithdrawalService.get_user_balance(user)
         
        # Check minimum withdrawal amount
        if amount < min_amount:
            return False, f"Minimum withdrawal amount is ${min_amount}"
         
        # Check sufficient balance / debt restrictions
        if amount > balance:
            try:
                wallet = Wallet.objects.get(user=user)
            except Exception:
                wallet = None

            try:
                debt_amount = Decimal(str(getattr(wallet, "debt_balance", 0) or 0)) if wallet else Decimal("0.00")
                if debt_amount > 0:
                    return (
                        False,
                        f"Withdrawals are disabled until refund debt is repaid. Outstanding debt: ${debt_amount}.",
                    )
            except Exception:
                pass

            # If user has held funds, explain the 14-day maturity wait.
            try:
                held_amount = Decimal(str(getattr(wallet, "pending_balance", 0) or 0)) if wallet else Decimal("0.00")
                if held_amount > 0:
                    from datetime import timedelta
                    from django.utils import timezone
                    from sales.models import Sale

                    hold_days = WithdrawalService.hold_days()
                    oldest_held = (
                        Sale.objects.filter(seller=user, wallet_released_at__isnull=True)
                        .order_by("created_at")
                        .only("created_at")
                        .first()
                    )
                    if oldest_held and oldest_held.created_at:
                        maturity_date = (oldest_held.created_at + timedelta(days=hold_days)).date()
                        days_until = (maturity_date - timezone.localdate()).days
                        if days_until > 0:
                            return (
                                False,
                                f"Insufficient withdrawable balance. You have ${held_amount} held. "
                                f"Next funds mature in {days_until} day(s) (on {maturity_date}).",
                            )
            except Exception:
                pass

            return False, "Insufficient balance"
         
        return True, "Withdrawal allowed"
