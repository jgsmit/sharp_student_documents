"""
PayPal payout destination helpers.

Note: Platforms generally cannot "verify" a seller's PayPal email via API.
The platform can only attempt a payout to the provided email; if it fails,
the seller must correct the email or their PayPal account must accept payouts.
"""
import logging

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import validate_email
from django.utils import timezone
from django.urls import reverse

logger = logging.getLogger(__name__)

def validate_paypal_email(paypal_email: str):
    """Basic validation for a PayPal payout email (syntax only)."""
    try:
        validate_email(paypal_email)
        return True, "PayPal payout email saved."
    except ValidationError:
        return False, "Invalid email format."

def send_paypal_verification_email(user, paypal_email, request=None):
    """
    Send verification email to user
    """
    from django.core.mail import send_mail

    verification_path = reverse("withdrawals:verify_paypal", args=[user.id])
    if request:
        verification_link = request.build_absolute_uri(verification_path)
    else:
        verification_link = f"{getattr(settings, 'SITE_URL', 'http://127.0.0.1:8000').rstrip('/')}{verification_path}"
    
    subject = "Verify Your PayPal Account - SharpDocs"
    message = f"""
Hi {user.username},

Please verify your PayPal payout email ({paypal_email}) for SharpDocs withdrawals.

Click here to verify:
{verification_link}

If you did not add this payout email, you can ignore this message.

Thanks,
SharpDocs Team
    """
    
    try:
        send_mail(
            subject,
            message,
            settings.DEFAULT_FROM_EMAIL,
            [user.email],
            fail_silently=False,
        )
        return True
    except Exception as e:
        logger.exception("Failed to send verification email")
        return False

def auto_verify_paypal_account(withdrawal_method):
    """
    Auto-verify PayPal account for testing/demo purposes
    """
    withdrawal_method.is_verified = True
    withdrawal_method.paypal_verified = True
    withdrawal_method.updated_at = timezone.now()
    withdrawal_method.save()
    return True
