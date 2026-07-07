from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from withdrawals.models import WithdrawalRequest, WithdrawalMethod
from sales.models import Wallet

User = get_user_model()


class Command(BaseCommand):
    help = 'Check Ripper seller account withdrawal dashboard synchronization'

    def handle(self, *args, **options):
        self.stdout.write('=== RIPPER SELLER ACCOUNT ANALYSIS ===')
        
        # Get Ripper user account
        try:
            ripper = User.objects.get(username='Ripper')
            self.stdout.write(f'\\n--- RIPPER USER INFO ---')
            self.stdout.write(f'Username: {ripper.username}')
            self.stdout.write(f'Email: {ripper.email}')
            self.stdout.write(f'Is Superuser: {ripper.is_superuser}')
            self.stdout.write(f'Is Staff: {ripper.is_staff}')
            self.stdout.write(f'Is Active: {ripper.is_active}')
        except User.DoesNotExist:
            self.stdout.write('Ripper user not found!')
            return
        
        # Check Ripper's withdrawal methods
        self.stdout.write(f'\\n--- RIPPER WITHDRAWAL METHODS ---')
        withdrawal_methods = WithdrawalMethod.objects.filter(user=ripper, is_active=True)
        if withdrawal_methods.exists():
            for method in withdrawal_methods:
                self.stdout.write(f'Method: {method.method_type}')
                self.stdout.write(f'  PayPal Email: {method.paypal_email}')
                self.stdout.write(f'  Stripe Account: {method.stripe_account_id}')
                self.stdout.write(f'  Bank Name: {method.bank_name}')
                self.stdout.write(f'  Is Active: {method.is_active}')
                self.stdout.write(f'  Created: {method.created_at}')
        else:
            self.stdout.write('No active withdrawal methods found for Ripper')
        
        # Check Ripper's wallet balance
        self.stdout.write(f'\\n--- RIPPER WALLET ---')
        try:
            wallet = Wallet.objects.get(user=ripper)
            self.stdout.write(f'Balance: ${wallet.balance}')
            self.stdout.write(f'Last Updated: {wallet.updated_at}')
        except Wallet.DoesNotExist:
            self.stdout.write('No wallet found for Ripper')
        
        # Check all Ripper's withdrawal requests
        self.stdout.write(f'\\n--- RIPPER WITHDRAWAL REQUESTS ---')
        withdrawals = WithdrawalRequest.objects.filter(user=ripper).order_by('-requested_at')
        
        if not withdrawals.exists():
            self.stdout.write('No withdrawal requests found for Ripper')
            return
        
        self.stdout.write(f'Total withdrawal requests: {withdrawals.count()}')
        
        for withdrawal in withdrawals:
            self.stdout.write(f'\\n--- Withdrawal #{withdrawal.id} ---')
            self.stdout.write(f'Amount: ${withdrawal.amount}')
            self.stdout.write(f'Type: {withdrawal.payout_type}')
            self.stdout.write(f'Status: {withdrawal.status}')
            self.stdout.write(f'Method: {withdrawal.withdrawal_method.method_type}')
            self.stdout.write(f'Requested: {withdrawal.requested_at}')
            self.stdout.write(f'Processed: {withdrawal.processed_at}')
            self.stdout.write(f'Completed: {withdrawal.completed_at}')
            self.stdout.write(f'Fee: ${withdrawal.fee}')
            self.stdout.write(f'Net Amount: ${withdrawal.net_amount}')
            
            if withdrawal.failure_reason:
                self.stdout.write(f'Failure Reason: {withdrawal.failure_reason}')
            
            # Check if it can process instant
            can_instant = withdrawal.can_process_instant()
            self.stdout.write(f'Can Process Instant: {can_instant}')
            
            # Show expected flow
            if withdrawal.status == 'pending':
                if can_instant:
                    self.stdout.write(f'Expected Flow: pending -> processing -> completed (instant)')
                else:
                    self.stdout.write(f'Expected Flow: pending -> processing -> pending (weekly queue)')
        
        # Check what seller dashboard would show
        self.stdout.write(f'\\n--- SELLER DASHBOARD DATA FOR RIPPER ---')
        
        # Recent withdrawals (same query as dashboard)
        recent_withdrawals = WithdrawalRequest.objects.filter(
            user=ripper
        ).order_by('-requested_at')[:10]
        
        self.stdout.write(f'Recent Withdrawals Count: {recent_withdrawals.count()}')
        for w in recent_withdrawals:
            self.stdout.write(f'  - #{w.id}: ${w.amount} ({w.status}) - {w.payout_type}')
        
        # Pending withdrawals calculation
        pending_withdrawals = WithdrawalRequest.objects.filter(
            user=ripper,
            status__in=['pending', 'processing', '2fa_required']
        )
        
        pending_amount = sum(w.amount for w in pending_withdrawals)
        self.stdout.write(f'Pending Withdrawals: ${pending_amount} ({pending_withdrawals.count()} requests)')
        
        # Completed withdrawals calculation
        completed_withdrawals = WithdrawalRequest.objects.filter(
            user=ripper,
            status='completed'
        )
        
        completed_amount = sum(w.amount for w in completed_withdrawals)
        self.stdout.write(f'Completed Withdrawals: ${completed_amount} ({completed_withdrawals.count()} requests)')
        
        # Check balance calculation
        try:
            wallet = Wallet.objects.get(user=ripper)
            self.stdout.write(f'\\n--- BALANCE VERIFICATION ---')
            self.stdout.write(f'Current Wallet Balance: ${wallet.balance}')
            self.stdout.write(f'Pending Amount: ${pending_amount}')
            self.stdout.write(f'Completed Amount: ${completed_amount}')
            self.stdout.write(f'Total Requested: ${pending_amount + completed_amount}')
            
            # Check if balance makes sense
            if wallet.balance >= 0:
                self.stdout.write(f'Balance Status: OK (non-negative)')
            else:
                self.stdout.write(f'Balance Status: WARNING (negative balance)')
        except Wallet.DoesNotExist:
            self.stdout.write('No wallet to verify balance')
        
        # Check admin view of this withdrawal
        self.stdout.write(f'\\n--- ADMIN VIEW OF RIPPER WITHDRAWALS ---')
        admin_withdrawals = WithdrawalRequest.objects.filter(user=ripper).order_by('-requested_at')
        self.stdout.write(f'Admin sees {admin_withdrawals.count()} withdrawals for Ripper:')
        
        for w in admin_withdrawals:
            self.stdout.write(f'  - #{w.id}: ${w.amount} ({w.status}) - {w.payout_type} - {w.withdrawal_method.method_type}')
        
        # Check if there are any discrepancies
        self.stdout.write(f'\\n--- SYNCHRONIZATION CHECK ---')
        seller_count = recent_withdrawals.count()
        admin_count = admin_withdrawals.count()
        
        self.stdout.write(f'Seller Dashboard Count: {seller_count}')
        self.stdout.write(f'Admin Dashboard Count: {admin_count}')
        self.stdout.write(f'Synchronization: {"OK" if seller_count == admin_count else "MISMATCH"}')
        
        if seller_count != admin_count:
            self.stdout.write('WARNING: Synchronization issue detected!')
        
        # Check specific withdrawal statuses
        self.stdout.write(f'\\n--- STATUS BREAKDOWN ---')
        status_counts = {}
        for withdrawal in withdrawals:
            status = withdrawal.status
            if status not in status_counts:
                status_counts[status] = 0
            status_counts[status] += 1
        
        for status, count in status_counts.items():
            self.stdout.write(f'{status.upper()}: {count} withdrawals')
        
        self.stdout.write(f'\\n=== RECOMMENDATIONS ===')
        
        pending_count = status_counts.get('pending', 0)
        if pending_count > 0:
            self.stdout.write('\\n1. Ripper has pending withdrawals that need admin approval')
            self.stdout.write('2. Check admin dashboard for pending withdrawals from Ripper')
            self.stdout.write('3. Approve withdrawals in admin panel to update status')
        
        failed_count = status_counts.get('failed', 0)
        if failed_count > 0:
            self.stdout.write('\\n4. Some withdrawals failed - check failure reasons')
            self.stdout.write('5. Ripper may need to update withdrawal method or try again')
        
        if wallet.balance > 0 and pending_count == 0:
            self.stdout.write('\\n6. Ripper has balance but no pending withdrawals')
            self.stdout.write('7. Ripper can request new withdrawal from seller dashboard')
        
        self.stdout.write('\\n=== TROUBLESHOOTING STEPS ===')
        self.stdout.write('If Ripper sees no changes on dashboard:')
        self.stdout.write('1. Refresh the seller dashboard page (Ctrl+F5)')
        self.stdout.write('2. Check if withdrawal requests were created successfully')
        self.stdout.write('3. Verify withdrawal method is set up correctly')
        self.stdout.write('4. Check if wallet has sufficient balance')
        self.stdout.write('5. Look for any error messages during withdrawal request')
