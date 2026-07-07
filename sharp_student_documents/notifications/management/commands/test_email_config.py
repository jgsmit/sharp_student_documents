from django.core.management.base import BaseCommand
from django.conf import settings
import smtplib


class Command(BaseCommand):
    help = 'Test email configuration and connectivity'

    def handle(self, *args, **options):
        self.stdout.write('Testing Email Configuration...')
        self.stdout.write('=' * 50)
        
        # Check configuration
        self.stdout.write(f'Email Backend: {settings.EMAIL_BACKEND}')
        self.stdout.write(f'Email Host: {settings.EMAIL_HOST}')
        self.stdout.write(f'Email Port: {settings.EMAIL_PORT}')
        self.stdout.write(f'Email User: {settings.EMAIL_HOST_USER}')
        self.stdout.write(f'Use TLS: {settings.EMAIL_USE_TLS}')
        self.stdout.write(f'From Email: {settings.DEFAULT_FROM_EMAIL}')
        
        # Test SMTP connection
        self.stdout.write('\nTesting SMTP Connection...')
        try:
            server = smtplib.SMTP(settings.EMAIL_HOST, settings.EMAIL_PORT)
            server.starttls()  # Upgrade to secure connection
            
            # Try to authenticate
            server.login(settings.EMAIL_HOST_USER, settings.EMAIL_HOST_PASSWORD)
            self.stdout.write(self.style.SUCCESS('SUCCESS: SMTP connection and authentication successful!'))
            
            # Test sending a test email to yourself
            from_email = settings.DEFAULT_FROM_EMAIL
            to_email = settings.EMAIL_HOST_USER
            
            subject = 'SMTP Test from SharpDocs'
            body = f'''
This is a test email to verify your SMTP configuration is working.

Configuration Details:
- SMTP Server: {settings.EMAIL_HOST}:{settings.EMAIL_PORT}
- Authentication: Successful
- TLS: {settings.EMAIL_USE_TLS}
- From: {from_email}
- To: {to_email}

Your email system is ready to send notifications!

Best regards,
SharpDocs System
            '''
            
            message = f'Subject: {subject}\n\n{body}'
            server.sendmail(from_email, to_email, message)
            server.quit()
            
            self.stdout.write(self.style.SUCCESS('SUCCESS: Test email sent to your inbox!'))
            self.stdout.write(f'Check your email at: {settings.EMAIL_HOST_USER}')
            
        except smtplib.SMTPAuthenticationError as e:
            self.stdout.write(self.style.ERROR(f'ERROR: Authentication failed - {e}'))
            self.stdout.write('Check your email and app password in .env file')
            
        except smtplib.SMTPConnectError as e:
            self.stdout.write(self.style.ERROR(f'ERROR: Connection failed - {e}'))
            self.stdout.write('Check your internet connection and firewall settings')
            
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'ERROR: {e}'))
            
        self.stdout.write('\nConfiguration Status:')
        if settings.EMAIL_HOST_USER and settings.EMAIL_HOST_PASSWORD:
            self.stdout.write(self.style.SUCCESS('✓ Email credentials configured'))
        else:
            self.stdout.write(self.style.ERROR('✗ Email credentials missing'))
            
        if 'console' in settings.EMAIL_BACKEND:
            self.stdout.write(self.style.WARNING('⚠ Using console backend (emails will print to console)'))
        else:
            self.stdout.write(self.style.SUCCESS('✓ Using SMTP backend'))
