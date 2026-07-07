from django.core.management.base import BaseCommand
from django.test import Client
from django.contrib.auth import get_user_model
from withdrawals.models import WithdrawalRequest


class Command(BaseCommand):
    help = 'Test withdrawal approval API'

    def handle(self, *args, **options):
        self.stdout.write('=== TESTING WITHDRAWAL APPROVAL API ===')
        
        User = get_user_model()
        
        # Get admin user
        try:
            admin_user = User.objects.get(username='testadmin')
            self.stdout.write(f'Admin user found: {admin_user.username}')
        except User.DoesNotExist:
            self.stdout.write('ERROR: Admin user not found')
            return
        
        # Get a pending withdrawal
        withdrawal = WithdrawalRequest.objects.filter(status='pending').first()
        if not withdrawal:
            self.stdout.write('ERROR: No pending withdrawals found')
            return
        
        self.stdout.write(f'Testing approval for withdrawal: {withdrawal.id}')
        self.stdout.write(f'Amount: ${withdrawal.amount}')
        self.stdout.write(f'Status: {withdrawal.status}')
        self.stdout.write(f'Type: {withdrawal.payout_type}')
        
        # Test the approval endpoint
        client = Client()
        client.force_login(admin_user)
        
        self.stdout.write('\\n--- Testing API Endpoint ---')
        response = client.post(
            f'/withdrawals/admin/approve/{withdrawal.id}/',
            data={},
            content_type='application/json'
        )
        
        self.stdout.write(f'Response status: {response.status_code}')
        
        if response.status_code == 200:
            data = response.json()
            self.stdout.write(f'SUCCESS: {data}')
            
            # Check if withdrawal was updated
            withdrawal.refresh_from_db()
            self.stdout.write(f'New status: {withdrawal.status}')
            
            if withdrawal.paypal_payout_id:
                self.stdout.write(f'PayPal payout ID: {withdrawal.paypal_payout_id}')
        else:
            self.stdout.write(f'ERROR: {response.content.decode()}')
        
        self.stdout.write('\\n=== TEST COMPLETE ===')
