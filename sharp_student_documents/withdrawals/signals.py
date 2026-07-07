import logging
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone
from .models import WithdrawalRequest, WithdrawalSchedule
try:
    from security.models import TwoFactorAuth
except ImportError:
    TwoFactorAuth = None
from .services import WithdrawalService

logger = logging.getLogger(__name__)

@receiver(post_save, sender=WithdrawalRequest)
def withdrawal_request_created(sender, instance, created, **kwargs):
    """Handle withdrawal request creation"""
    if created:
        # Calculate fees
        try:
            instance.calculate_fee()
        except Exception:
            logger.exception("Error calculating fees for withdrawal %s", instance.id)
        
        # Check if 2FA is required
        try:
            # Check if user has 2FA enabled
            try:
                two_fa = instance.user.two_factor
                if two_fa and two_fa.is_enabled:
                    # Require 2FA for all withdrawals for security
                    if instance.status == 'pending':
                        instance.status = '2fa_required'
                        instance.save()
                else:
                    # No 2FA setup, proceed normally
                    logger.debug("No 2FA required for withdrawal %s", instance.id)
            except ImportError:
                # Security app not available, proceed without 2FA
                logger.warning("Security app not available for withdrawal %s", instance.id)
            except Exception:
                logger.exception("Error checking 2FA for withdrawal %s", instance.id)
            
            try:
                # Instant withdrawals are disabled; schedule for payout day.
                WithdrawalService._schedule_weekly_withdrawal(instance)
            except AttributeError:
                logger.exception("Error processing withdrawal %s", instance.id)
                # Fallback: try to process anyway
                try:
                    WithdrawalService._schedule_weekly_withdrawal(instance)
                except Exception:
                    logger.exception("Fallback: Failed to process withdrawal %s", instance.id)
        except Exception:
            logger.exception("Error in withdrawal_request_created signal")

@receiver(post_save, sender=WithdrawalSchedule)
def withdrawal_schedule_updated(sender, instance, **kwargs):
    """Update next processing time when schedule changes"""
    if instance.is_active:
        instance.next_processing = instance.get_next_processing_time()
        instance.save()

if TwoFactorAuth is not None:
    @receiver(post_save, sender=TwoFactorAuth)
    def two_factor_auth_enabled(sender, instance, created, **kwargs):
        """Generate backup codes when 2FA is enabled"""
        if instance.is_enabled and not instance.backup_codes:
            instance.generate_backup_codes()
