from django.core.management.base import BaseCommand
from django.core.mail import send_mail
from django.conf import settings
from notifications.utils import send_admin_notification, send_system_alert


class Command(BaseCommand):
    help = 'Test email configuration and send test notification'

    def handle(self, *args, **options):
        self.stdout.write('Testing email configuration...')
        
        # Test basic email sending
        try:
            subject = 'SharpDocs Email Test'
            message = 'This is a test email to verify your email configuration is working correctly.'
            
            result = send_admin_notification(subject, message)
            
            if result:
                self.stdout.write(
                    self.style.SUCCESS('SUCCESS: Test email sent successfully!')
                )
                self.stdout.write(f'   Sent to: {settings.EMAIL_HOST_USER}')
                self.stdout.write(f'   From: {settings.DEFAULT_FROM_EMAIL}')
            else:
                self.stdout.write(
                    self.style.ERROR('ERROR: Failed to send test email')
                )
                
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'ERROR: Error sending test email: {e}')
            )
            
        # Test system alert
        try:
            send_system_alert(
                'System Test',
                'This is a test system alert from SharpDocs.',
                'info'
            )
            self.stdout.write(
                self.style.SUCCESS('SUCCESS: System alert test sent successfully!')
            )
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'ERROR: Error sending system alert: {e}')
            )
            
        self.stdout.write('\nEmail Configuration Details:')
        self.stdout.write(f'   Email Backend: {settings.EMAIL_BACKEND}')
        self.stdout.write(f'   Email Host: {settings.EMAIL_HOST}')
        self.stdout.write(f'   Email Port: {settings.EMAIL_PORT}')
        self.stdout.write(f'   Email User: {settings.EMAIL_HOST_USER}')
        self.stdout.write(f'   Use TLS: {settings.EMAIL_USE_TLS}')
