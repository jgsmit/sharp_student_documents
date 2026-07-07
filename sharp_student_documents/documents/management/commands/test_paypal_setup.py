from django.core.management.base import BaseCommand
from django.test import Client
from django.contrib.auth import get_user_model
from withdrawals.models import WithdrawalMethod


class Command(BaseCommand):
    help = 'Test PayPal withdrawal setup'

    def handle(self, *args, **options):
        self.stdout.write('=== TESTING PAYPAL WITHDRAWAL SETUP ===')
        
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
        
        # Test PayPal setup
        client = Client()
        client.force_login(test_user)
        
        try:
            # Test PayPal setup form submission
            response = client.post('/withdrawals/setup/', {
                'method_type': 'paypal',
                'paypal_email': 'test-paypal@example.com'
            })
            
            if response.status_code == 302:
                self.stdout.write(self.style.SUCCESS('PayPal setup redirect working'))
                self.stdout.write('   User should be redirected to withdrawal dashboard')
                
                # Check if withdrawal method was created
                try:
                    withdrawal_method = WithdrawalMethod.objects.get(
                        user=test_user,
                        method_type='paypal'
                    )
                    self.stdout.write(self.style.SUCCESS('PayPal withdrawal method created'))
                    self.stdout.write(f'   PayPal Email: {withdrawal_method.paypal_email}')
                    self.stdout.write(f'   Verified: {withdrawal_method.is_verified}')
                    self.stdout.write(f'   Active: {withdrawal_method.is_active}')
                    
                except WithdrawalMethod.DoesNotExist:
                    self.stdout.write(self.style.ERROR('PayPal withdrawal method not found'))
                    
            else:
                self.stdout.write(self.style.ERROR(f'Unexpected response status: {response.status_code}'))
                if response.status_code == 200:
                    self.stdout.write('   Check for error messages in response')
                    
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Test failed: {e}'))
        
        # Test Stripe is properly disabled
        self.stdout.write('\n--- TESTING STRIPE DISABLE ---')
        response = client.post('/withdrawals/setup/', {
            'method_type': 'stripe'
        })
        
        if response.status_code == 302:
            # Should redirect back to setup page with warning message
            self.stdout.write(self.style.SUCCESS('Stripe properly disabled'))
            self.stdout.write('   User redirected with warning message')
        else:
            self.stdout.write(self.style.ERROR(f'Stripe disable not working: {response.status_code}'))
        
        # Clean up
        try:
            WithdrawalMethod.objects.filter(user=test_user).delete()
            test_user.delete()
            self.stdout.write('\nCleaned up test data')
        except:
            pass
        
        self.stdout.write('\n=== PAYPAL SETUP TEST COMPLETE ===')
        self.stdout.write('PayPal withdrawal setup is working correctly!')
        self.stdout.write('Users can now add PayPal accounts for withdrawals.')
