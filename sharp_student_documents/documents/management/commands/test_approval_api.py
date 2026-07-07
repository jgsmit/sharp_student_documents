from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.test import Client
from withdrawals.models import WithdrawalRequest, WithdrawalMethod
from decimal import Decimal
import json


class Command(BaseCommand):
    help = 'Test admin approval functionality with real API calls'

    def handle(self, *args, **options):
        self.stdout.write('=== TESTING ADMIN APPROVAL FUNCTIONALITY ===')
        
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
            self.stdout.write(f'  Status: {withdrawal.status}')
            
            # Test the approval API endpoint
            client = Client()
            client.force_login(admin_user)
            
            # Test approval endpoint
            self.stdout.write('\n--- TESTING APPROVAL ENDPOINT ---')
            response = client.post(
                f'/withdrawals/admin/approve/{withdrawal.id}/',
                data=json.dumps({}),
                content_type='application/json'
            )
            
            self.stdout.write(f'Approval response status: {response.status_code}')
            if response.status_code == 200:
                response_data = response.json()
                self.stdout.write(f'Approval response data: {response_data}')
                
                # Check if withdrawal status changed
                withdrawal.refresh_from_db()
                self.stdout.write(f'Withdrawal status after approval: {withdrawal.status}')
            else:
                self.stdout.write(f'Approval response content: {response.content.decode()}')
            
            # Create another withdrawal for rejection test
            withdrawal2 = WithdrawalRequest.objects.create(
                user=seller_user,
                withdrawal_method=paypal_method,
                amount=Decimal('25.00'),
                payout_type='weekly'
            )
            
            # Test rejection endpoint
            self.stdout.write('\n--- TESTING REJECTION ENDPOINT ---')
            response = client.post(
                f'/withdrawals/admin/reject/{withdrawal2.id}/',
                data={'reason': 'Test rejection'},
                content_type='application/x-www-form-urlencoded'
            )
            
            self.stdout.write(f'Rejection response status: {response.status_code}')
            if response.status_code == 200:
                response_data = response.json()
                self.stdout.write(f'Rejection response data: {response_data}')
                
                # Check if withdrawal status changed
                withdrawal2.refresh_from_db()
                self.stdout.write(f'Withdrawal status after rejection: {withdrawal2.status}')
                self.stdout.write(f'Failure reason: {withdrawal2.failure_reason}')
            else:
                self.stdout.write(f'Rejection response content: {response.content.decode()}')
            
            # Test details endpoint
            self.stdout.write('\n--- TESTING DETAILS ENDPOINT ---')
            response = client.get(f'/withdrawals/admin/details/{withdrawal.id}/')
            
            self.stdout.write(f'Details response status: {response.status_code}')
            if response.status_code == 200:
                response_data = response.json()
                self.stdout.write(f'Details response data: {response_data}')
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
