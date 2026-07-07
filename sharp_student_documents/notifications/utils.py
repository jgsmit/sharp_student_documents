from django.core.mail import send_mail
from django.conf import settings
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.template import TemplateDoesNotExist
import logging

logger = logging.getLogger(__name__)


def _render_email(template_name, context, fallback_message):
    try:
        html_message = render_to_string(template_name, context)
        plain_message = strip_tags(html_message)
        return plain_message, html_message
    except TemplateDoesNotExist:
        return fallback_message, None
    except Exception:
        logger.exception("Failed to render email template %s", template_name)
        return fallback_message, None


def send_admin_notification(subject, message, html_message=None, recipient_email=None):
    """
    Send notification email to admin (your personal email)
    
    Args:
        subject (str): Email subject
        message (str): Plain text message
        html_message (str): Optional HTML message
        recipient_email (str): Optional recipient email (defaults to admin email)
    """
    try:
        recipient = recipient_email or settings.EMAIL_HOST_USER
        send_mail(
            subject=subject,
            message=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[recipient],
            html_message=html_message,
            fail_silently=False,
        )
        return True
    except Exception as e:
        logger.exception("Failed to send admin notification")
        return False


def send_new_document_notification(document):
    """Send notification when a new document is uploaded"""
    subject = f"New Document Uploaded: {document.title}"
    
    context = {
        'document': document,
        'seller': document.seller,
        'site_url': settings.ALLOWED_HOSTS[0] if settings.ALLOWED_HOSTS else 'localhost:8000'
    }
    
    plain_message, html_message = _render_email(
        "notifications/new_document.html",
        context,
        f"New document uploaded: {document.title} by {getattr(document.seller, 'username', '')}",
    )
    
    return send_admin_notification(subject, plain_message, html_message)


def send_new_purchase_notification(purchase):
    """Send notification when a document is purchased"""
    subject = f"New Purchase: {purchase.document.title}"
    
    context = {
        'purchase': purchase,
        'document': purchase.document,
        'buyer': purchase.buyer,
        'site_url': settings.ALLOWED_HOSTS[0] if settings.ALLOWED_HOSTS else 'localhost:8000'
    }
    
    plain_message, html_message = _render_email(
        "notifications/new_purchase.html",
        context,
        f"New purchase: {purchase.document.title} by {getattr(purchase.buyer, 'username', '')}",
    )
    
    return send_admin_notification(subject, plain_message, html_message)


def send_new_user_notification(user):
    """Send notification when a new user registers"""
    subject = f"New User Registration: {user.get_full_name() or user.email}"
    
    context = {
        'user': user,
        'site_url': settings.ALLOWED_HOSTS[0] if settings.ALLOWED_HOSTS else 'localhost:8000'
    }
    
    plain_message, html_message = _render_email(
        "notifications/new_user.html",
        context,
        f"New user registration: {user.get_full_name() or user.email}",
    )
    
    return send_admin_notification(subject, plain_message, html_message)


def send_payment_notification(payment):
    """Send notification when a payment is received"""
    subject = f"Payment Received: ${payment.amount}"

    order = getattr(payment, "order", None)
    document = getattr(order, "document", None) if order else None
    buyer = getattr(order, "buyer", None) if order else None
    
    context = {
        'payment': payment,
        'document': document,
        'buyer': buyer,
        'site_url': settings.ALLOWED_HOSTS[0] if settings.ALLOWED_HOSTS else 'localhost:8000'
    }

    document_title = getattr(document, "title", "")
    buyer_name = getattr(buyer, "username", "") or getattr(buyer, "email", "")
    plain_message, html_message = _render_email(
        "notifications/payment_received.html",
        context,
        f"Payment received: ${payment.amount} for {document_title} by {buyer_name}",
    )
    
    return send_admin_notification(subject, plain_message, html_message)


def send_system_alert(subject, message, level='info'):
    """Send system alert notification"""
    subject = f"[SharpDocs Alert] {subject}"
    
    context = {
        'subject': subject,
        'message': message,
        'level': level,
        'site_url': settings.ALLOWED_HOSTS[0] if settings.ALLOWED_HOSTS else 'localhost:8000'
    }
    
    plain_message, html_message = _render_email(
        "notifications/system_alert.html",
        context,
        f"{subject}\n\n{message}",
    )
    
    return send_admin_notification(subject, plain_message, html_message)
