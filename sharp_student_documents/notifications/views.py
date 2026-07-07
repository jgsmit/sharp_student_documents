from django.shortcuts import render
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.contrib.auth.decorators import login_required
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
