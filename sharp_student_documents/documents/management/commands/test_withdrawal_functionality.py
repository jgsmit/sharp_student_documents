from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from withdrawals.models import WithdrawalRequest
from withdrawals.services import WithdrawalService
from django.utils import timezone


class Command(BaseCommand):
    help = 'Test withdrawal approval functionality directly'

    def handle(self, *args, **options):
        self.stdout.write('=== TESTING WITHDRAWAL APPROVAL FUNCTIONALITY ===')
        
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
        self.stdout.write(f'Type: {withdrawal.payout_type}')
        self.stdout.write(f'Can process instant: {withdrawal.can_process_instant()}')
        
        # Test the withdrawal service directly
        self.stdout.write('\\n--- Testing Withdrawal Service ---')
        
        try:
            # Test instant processing
            if withdrawal.can_process_instant():
                self.stdout.write('Processing as instant withdrawal...')
                result = WithdrawalService.process_instant_withdrawal(withdrawal)
                self.stdout.write(f'Instant withdrawal result: {result}')
            else:
                self.stdout.write('Processing as weekly withdrawal...')
                result = WithdrawalService.queue_weekly_withdrawal(withdrawal)
                self.stdout.write(f'Weekly withdrawal result: {result}')
            
            # Check the updated status
            withdrawal.refresh_from_db()
            self.stdout.write(f'New status: {withdrawal.status}')
            
            if withdrawal.paypal_payout_id:
                self.stdout.write(f'PayPal payout ID: {withdrawal.paypal_payout_id}')
                self.stdout.write('SUCCESS: PayPal payout created!')
            else:
                self.stdout.write('No PayPal payout ID (weekly withdrawal)')
            
        except Exception as e:
            self.stdout.write(f'ERROR in withdrawal service: {e}')
        
        # Create a new test withdrawal to test the admin approval flow
        self.stdout.write('\\n--- Creating New Test Withdrawal ---')
        
        try:
            # Create a new withdrawal request
            new_withdrawal = WithdrawalRequest.objects.create(
                user=admin_user,  # Use admin as seller for testing
                withdrawal_method=withdrawal.withdrawal_method,
                amount=25.00,  # Small amount for instant processing
                payout_type='instant'
            )
            
            self.stdout.write(f'Created new withdrawal: {new_withdrawal.id}')
            self.stdout.write(f'Amount: ${new_withdrawal.amount}')
            self.stdout.write(f'Status: {new_withdrawal.status}')
            
            # Test admin approval flow
            self.stdout.write('\\n--- Simulating Admin Approval ---')
            
            # Update status to processing (like admin approval does)
            new_withdrawal.status = 'processing'
            new_withdrawal.processed_at = timezone.now()
            new_withdrawal.save()
            
            # Process the withdrawal
            result = WithdrawalService.process_instant_withdrawal(new_withdrawal)
            self.stdout.write(f'Processing result: {result}')
            
            # Check final status
            new_withdrawal.refresh_from_db()
            self.stdout.write(f'Final status: {new_withdrawal.status}')
            
            if new_withdrawal.paypal_payout_id:
                self.stdout.write(f'PayPal payout ID: {new_withdrawal.paypal_payout_id}')
                self.stdout.write('SUCCESS: Complete withdrawal flow tested!')
            else:
                self.stdout.write('ERROR: No PayPal payout created')
            
        except Exception as e:
            self.stdout.write(f'ERROR in test withdrawal: {e}')
        
        self.stdout.write('\\n=== TEST COMPLETE ===')
