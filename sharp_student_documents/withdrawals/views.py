from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse, HttpResponse
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_exempt
from django.utils import timezone
from django.db.models import Sum, Q
from django.core.paginator import Paginator
from django.conf import settings
from decimal import Decimal
import json
import logging
import stripe
import pyotp

from .models import WithdrawalMethod, WithdrawalRequest, WithdrawalSchedule
try:
    from security.models import TwoFactorAuth
except ImportError:
    TwoFactorAuth = None
from .services import WithdrawalService
from documents.models import Document, Order
from sales.models import Sale, Wallet
from sharp_student_documents.paypal import verify_paypal_webhook_signature

logger = logging.getLogger(__name__)

def _seller_2fa_enabled(user) -> bool:
    if not TwoFactorAuth:
        return False
    try:
        two_fa = user.two_factor
        return bool(two_fa and two_fa.is_enabled)
    except TwoFactorAuth.DoesNotExist:
        return False

def _require_2fa_for_payout_method() -> bool:
    """
    Feature flag: require 2FA before sellers can add/change payout methods.
    Keep this disabled during early testing.
    """
    return bool(getattr(settings, "WITHDRAWALS_REQUIRE_2FA_FOR_PAYOUT_METHOD", False))

@login_required
def withdrawal_dashboard(request):
    """
    Main withdrawal dashboard
    """
    # Get user's withdrawal methods
    withdrawal_methods = WithdrawalMethod.objects.filter(user=request.user, is_active=True)
    
    # Get user's balance
    balance = WithdrawalService.get_user_balance(request.user)

    # Wallet details (available + held + reserved)
    wallet, _created = Wallet.objects.get_or_create(user=request.user)
    
    # Get recent withdrawals
    recent_withdrawals = WithdrawalRequest.objects.filter(
        user=request.user
    ).order_by('-requested_at')[:10]
    
    # Get 2FA status
    try:
        two_fa = request.user.two_factor
    except TwoFactorAuth.DoesNotExist:
        two_fa = None
    
    # Get withdrawal statistics
    total_withdrawn = WithdrawalRequest.objects.filter(
        user=request.user,
        status='completed'
    ).aggregate(total=Sum('amount'))['total'] or 0
    
    pending_withdrawals = WithdrawalRequest.objects.filter(
        user=request.user,
        status__in=['pending', 'processing', '2fa_required']
    ).aggregate(total=Sum('amount'))['total'] or 0

    total_sold = Order.objects.filter(
        document__seller=request.user,
        status="paid",
    ).aggregate(total=Sum("amount_paid"))["total"] or 0
    
    context = {
        'withdrawal_methods': withdrawal_methods,
        'balance': balance,
        'pending_balance': wallet.pending_balance,
        'reserved_balance': wallet.reserved_balance,
        'recent_withdrawals': recent_withdrawals,
        'two_fa': two_fa,
        'total_withdrawn': total_withdrawn,
        'pending_withdrawals': pending_withdrawals,
        'total_sold': total_sold,
    }
    
    return render(request, 'withdrawals/dashboard.html', context)

@login_required
def setup_withdrawal_method(request):
    """
    Setup new withdrawal method
    """
    if not getattr(request.user, "is_seller", False):
        messages.error(request, "Only sellers can add withdrawal methods.")
        return redirect("home")

    if _require_2fa_for_payout_method() and not _seller_2fa_enabled(request.user):
        messages.error(request, "Enable 2FA before adding or changing a payout method.")
        return redirect("withdrawals:dashboard")

    if request.method == 'POST':
        method_type = request.POST.get('method_type')
        
        if method_type == 'stripe':
            # Stripe temporarily disabled
            messages.warning(request, 
                'Stripe Connect is temporarily unavailable while we upgrade our payment infrastructure. '
                'Please use PayPal for now. We\'ll notify you when Stripe is available again.'
            )
            return redirect('withdrawals:setup_method')
        elif method_type == 'paypal':
            return setup_paypal_method(request)
        elif method_type == 'bank':
            messages.info(request, 'Direct bank transfers are coming soon! Please use PayPal for now.')
            return redirect('withdrawals:setup_method')
        else:
            messages.error(request, 'Invalid withdrawal method selected.')
            return redirect('withdrawals:setup_method')
    
    return render(request, 'withdrawals/setup_method.html')

@login_required
def setup_stripe_connect(request):
    """
    Setup Stripe Connect account
    """
    if not getattr(request.user, "is_seller", False):
        messages.error(request, "Only sellers can add withdrawal methods.")
        return redirect("home")

    if _require_2fa_for_payout_method() and not _seller_2fa_enabled(request.user):
        messages.error(request, "Enable 2FA before adding or changing a payout method.")
        return redirect("withdrawals:dashboard")

    try:
        stripe.api_key = settings.STRIPE_SECRET_KEY
        
        # First, check if this is a Connect-enabled account
        try:
            # Test if we can create Express accounts (Connect feature)
            test_account = stripe.Account.create(
                type='express',
                country='US',
                email=request.user.email,
                capabilities={
                    'card_payments': {'requested': True},
                    'transfers': {'requested': True},
                },
                business_type='individual',
            )
            
            # If successful, delete the test account
            stripe.Account.delete(test_account.id)
            
        except stripe.error.StripeError as e:
            if "signed up for Connect" in str(e):
                messages.error(request, 
                    'This Stripe account is not configured for Connect. '
                    'Please sign up for Stripe Connect at https://stripe.com/docs/connect '
                    'and use a Connect-enabled account.'
                )
                return redirect('withdrawals:setup_method')
            else:
                # Some other Stripe error
                messages.error(request, f'Stripe configuration error: {str(e)}')
                return redirect('withdrawals:setup_method')
        
        # Create actual Stripe Express account for user
        account = stripe.Account.create(
            type='express',
            country='US',
            email=request.user.email,
            capabilities={
                'card_payments': {'requested': True},
                'transfers': {'requested': True},
            },
            business_type='individual',
        )
        
        # Create account link for onboarding
        account_link = stripe.AccountLink.create(
            account=account.id,
            refresh_url=request.build_absolute_uri('/withdrawals/stripe/refresh/'),
            return_url=request.build_absolute_uri('/withdrawals/stripe/return/'),
            type='account_onboarding',
        )
        
        # Save withdrawal method
        withdrawal_method = WithdrawalMethod.objects.create(
            user=request.user,
            method_type='stripe',
            stripe_account_id=account.id,
            is_verified=False
        )
        
        # Redirect to Stripe onboarding
        return redirect(account_link.url)
        
    except stripe.error.StripeError as e:
        messages.error(request, f'Stripe Connect error: {str(e)}')
        return redirect('withdrawals:setup_method')
    except Exception as e:
        messages.error(request, f'Failed to setup Stripe Connect: {str(e)}')
        return redirect('withdrawals:setup_method')

@login_required
def stripe_return(request):
    """
    Handle return from Stripe onboarding
    """
    if not getattr(request.user, "is_seller", False):
        messages.error(request, "Only sellers can add withdrawal methods.")
        return redirect("home")

    account_id = request.GET.get('account')
    
    try:
        withdrawal_method = WithdrawalMethod.objects.get(
            user=request.user,
            stripe_account_id=account_id
        )
        
        # Check account status
        stripe.api_key = settings.STRIPE_SECRET_KEY
        account = stripe.Account.retrieve(account_id)
        
        if account.charges_enabled:
            withdrawal_method.is_verified = True
            messages.success(request, 'Stripe Connect account successfully linked!')
        else:
            messages.warning(request, 'Stripe Connect account setup incomplete. Please complete onboarding.')
        
        withdrawal_method.save()
        
    except Exception as e:
        messages.error(request, f'Failed to verify Stripe account: {str(e)}')
    
    return redirect('withdrawals:dashboard')

@login_required
def setup_paypal_method(request):
    """
    Setup PayPal withdrawal method
    """
    if not getattr(request.user, "is_seller", False):
        messages.error(request, "Only sellers can add withdrawal methods.")
        return redirect("home")

    if _require_2fa_for_payout_method() and not _seller_2fa_enabled(request.user):
        messages.error(request, "Enable 2FA before adding or changing a payout method.")
        return redirect("withdrawals:dashboard")

    if request.method == 'POST':
        paypal_email = request.POST.get('paypal_email')
        
        if not paypal_email:
            messages.error(request, 'PayPal email is required.')
            return render(request, 'withdrawals/setup_paypal.html')
        
        # Check if PayPal method already exists for this user
        existing_method = WithdrawalMethod.objects.filter(
            user=request.user,
            method_type='paypal',
            paypal_email=paypal_email
        ).first()
        
        if existing_method:
            if existing_method.is_verified:
                messages.info(request, 'This PayPal account is already verified and active.')
            else:
                messages.info(request, 'This PayPal account is already added. Verification in progress.')
            return redirect('withdrawals:dashboard')
        
        from .paypal_verification import validate_paypal_email, send_paypal_verification_email

        # Create withdrawal method
        withdrawal_method = WithdrawalMethod.objects.create(
            user=request.user,
            method_type='paypal',
            paypal_email=paypal_email,
            is_verified=False,
            is_active=True
        )

        # Platforms generally cannot verify a seller's PayPal email via API.
        # We validate syntax only and confirm the setup through the account owner's email.
        is_valid, verification_message = validate_paypal_email(paypal_email)
        if not is_valid:
            withdrawal_method.delete()
            messages.error(request, verification_message)
            return render(request, 'withdrawals/setup_paypal.html')

        if request.user.email:
            email_sent = send_paypal_verification_email(request.user, paypal_email, request=request)
            if email_sent:
                messages.success(request, 'PayPal account added. Check your email to verify and activate it for withdrawals.')
            else:
                messages.warning(request, 'PayPal account was added, but the verification email could not be sent right now.')
        else:
            messages.warning(request, 'PayPal account was added, but your user account has no email address for verification.')
        
        return redirect('withdrawals:dashboard')
    
    return render(request, 'withdrawals/setup_paypal.html')

@login_required
def verify_paypal_account(request, user_id):
    """
    Verify PayPal account from email link
    """
    if request.user.id != user_id:
        messages.error(request, 'Invalid verification link.')
        return redirect('withdrawals:dashboard')
    
    # Get the user's PayPal withdrawal method
    withdrawal_method = WithdrawalMethod.objects.filter(
        user=request.user,
        method_type='paypal',
        is_verified=False
    ).first()
    
    if not withdrawal_method:
        messages.info(request, 'No pending PayPal verification found.')
        return redirect('withdrawals:dashboard')
    
    withdrawal_method.is_verified = True
    withdrawal_method.paypal_verified = True
    withdrawal_method.save(update_fields=["is_verified", "paypal_verified"])
    messages.success(request, f'PayPal account ({withdrawal_method.paypal_email}) activated successfully!')
    
    return redirect('withdrawals:dashboard')

@login_required
@require_POST
def verify_paypal_method_ajax(request, method_id):
    """
    AJAX endpoint to verify PayPal method
    """
    if request.method != 'POST':
        return JsonResponse({'success': False, 'message': 'Invalid request method'})

    if _require_2fa_for_payout_method() and not _seller_2fa_enabled(request.user):
        return JsonResponse({'success': False, 'message': 'Enable 2FA before changing payout methods.'}, status=403)
    
    try:
        withdrawal_method = WithdrawalMethod.objects.get(
            id=method_id,
            user=request.user,
            method_type='paypal'
        )
        
        if withdrawal_method.is_verified:
            return JsonResponse({'success': False, 'message': 'PayPal account already verified'})
        
        # Auto-verify for testing purposes
        from .paypal_verification import auto_verify_paypal_account
        auto_verify_paypal_account(withdrawal_method)
        
        return JsonResponse({
            'success': True, 
            'message': f'PayPal account ({withdrawal_method.paypal_email}) verified successfully!'
        })
        
    except WithdrawalMethod.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'PayPal method not found'})
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)})

@login_required
def request_withdrawal(request):
    """
    Request a withdrawal
    """
    if not getattr(request.user, "is_seller", False):
        messages.error(request, "Only sellers can request withdrawals.")
        return redirect("home")

    # Compute a hold/maturity notice for sellers who have held funds but no withdrawable balance.
    withdrawal_hold_notice = None
    try:
        from django.conf import settings
        from datetime import timedelta
        from sales.models import Wallet, Sale

        wallet, _ = Wallet.objects.get_or_create(user=request.user)
        min_amount = Decimal(str(getattr(settings, "WITHDRAWALS_MIN_WITHDRAWAL_AMOUNT", "10.00")))
        hold_days = WithdrawalService.hold_days()

        available_balance = WithdrawalService.get_user_balance(request.user)
        held_amount = Decimal(str(wallet.pending_balance or 0))

        if available_balance < min_amount and held_amount > 0:
            oldest_held = (
                Sale.objects.filter(seller=request.user, wallet_released_at__isnull=True)
                .order_by("created_at")
                .only("created_at")
                .first()
            )
            if oldest_held and oldest_held.created_at:
                maturity_date = (oldest_held.created_at + timedelta(days=hold_days)).date()
                days_until = (maturity_date - timezone.localdate()).days
                if days_until > 0:
                    withdrawal_hold_notice = (
                        f"You have ${held_amount} held. You can withdraw after the {hold_days}-day holding period. "
                        f"Next funds mature in {days_until} day(s) (on {maturity_date})."
                    )
                else:
                    withdrawal_hold_notice = (
                        f"You have ${held_amount} held. Your funds should mature soon; refresh to release matured funds."
                    )
    except Exception:
        withdrawal_hold_notice = None

    # Get user's withdrawal methods
    withdrawal_methods = WithdrawalMethod.objects.filter(
        user=request.user,
        is_active=True,
        is_verified=True
    )
    
    if not withdrawal_methods.exists():
        messages.warning(request, 'Please add a withdrawal method first.')
        return redirect('withdrawals:setup_method')
    
    if request.method == 'POST':
        method_id = request.POST.get('withdrawal_method')
        amount = Decimal(request.POST.get('amount'))
        payout_type = request.POST.get('payout_type', 'weekly')
        
        # Validate withdrawal
        withdrawal_method = get_object_or_404(WithdrawalMethod, id=method_id, user=request.user)
        can_withdraw, message = WithdrawalService.can_withdraw(request.user, amount)
        
        if not can_withdraw:
            messages.error(request, message)
            return render(request, 'withdrawals/request_withdrawal.html', {
                'withdrawal_methods': withdrawal_methods,
                'balance': WithdrawalService.get_user_balance(request.user),
                'withdrawal_hold_notice': withdrawal_hold_notice,
            })
        
        # Create withdrawal request using service
        result = WithdrawalService.create_withdrawal_request(
            user=request.user,
            withdrawal_method=withdrawal_method,
            amount=amount,
            payout_type=payout_type
        )
        
        if not result['success']:
            messages.error(request, result['error'])
            return render(request, 'withdrawals/request_withdrawal.html', {
                'withdrawal_methods': withdrawal_methods,
                'balance': WithdrawalService.get_user_balance(request.user),
                'withdrawal_hold_notice': withdrawal_hold_notice,
            })
        
        withdrawal_request = result['withdrawal_request']
         
        # Check if 2FA is required
        if result.get("requires_2fa") or withdrawal_request.status == "2fa_required":
            messages.info(request, 'Please complete 2FA verification to process this withdrawal.')
            return redirect('withdrawals:verify_2fa', withdrawal_id=withdrawal_request.id)

        if withdrawal_request.status == "completed":
            messages.success(request, "Instant withdrawal processed successfully!")
        elif withdrawal_request.payout_type == "weekly":
            scheduled_for = getattr(withdrawal_request, "scheduled_for", None)
            if scheduled_for:
                messages.success(request, f"Withdrawal scheduled for {scheduled_for}.")
            else:
                messages.success(request, "Withdrawal scheduled for the next payout date.")
        else:
            messages.success(request, "Withdrawal request submitted.")

        return redirect('withdrawals:dashboard')
    
    return render(request, 'withdrawals/request_withdrawal.html', {
        'withdrawal_methods': withdrawal_methods,
        'balance': WithdrawalService.get_user_balance(request.user),
        'withdrawal_hold_notice': withdrawal_hold_notice,
    })

@login_required
def verify_2fa(request, withdrawal_id):
    """
    Verify 2FA for withdrawal
    """
    withdrawal_request = get_object_or_404(
        WithdrawalRequest,
        id=withdrawal_id,
        user=request.user
    )
    
    if request.method == 'POST':
        token = request.POST.get('2fa_token')

        ok, message = WithdrawalService.verify_2fa_for_withdrawal(withdrawal_request, token)
        if ok:
            success, _msg = WithdrawalService.process_withdrawal(withdrawal_request)
            withdrawal_request.refresh_from_db()

            if withdrawal_request.status == "completed":
                messages.success(request, "2FA verified! Instant withdrawal processed.")
            elif withdrawal_request.payout_type == "weekly":
                if withdrawal_request.scheduled_for:
                    messages.success(request, f"2FA verified! Withdrawal scheduled for {withdrawal_request.scheduled_for}.")
                else:
                    messages.success(request, "2FA verified! Withdrawal scheduled for the next payout date.")
            else:
                messages.success(request, "2FA verified! Withdrawal request updated.")
            return redirect('withdrawals:dashboard')
        else:
            messages.error(request, message or 'Invalid 2FA token. Please try again.')
    
    return render(request, 'withdrawals/verify_2fa.html', {
        'withdrawal_request': withdrawal_request,
        'two_fa': request.user.two_factor,
    })

@login_required
def withdrawal_history(request):
    """
    View withdrawal history
    """
    withdrawals = WithdrawalRequest.objects.filter(
        user=request.user
    ).order_by('-requested_at')
    
    # Pagination
    paginator = Paginator(withdrawals, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    return render(request, 'withdrawals/history.html', {
        'withdrawals': page_obj,
        'page_obj': page_obj,
    })

@login_required
def withdrawal_details(request, withdrawal_id):
    """
    View withdrawal details
    """
    withdrawal = get_object_or_404(
        WithdrawalRequest,
        id=withdrawal_id,
        user=request.user
    )
    
    return render(request, 'withdrawals/details.html', {
        'withdrawal': withdrawal,
    })

# Admin views
@require_POST
@csrf_exempt
def stripe_webhook(request):
    """
    Handle Stripe webhooks for Connect accounts
    """
    payload = request.body
    sig_header = request.META.get('HTTP_STRIPE_SIGNATURE')
    
    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, settings.STRIPE_WEBHOOK_SECRET
        )
        
        # Handle relevant events
        if event.type == 'account.updated':
            account = event.data.object
            # Update withdrawal method verification status
            WithdrawalMethod.objects.filter(
                stripe_account_id=account.id
            ).update(is_verified=account.charges_enabled)
        
        elif event.type == 'transfer.updated':
            transfer = event.data.object
            # Update withdrawal status
            WithdrawalRequest.objects.filter(
                stripe_transfer_id=transfer.id
            ).update(status=transfer.status)
        
        return HttpResponse(status=200)
        
    except Exception as e:
        return HttpResponse(status=400)

@require_POST
@csrf_exempt
def paypal_webhook(request):
    """
    Handle PayPal webhooks for payouts
    """
    try:
        # Parse PayPal webhook
        webhook_data = json.loads(request.body)
        if not verify_paypal_webhook_signature(request=request, webhook_event=webhook_data):
            return HttpResponse(status=400)
        
        # Handle payout status updates
        if webhook_data.get('event_type') == 'PAYMENT.PAYOUTSBATCH.COMPLETED':
            payout_batch_id = webhook_data['resource']['payout_batch_id']
            WithdrawalRequest.objects.filter(
                paypal_payout_id=payout_batch_id
            ).update(status='completed', completed_at=timezone.now())
        
        return HttpResponse(status=200)
        
    except Exception:
        logger.exception("PayPal payouts webhook handling error")
        return HttpResponse(status=400)
