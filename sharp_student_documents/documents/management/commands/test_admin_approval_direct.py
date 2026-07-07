from django.core.management.base import BaseCommand
from django.test import Client, TestCase
from django.contrib.auth import get_user_model
from withdrawals.models import WithdrawalRequest
import json


class Command(BaseCommand):
    help = 'Test admin approval with direct request'

    def handle(self, *args, **options):
        self.stdout.write('=== TESTING ADMIN APPROVAL DIRECTLY ===')
        
        User = get_user_model()
        
        # Get admin user
        try:
            admin_user = User.objects.get(username='testadmin')
            self.stdout.write(f'Admin user: {admin_user.username}')
        except User.DoesNotExist:
            self.stdout.write('ERROR: Admin user not found')
            return
        
        # Get a pending withdrawal
        withdrawal = WithdrawalRequest.objects.filter(status='pending').first()
        if not withdrawal:
            self.stdout.write('ERROR: No pending withdrawals found')
            return
        
        self.stdout.write(f'Testing approval for: {withdrawal.id}')
        self.stdout.write(f'Amount: ${withdrawal.amount}')
        self.stdout.write(f'Status: {withdrawal.status}')
        
        # Create client and login
        client = Client()
        
        # First try to get the admin page to check if it loads
        self.stdout.write('\\n--- Testing Admin Page ---')
        response = client.get('/admin/manage-withdrawals/')
        self.stdout.write(f'Admin page status: {response.status_code}')
        
        if response.status_code != 200:
            self.stdout.write('ERROR: Admin page not accessible')
            return
        
        # Now test the approval endpoint
        self.stdout.write('\\n--- Testing Approval Endpoint ---')
        
        # Get CSRF token from the page
        csrf_token = client.get('/admin/manage-withdrawals/').cookies.get('csrftoken')
        self.stdout.write(f'CSRF token: {csrf_token[:20] if csrf_token else "None"}')
        
        # Test approval with CSRF
        if csrf_token:
            response = client.post(
                f'/withdrawals/admin/approve/{withdrawal.id}/',
                data=json.dumps({}),
                content_type='application/json',
                HTTP_X_CSRFTOKEN=csrf_token
            )
        else:
            # Try without CSRF token
            response = client.post(
                f'/withdrawals/admin/approve/{withdrawal.id}/',
                data=json.dumps({}),
                content_type='application/json'
            )
        
        self.stdout.write(f'Approval response status: {response.status_code}')
        
        if response.status_code == 200:
            data = response.json()
            self.stdout.write(f'SUCCESS: {data}')
            
            # Check withdrawal status
            withdrawal.refresh_from_db()
            self.stdout.write(f'New status: {withdrawal.status}')
            
            if withdrawal.paypal_payout_id:
                self.stdout.write(f'PayPal payout ID: {withdrawal.paypal_payout_id}')
        else:
            self.stdout.write(f'ERROR: {response.content.decode()}')
        
        self.stdout.write('\\n=== TEST COMPLETE ===')
