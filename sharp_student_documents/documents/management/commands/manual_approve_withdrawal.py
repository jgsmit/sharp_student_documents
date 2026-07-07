from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.utils import timezone

User = get_user_model()

# Import after User to avoid circular imports
from withdrawals.models import WithdrawalRequest
from withdrawals.services import WithdrawalService


class Command(BaseCommand):
    help = 'Manually approve a withdrawal to bypass frontend issues'

    def add_arguments(self, parser):
        parser.add_argument('withdrawal_id', type=str, help='Withdrawal ID to approve')

    def handle(self, *args, **options):
        withdrawal_id = options['withdrawal_id']
        
        self.stdout.write(f'=== MANUAL APPROVAL OF WITHDRAWAL {withdrawal_id} ===')
        
        try:
            withdrawal = WithdrawalRequest.objects.get(id=withdrawal_id)
        except Exception as e:
            self.stdout.write(f'Withdrawal {withdrawal_id} not found! Error: {e}')
            return
        
        self.stdout.write(f'\\n--- WITHDRAWAL DETAILS ---')
        self.stdout.write(f'User: {withdrawal.user.username}')
        self.stdout.write(f'Amount: ${withdrawal.amount}')
        self.stdout.write(f'Type: {withdrawal.payout_type}')
        self.stdout.write(f'Status: {withdrawal.status}')
        self.stdout.write(f'Method: {withdrawal.withdrawal_method.method_type}')
        self.stdout.write(f'Requested: {withdrawal.requested_at}')
        self.stdout.write(f'Processed: {withdrawal.processed_at}')
        self.stdout.write(f'Completed: {withdrawal.completed_at}')
        
        if withdrawal.failure_reason:
            self.stdout.write(f'Failure Reason: {withdrawal.failure_reason}')
        
        # Check if it's already processed
        if withdrawal.status != 'pending':
            self.stdout.write(f'\\nWithdrawal is not pending (status: {withdrawal.status})')
            self.stdout.write('Cannot approve - withdrawal already processed')
            return
        
        # Simulate admin approval process
        self.stdout.write(f'\\n--- SIMULATING ADMIN APPROVAL ---')
        
        try:
            # Step 1: Update status to processing
            self.stdout.write('Step 1: Changing status to processing...')
            withdrawal.status = 'processing'
            withdrawal.processed_at = timezone.now()
            withdrawal.save()
            
            self.stdout.write(f'Status updated to: {withdrawal.status}')
            self.stdout.write(f'Processed at: {withdrawal.processed_at}')
            
            # Step 2: Process the withdrawal
            self.stdout.write('\\nStep 2: Processing withdrawal...')
            
            if withdrawal.can_process_instant():
                self.stdout.write('Processing as instant withdrawal...')
                result = WithdrawalService.process_instant_withdrawal(withdrawal)
                self.stdout.write(f'Instant processing result: {result}')
                
                if result:
                    self.stdout.write('SUCCESS: Withdrawal completed instantly')
                else:
                    self.stdout.write('FAILED: Instant processing failed')
            else:
                self.stdout.write('Processing as weekly withdrawal...')
                result = WithdrawalService.queue_weekly_withdrawal(withdrawal)
                self.stdout.write(f'Weekly processing result: {result}')
                
                if result:
                    self.stdout.write('SUCCESS: Withdrawal queued for weekly processing')
                else:
                    self.stdout.write('FAILED: Weekly processing failed')
            
            # Step 3: Check final status
            withdrawal.refresh_from_db()
            self.stdout.write(f'\\n--- FINAL STATUS ---')
            self.stdout.write(f'Status: {withdrawal.status}')
            self.stdout.write(f'Processed: {withdrawal.processed_at}')
            self.stdout.write(f'Completed: {withdrawal.completed_at}')
            
            if withdrawal.failure_reason:
                self.stdout.write(f'Failure Reason: {withdrawal.failure_reason}')
            
            # Step 4: Update seller dashboard calculations
            self.stdout.write(f'\\n--- SELLER DASHBOARD IMPACT ---')
            
            # Recalculate pending withdrawals
            from withdrawals.models import WithdrawalRequest
            pending_withdrawals = WithdrawalRequest.objects.filter(
                user=withdrawal.user,
                status__in=['pending', 'processing', '2fa_required']
            )
            
            pending_amount = sum(w.amount for w in pending_withdrawals)
            self.stdout.write(f'User pending withdrawals: ${pending_amount} ({pending_withdrawals.count()} requests)')
            
            # Recalculate completed withdrawals
            completed_withdrawals = WithdrawalRequest.objects.filter(
                user=withdrawal.user,
                status='completed'
            )
            
            completed_amount = sum(w.amount for w in completed_withdrawals)
            self.stdout.write(f'User completed withdrawals: ${completed_amount} ({completed_withdrawals.count()} requests)')
            
            self.stdout.write(f'\\n=== APPROVAL COMPLETE ===')
            self.stdout.write('The withdrawal has been manually processed.')
            self.stdout.write('Ripper should refresh the seller dashboard to see the changes.')
            
        except Exception as e:
            self.stdout.write(f'\\nERROR during approval: {e}')
            self.stdout.write('Rolling back status changes...')
            
            # Rollback the status change
            withdrawal.status = 'pending'
            withdrawal.processed_at = None
            withdrawal.save()
            
            self.stdout.write(f'Status rolled back to: {withdrawal.status}')
            
            # Provide troubleshooting info
            self.stdout.write(f'\\n--- TROUBLESHOOTING INFO ---')
            self.stdout.write('The approval failed. Possible causes:')
            self.stdout.write('1. PayPal API not configured')
            self.stdout.write('2. Invalid PayPal credentials')
            self.stdout.write('3. Network connectivity issues')
            self.stdout.write('4. Insufficient permissions')
            self.stdout.write('5. Withdrawal method configuration issues')
            
            # Check PayPal configuration
            try:
                from django.conf import settings
                paypal_configured = hasattr(settings, 'PAYPAL_REST_API') and settings.PAYPAL_REST_API
                self.stdout.write(f'\\nPayPal configured: {paypal_configured}')
                
                if not paypal_configured:
                    self.stdout.write('RECOMMENDATION: Configure PayPal API in settings')
            except Exception as config_error:
                self.stdout.write(f'Configuration check error: {config_error}')
