from django.core.management.base import BaseCommand
from django.test import Client
from django.contrib.auth import get_user_model
from withdrawals.models import WithdrawalMethod


class Command(BaseCommand):
    help = 'Test Stripe Connect setup flow'

    def handle(self, *args, **options):
        self.stdout.write('=== TESTING STRIPE CONNECT SETUP ===')
        
        # Get or create a test user
        User = get_user_model()
        try:
            test_user = User.objects.get(username='testuser')
        except User.DoesNotExist:
            test_user = User.objects.create_user(
                username='testuser',
                email='test@example.com',
                password='testpass123'
            )
            self.stdout.write('Created test user: testuser')
        
        # Simulate the Stripe Connect setup request
        client = Client()
        client.force_login(test_user)
        
        # Test the setup_stripe_connect view
        try:
            response = client.post('/withdrawals/setup/', {
                'method_type': 'stripe'
            })
            
            if response.status_code == 302:
                self.stdout.write(self.style.SUCCESS('✅ Redirect working correctly'))
                self.stdout.write(f'   Redirecting to: {response.url}')
            else:
                self.stdout.write(self.style.ERROR(f'❌ Unexpected response status: {response.status_code}'))
                if response.status_code == 200:
                    self.stdout.write('   Check for error messages in the response')
            
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'❌ Test failed: {e}'))
        
        # Clean up
        try:
            WithdrawalMethod.objects.filter(user=test_user).delete()
            test_user.delete()
            self.stdout.write('Cleaned up test data')
        except:
            pass
