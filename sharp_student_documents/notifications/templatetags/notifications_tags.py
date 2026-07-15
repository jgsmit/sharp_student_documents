from django import template
from ..models import UserNotification

register = template.Library()


@register.simple_tag
def user_unread_count(user):
    if user and user.is_authenticated:
        return UserNotification.objects.filter(user=user, is_read=False).count()
    return 0


@register.simple_tag
def user_recent_notifications(user, limit=5):
    if user and user.is_authenticated:
        return UserNotification.objects.filter(user=user).order_by('-created_at')[:limit]
    return []
