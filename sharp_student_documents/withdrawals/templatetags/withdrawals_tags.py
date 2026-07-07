from django import template
from withdrawals.models import AdminNotification

register = template.Library()

@register.simple_tag
def unread_notification_count(user):
    """Get the count of unread admin notifications for the current user"""
    if user and user.is_superuser:
        return AdminNotification.objects.filter(is_read=False).count()
    return 0

@register.simple_tag
def urgent_notification_count(user):
    """Get the count of urgent unread admin notifications"""
    if user and user.is_superuser:
        return AdminNotification.objects.filter(is_read=False, priority='urgent').count()
    return 0

@register.simple_tag
def recent_notifications(user, limit=5):
    """Get recent admin notifications for the current user"""
    if user and user.is_superuser:
        return AdminNotification.objects.filter(
            is_read=False
        ).order_by('-created_at')[:limit]
    return []
