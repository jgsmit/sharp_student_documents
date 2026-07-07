from django.core.management.base import BaseCommand
from django.conf import settings
from django.utils import timezone
from notifications.utils import send_admin_notification


class Command(BaseCommand):
    help = 'Send a test email to specified recipient'

    def add_arguments(self, parser):
        parser.add_argument(
            '--email',
            type=str,
            default='themanpappylove@gmail.com',
            help='Email address to send test to (default: themanpappylove@gmail.com)'
        )
        parser.add_argument(
            '--subject',
            type=str,
            default='Test Email from SharpDocs',
            help='Email subject'
        )

    def handle(self, *args, **options):
        recipient_email = options['email']
        subject = options['subject']
        
        self.stdout.write(f'Sending test email to: {recipient_email}')
        
        # Create test message
        message = f'''
Hello!

This is a test email from your SharpDocs document marketplace.

Email Details:
- From: {settings.DEFAULT_FROM_EMAIL}
- To: {recipient_email}
- Subject: {subject}
- Sent at: {timezone.now().strftime('%Y-%m-%d %H:%M:%S')}

Your email integration is working correctly!

Best regards,
SharpDocs Team
        '''
        
        try:
            result = send_admin_notification(
                subject=subject,
                message=message.strip(),
                recipient_email=recipient_email
            )
            
            if result:
                self.stdout.write(
                    self.style.SUCCESS(f'SUCCESS: Email sent successfully to {recipient_email}!')
                )
                self.stdout.write(f'   From: {settings.DEFAULT_FROM_EMAIL}')
                self.stdout.write(f'   Subject: {subject}')
            else:
                self.stdout.write(
                    self.style.ERROR('ERROR: Failed to send email')
                )
                
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'ERROR: {e}')
            )
