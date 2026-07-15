import json
from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.utils import timezone
from .models import UserNotification
from .utils import send_admin_notification


@require_POST
@login_required
def send_test_email_view(request):
    """Send test email from web interface"""
    recipient_email = request.POST.get('email', 'themanpappylove@gmail.com')
    subject = request.POST.get('subject', 'Test Email from SharpDocs')
    message = request.POST.get('message', 'This is a test email from SharpDocs.')

    try:
        result = send_admin_notification(
            subject=subject,
            message=message,
            recipient_email=recipient_email
        )

        if result:
            return JsonResponse({
                'success': True,
                'message': f'Email sent successfully to {recipient_email}'
            })
        else:
            return JsonResponse({
                'success': False,
                'message': 'Failed to send email'
            })

    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'Error: {str(e)}'
        })


def test_email_page(request):
    """Simple page to test email sending"""
    return render(request, 'notifications/test_email.html')


@login_required
def check_new_notifications(request):
    """Check for new user notifications since last check"""
    try:
        five_min_ago = timezone.now() - timezone.timedelta(minutes=5)
        notifications = UserNotification.objects.filter(
            user=request.user,
            is_read=False,
            created_at__gte=five_min_ago
        ).order_by('-created_at')[:5]

        data = [{
            'id': str(n.id),
            'type': n.notification_type,
            'title': n.title,
            'message': n.message,
            'link': n.link,
            'created_at': n.created_at.isoformat(),
        } for n in notifications]

        total_unread = UserNotification.objects.filter(
            user=request.user, is_read=False
        ).count()

        return JsonResponse({
            'has_new': len(data) > 0,
            'notifications': data,
            'total_unread': total_unread,
        })
    except Exception as e:
        return JsonResponse({'has_new': False, 'error': str(e)})


@login_required
def notification_list(request):
    """Full notification list page for the user"""
    notifications = UserNotification.objects.filter(user=request.user)

    # Filters
    ntype = request.GET.get('type', '')
    status = request.GET.get('status', '')

    if ntype:
        notifications = notifications.filter(notification_type=ntype)
    if status == 'unread':
        notifications = notifications.filter(is_read=False)
    elif status == 'read':
        notifications = notifications.filter(is_read=True)

    notifications = notifications.order_by('-created_at')

    paginator = Paginator(notifications, 20)
    page = request.GET.get('page')
    page_obj = paginator.get_page(page)

    unread_count = UserNotification.objects.filter(
        user=request.user, is_read=False
    ).count()

    context = {
        'notifications': page_obj,
        'page_obj': page_obj,
        'is_paginated': page_obj.has_other_pages(),
        'unread_count': unread_count,
        'total_count': UserNotification.objects.filter(user=request.user).count(),
        'notification_types': UserNotification.NOTIFICATION_TYPES,
    }
    return render(request, 'notifications/list.html', context)


@login_required
@require_POST
def mark_notification_read(request, notification_id):
    notification = get_object_or_404(
        UserNotification, id=notification_id, user=request.user
    )
    notification.mark_as_read()
    return JsonResponse({'success': True})


@login_required
@require_POST
def mark_all_notifications_read(request):
    count = UserNotification.objects.filter(
        user=request.user, is_read=False
    ).update(is_read=True, read_at=timezone.now())
    return JsonResponse({'success': True, 'count': count})


@login_required
@require_POST
def delete_notification(request, notification_id):
    notification = get_object_or_404(
        UserNotification, id=notification_id, user=request.user
    )
    notification.delete()
    return JsonResponse({'success': True})
