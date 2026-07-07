from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from withdrawals.models import WithdrawalRequest


class Command(BaseCommand):
    help = 'Debug withdrawal approval button issue'

    def handle(self, *args, **options):
        self.stdout.write('=== DEBUGGING WITHDRAWAL APPROVAL BUTTON ===')
        
        User = get_user_model()
        
        # Get a pending withdrawal
        withdrawal = WithdrawalRequest.objects.filter(status='pending').first()
        if not withdrawal:
            self.stdout.write('No pending withdrawals found')
            return
        
        self.stdout.write(f'Testing withdrawal: {withdrawal.id}')
        self.stdout.write(f'Amount: ${withdrawal.amount}')
        self.stdout.write(f'Status: {withdrawal.status}')
        self.stdout.write(f'Type: {withdrawal.payout_type}')
        
        # Test the URL that should be called
        from django.urls import reverse
        url = reverse('withdrawals:admin_approve', kwargs={'withdrawal_id': withdrawal.id})
        self.stdout.write(f'API URL: {url}')
        
        # Check if the admin user exists and is a superuser
        try:
            admin = User.objects.get(username='admin')
            self.stdout.write(f'Admin user: {admin.username}')
            self.stdout.write(f'Is superuser: {admin.is_superuser}')
            self.stdout.write(f'Is staff: {admin.is_staff}')
            self.stdout.write(f'Is active: {admin.is_active}')
        except User.DoesNotExist:
            self.stdout.write('ERROR: Admin user not found')
            return
        
        # Create a simple test HTML to debug the issue
        self.stdout.write('\\n--- DEBUGGING HTML ---')
        self.stdout.write('The approve button should call: approveWithdrawal("withdrawal_id")')
        self.stdout.write('This function should:')
        self.stdout.write('1. Show confirmation dialog')
        self.stdout.write('2. Update UI to "Processing..."')
        self.stdout.write('3. Make POST request to API')
        self.stdout.write('4. Handle response and update UI')
        
        # Check if there are any JavaScript errors in the template
        self.stdout.write('\\n--- POTENTIAL ISSUES ---')
        self.stdout.write('1. JavaScript function not defined')
        self.stdout.write('2. CSRF token missing')
        self.stdout.write('3. API endpoint not found')
        self.stdout.write('4. Network request failing')
        self.stdout.write('5. Response handling error')
        
        # Create a simple test script
        self.stdout.write('\\n--- TEST SCRIPT ---')
        self.stdout.write('Open browser console and run:')
        self.stdout.write(f'approveWithdrawal("{withdrawal.id}")')
        self.stdout.write('This will test if the function exists and works')
        
        self.stdout.write('\\n=== DEBUGGING COMPLETE ===')
