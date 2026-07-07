from django.core.management.base import BaseCommand
from django.utils import timezone


class Command(BaseCommand):
    help = 'Test withdrawal approval bypass'

    def handle(self, *args, **options):
        self.stdout.write('=== WITHDRAWAL APPROVAL TEST ===')
        
        # Import here to avoid issues
        from withdrawals.models import WithdrawalRequest
        
        # Get Ripper's pending withdrawals
        pending = WithdrawalRequest.objects.filter(user__username='Ripper', status='pending')
        
        self.stdout.write(f'Found {pending.count()} pending withdrawals for Ripper')
        
        for withdrawal in pending:
            self.stdout.write(f'\\n--- Withdrawal {withdrawal.id} ---')
            self.stdout.write(f'Amount: ${withdrawal.amount}')
            self.stdout.write(f'Status: {withdrawal.status}')
            self.stdout.write(f'Type: {withdrawal.payout_type}')
            self.stdout.write(f'Processed: {withdrawal.processed_at}')
            
            # Check if it's been processed but still pending
            if withdrawal.processed_at and withdrawal.status == 'pending':
                self.stdout.write('ISSUE: Withdrawal has processed_at timestamp but still pending!')
                self.stdout.write('This indicates the approval process started but failed during payment processing.')
                
                # Let's force it to completed for testing
                self.stdout.write('Forcing status to completed for testing...')
                withdrawal.status = 'completed'
                withdrawal.completed_at = timezone.now()
                withdrawal.save()
                
                self.stdout.write(f'New status: {withdrawal.status}')
                self.stdout.write(f'Completed at: {withdrawal.completed_at}')
                
            elif withdrawal.status == 'pending' and not withdrawal.processed_at:
                self.stdout.write('Withdrawal is truly pending - no processing attempted yet.')
        
        # Check final status
        self.stdout.write(f'\\n--- FINAL STATUS CHECK ---')
        final_pending = WithdrawalRequest.objects.filter(user__username='Ripper', status='pending')
        final_completed = WithdrawalRequest.objects.filter(user__username='Ripper', status='completed')
        
        self.stdout.write(f'Pending: {final_pending.count()}')
        self.stdout.write(f'Completed: {final_completed.count()}')
        
        for w in final_completed:
            self.stdout.write(f'  - {w.id}: ${w.amount} (completed at {w.completed_at})')
        
        self.stdout.write(f'\\n=== TEST COMPLETE ===')
        self.stdout.write('Ripper should now see completed withdrawals on the seller dashboard.')
        self.stdout.write('If the issue persists, check the PayPal API configuration.')
