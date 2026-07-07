from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from withdrawals.models import WithdrawalRequest
from sales.models import Wallet

User = get_user_model()


class Command(BaseCommand):
    help = 'Test withdrawal synchronization between admin and seller dashboard'

    def handle(self, *args, **options):
        self.stdout.write('=== WITHDRAWAL SYNCHRONIZATION TEST ===')
        
        # Get all withdrawal requests
        withdrawals = WithdrawalRequest.objects.all().order_by('-requested_at')
        
        self.stdout.write(f'\\n--- WITHDRAWAL REQUESTS OVERVIEW ---')
        self.stdout.write(f'Total withdrawal requests: {withdrawals.count()}')
        
        if not withdrawals.exists():
            self.stdout.write('No withdrawal requests found. Creating test scenario...')
            self.stdout.write('Please create a withdrawal request first to test synchronization.')
            return
        
        # Check each withdrawal status
        self.stdout.write(f'\\n--- WITHDRAWAL STATUS BREAKDOWN ---')
        status_counts = {}
        for withdrawal in withdrawals:
            status = withdrawal.status
            if status not in status_counts:
                status_counts[status] = []
            status_counts[status].append(withdrawal)
        
        for status, withdrawal_list in status_counts.items():
            self.stdout.write(f'\\n{status.upper()}: {len(withdrawal_list)} withdrawals')
            for withdrawal in withdrawal_list[:3]:  # Show first 3 of each status
                self.stdout.write(f'  - #{withdrawal.id}: ${withdrawal.amount} for {withdrawal.user.username}')
                self.stdout.write(f'    Requested: {withdrawal.requested_at}')
                self.stdout.write(f'    Method: {withdrawal.withdrawal_method.method_type}')
                self.stdout.write(f'    Type: {withdrawal.payout_type}')
                if withdrawal.processed_at:
                    self.stdout.write(f'    Processed: {withdrawal.processed_at}')
                if withdrawal.completed_at:
                    self.stdout.write(f'    Completed: {withdrawal.completed_at}')
                if withdrawal.failure_reason:
                    self.stdout.write(f'    Failure Reason: {withdrawal.failure_reason}')
        
        # Check seller dashboard data
        self.stdout.write(f'\\n--- SELLER DASHBOARD DATA VERIFICATION ---')
        for withdrawal in withdrawals[:5]:  # Check first 5 withdrawals
            user = withdrawal.user
            
            # Get user's recent withdrawals (same query as seller dashboard)
            recent_withdrawals = WithdrawalRequest.objects.filter(
                user=user
            ).order_by('-requested_at')[:10]
            
            # Check if this withdrawal appears in user's dashboard
            user_withdrawal_ids = [w.id for w in recent_withdrawals]
            is_in_dashboard = withdrawal.id in user_withdrawal_ids
            
            self.stdout.write(f'\\nWithdrawal #{withdrawal.id} for {user.username}:')
            self.stdout.write(f'  Status: {withdrawal.status}')
            self.stdout.write(f'  In Seller Dashboard: {"YES" if is_in_dashboard else "NO"}')
            
            # Check pending withdrawals calculation
            pending_withdrawals = WithdrawalRequest.objects.filter(
                user=user,
                status__in=['pending', 'processing', '2fa_required']
            )
            
            pending_amount = sum(w.amount for w in pending_withdrawals)
            self.stdout.write(f'  User Pending Withdrawals: ${pending_amount} ({pending_withdrawals.count()} requests)')
            
            # Check completed withdrawals calculation
            completed_withdrawals = WithdrawalRequest.objects.filter(
                user=user,
                status='completed'
            )
            
            completed_amount = sum(w.amount for w in completed_withdrawals)
            self.stdout.write(f'  User Completed Withdrawals: ${completed_amount} ({completed_withdrawals.count()} requests)')
        
        # Check wallet balances
        self.stdout.write(f'\n--- WALLET BALANCE VERIFICATION ---')
        users_with_withdrawals = WithdrawalRequest.objects.values_list('user', flat=True).distinct()
        
        for user_id in users_with_withdrawals:
            try:
                user = User.objects.get(id=user_id)
                wallet = Wallet.objects.get(user=user)
                
                user_withdrawals = WithdrawalRequest.objects.filter(user=user)
                total_requested = sum(w.amount for w in user_withdrawals)
                completed_amount = sum(w.amount for w in user_withdrawals.filter(status='completed'))
                pending_amount = sum(w.amount for w in user_withdrawals.filter(status__in=['pending', 'processing', '2fa_required']))
                
                self.stdout.write(f'\\nUser: {user.username}')
                self.stdout.write(f'  Wallet Balance: ${wallet.balance}')
                self.stdout.write(f'  Total Requested: ${total_requested}')
                self.stdout.write(f'  Completed: ${completed_amount}')
                self.stdout.write(f'  Pending: ${pending_amount}')
                self.stdout.write(f'  Balance + Pending + Completed: ${wallet.balance + pending_amount + completed_amount}')
                
            except Wallet.DoesNotExist:
                self.stdout.write(f'User {user.username}: No wallet found')
            except User.DoesNotExist:
                self.stdout.write(f'User ID {user_id}: User not found')
        
        # Test admin approval flow
        self.stdout.write(f'\\n--- ADMIN APPROVAL FLOW TEST ---')
        pending_withdrawals = WithdrawalRequest.objects.filter(status='pending')
        
        if pending_withdrawals.exists():
            self.stdout.write(f'Found {pending_withdrawals.count()} pending withdrawals:')
            for withdrawal in pending_withdrawals:
                self.stdout.write(f'\\n  Withdrawal #{withdrawal.id}:')
                self.stdout.write(f'    User: {withdrawal.user.username}')
                self.stdout.write(f'    Amount: ${withdrawal.amount}')
                self.stdout.write(f'    Current Status: {withdrawal.status}')
                self.stdout.write(f'    Can Process Instant: {withdrawal.can_process_instant()}')
                
                # Simulate what happens when admin approves
                if withdrawal.can_process_instant():
                    self.stdout.write(f'    Expected Flow: pending -> processing -> completed')
                else:
                    self.stdout.write(f'    Expected Flow: pending -> processing -> pending (weekly queue)')
        else:
            self.stdout.write('No pending withdrawals found to test approval flow.')
        
        self.stdout.write(f'\\n=== SYNCHRONIZATION ANALYSIS ===')
        self.stdout.write('\\nWhat happens when admin approves a withdrawal:')
        self.stdout.write('1. Admin clicks "Approve" -> calls approve_withdrawal() in admin_views.py')
        self.stdout.write('2. Status changes from "pending" -> "processing"')
        self.stdout.write('3. WithdrawalService.process_instant_withdrawal() is called')
        self.stdout.write('4. Payment is processed via Stripe/PayPal')
        self.stdout.write('5. Status changes to "completed" if successful, "failed" if error')
        self.stdout.write('\\nSeller dashboard should show updated status immediately because:')
        self.stdout.write('- It queries WithdrawalRequest.objects.filter(user=request.user) each time')
        self.stdout.write('- Status is stored in database and retrieved fresh each page load')
        self.stdout.write('- No caching involved in withdrawal status display')
        
        self.stdout.write('\\n=== TROUBLESHOOTING TIPS ===')
        self.stdout.write('If seller dashboard still shows "pending" after admin approval:')
        self.stdout.write('1. Check withdrawal status in database (should be "completed")')
        self.stdout.write('2. Refresh seller dashboard page (hard refresh: Ctrl+F5)')
        self.stdout.write('3. Check browser console for JavaScript errors')
        self.stdout.write('4. Verify admin approval completed successfully (check for error messages)')
        self.stdout.write('5. Check if payment processing failed (status would be "failed")')
