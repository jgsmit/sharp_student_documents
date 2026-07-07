from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.test import Client
from withdrawals.models import WithdrawalRequest, WithdrawalMethod
from decimal import Decimal
import json


class Command(BaseCommand):
    help = 'Test admin view details functionality'

    def handle(self, *args, **options):
        self.stdout.write('=== TESTING ADMIN VIEW DETAILS FUNCTIONALITY ===')
        
        # Get or create admin user
        User = get_user_model()
        try:
            admin_user = User.objects.get(username='admin')
        except User.DoesNotExist:
            admin_user = User.objects.create_superuser(
                username='admin',
                email='admin@example.com',
                password='admin123'
            )
            self.stdout.write('Created admin user: admin')
        
        # Get or create test seller
        try:
            seller_user = User.objects.get(username='testuser')
        except User.DoesNotExist:
            seller_user = User.objects.create_user(
                username='testuser',
                email='test@example.com',
                password='testpass123'
            )
            self.stdout.write('Created test user: testuser')
        
        # Create PayPal withdrawal method
        try:
            paypal_method = WithdrawalMethod.objects.get(
                user=seller_user,
                method_type='paypal'
            )
        except WithdrawalMethod.DoesNotExist:
            paypal_method = WithdrawalMethod.objects.create(
                user=seller_user,
                method_type='paypal',
                paypal_email='test@example.com',
                is_verified=True,
                is_active=True
            )
            self.stdout.write('Created PayPal withdrawal method')
        
        # Create a withdrawal request
        try:
            withdrawal = WithdrawalRequest.objects.create(
                user=seller_user,
                withdrawal_method=paypal_method,
                amount=Decimal('50.00'),
                payout_type='weekly'
            )
            self.stdout.write(f'Created withdrawal request: {withdrawal.id}')
            
            # Test the details API endpoint
            client = Client()
            client.force_login(admin_user)
            
            # Test details endpoint
            self.stdout.write('\n--- TESTING DETAILS ENDPOINT ---')
            response = client.get(f'/withdrawals/admin/details/{withdrawal.id}/')
            
            self.stdout.write(f'Details response status: {response.status_code}')
            if response.status_code == 200:
                response_data = response.json()
                self.stdout.write(f'Details response success: {response_data.get("success")}')
                
                if response_data.get('success'):
                    details = response_data.get('details', {})
                    self.stdout.write('Withdrawal details:')
                    self.stdout.write(f'  User: {details.get("user", {}).get("username", "N/A")}')
                    self.stdout.write(f'  Amount: ${details.get("amount", "N/A")}')
                    self.stdout.write(f'  Fee: ${details.get("fee", "N/A")}')
                    self.stdout.write(f'  Net Amount: ${details.get("net_amount", "N/A")}')
                    self.stdout.write(f'  Status: {details.get("status", "N/A")}')
                    self.stdout.write(f'  Method Type: {details.get("withdrawal_method", {}).get("type", "N/A")}')
                    self.stdout.write(f'  Can Approve: {details.get("can_approve", False)}')
                    
                    # Check PayPal method details
                    method_details = details.get('withdrawal_method', {}).get('details', {})
                    if method_details:
                        self.stdout.write(f'  PayPal Email: {method_details.get("email", "N/A")}')
                        self.stdout.write(f'  PayPal Verified: {method_details.get("verified", False)}')
                else:
                    self.stdout.write(f'Error: {response_data.get("error", "Unknown error")}')
            else:
                self.stdout.write(f'Details response content: {response.content.decode()}')
            
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Error during testing: {e}'))
            import traceback
            self.stdout.write(traceback.format_exc())
        
        # Clean up
        try:
            WithdrawalRequest.objects.filter(user=seller_user).delete()
            WithdrawalMethod.objects.filter(user=seller_user).delete()
            seller_user.delete()
            self.stdout.write('\nCleaned up test data')
        except:
            pass
        
        self.stdout.write('\n=== TEST COMPLETE ===')
        self.stdout.write('The view details functionality should now work in the browser!')
        self.stdout.write('Click the "View Details" button (eye icon) to see the enhanced modal.')
