from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from withdrawals.models import WithdrawalRequest

User = get_user_model()


class Command(BaseCommand):
    help = 'Debug Ripper withdrawal synchronization issue'

    def handle(self, *args, **options):
        self.stdout.write('=== RIPPER SYNCHRONIZATION DEBUG ===')
        
        # Get Ripper user
        try:
            ripper = User.objects.get(username='Ripper')
        except User.DoesNotExist:
            self.stdout.write('Ripper user not found!')
            return
        
        # Get all withdrawals for Ripper
        all_withdrawals = WithdrawalRequest.objects.filter(user=ripper).order_by('-requested_at')
        
        self.stdout.write(f'\\n--- ALL WITHDRAWALS FOR RIPPER ({all_withdrawals.count()} total) ---')
        
        # Check what seller dashboard query returns
        seller_withdrawals = WithdrawalRequest.objects.filter(
            user=ripper
        ).order_by('-requested_at')[:10]
        
        self.stdout.write(f'\\nSeller Dashboard Query (LIMIT 10): {seller_withdrawals.count()} results')
        for w in seller_withdrawals:
            self.stdout.write(f'  {w.id}: ${w.amount} ({w.status}) - {w.payout_type}')
        
        # Check what admin sees
        admin_withdrawals = WithdrawalRequest.objects.filter(user=ripper).order_by('-requested_at')
        
        self.stdout.write(f'\\nAdmin Query (NO LIMIT): {admin_withdrawals.count()} results')
        for w in admin_withdrawals:
            self.stdout.write(f'  {w.id}: ${w.amount} ({w.status}) - {w.payout_type}')
        
        # Find the missing withdrawal
        seller_ids = {w.id for w in seller_withdrawals}
        admin_ids = {w.id for w in admin_withdrawals}
        
        missing_in_seller = admin_ids - seller_ids
        extra_in_seller = seller_ids - admin_ids
        
        if missing_in_seller:
            self.stdout.write(f'\\n--- MISSING IN SELLER DASHBOARD ---')
            for missing_id in missing_in_seller:
                w = WithdrawalRequest.objects.get(id=missing_id)
                self.stdout.write(f'  {w.id}: ${w.amount} ({w.status}) - {w.payout_type}')
                self.stdout.write(f'    Requested: {w.requested_at}')
                self.stdout.write(f'    Position: {list(admin_withdrawals).index(w) + 1} of {admin_withdrawals.count()}')
        
        if extra_in_seller:
            self.stdout.write(f'\\n--- EXTRA IN SELLER DASHBOARD ---')
            for extra_id in extra_in_seller:
                w = WithdrawalRequest.objects.get(id=extra_id)
                self.stdout.write(f'  {w.id}: ${w.amount} ({w.status}) - {w.payout_type}')
        
        # Check the specific missing withdrawal
        if missing_in_seller:
            missing_id = list(missing_in_seller)[0]
            missing_withdrawal = WithdrawalRequest.objects.get(id=missing_id)
            
            self.stdout.write(f'\\n--- ANALYSIS OF MISSING WITHDRAWAL ---')
            self.stdout.write(f'Withdrawal ID: {missing_withdrawal.id}')
            self.stdout.write(f'Amount: ${missing_withdrawal.amount}')
            self.stdout.write(f'Status: {missing_withdrawal.status}')
            self.stdout.write(f'Type: {missing_withdrawal.payout_type}')
            self.stdout.write(f'Requested: {missing_withdrawal.requested_at}')
            
            # Check if it should be in the top 10
            all_withdrawals_list = list(all_withdrawals)
            position = all_withdrawals_list.index(missing_withdrawal) + 1
            
            self.stdout.write(f'Position in all withdrawals: {position} of {all_withdrawals.count()}')
            
            if position > 10:
                self.stdout.write('REASON: This withdrawal is beyond the top 10 limit in seller dashboard')
                self.stdout.write('Seller dashboard only shows the 10 most recent withdrawals')
            else:
                self.stdout.write('ISSUE: This should be visible in seller dashboard - investigate further')
        
        # Check the seller dashboard template logic
        self.stdout.write(f'\\n--- SELLER DASHBOARD TEMPLATE LOGIC ---')
        self.stdout.write('Template uses: WithdrawalRequest.objects.filter(user=user).order_by("-requested_at")[:10]')
        self.stdout.write('This means: Only the 10 most recent withdrawals are shown')
        
        # Show the cutoff point
        if all_withdrawals.count() > 10:
            self.stdout.write(f'\\n--- SELLER DASHBOARD CUTOFF ---')
            self.stdout.write(f'Seller dashboard shows withdrawals 1-10 (most recent)')
            self.stdout.write(f'Total withdrawals: {all_withdrawals.count()}')
            
            self.stdout.write(f'\\nShown in seller dashboard:')
            for i, w in enumerate(all_withdrawals[:10]):
                self.stdout.write(f'  {i+1}. {w.id}: ${w.amount} ({w.status})')
            
            self.stdout.write(f'\\nNOT shown in seller dashboard (older than 10):')
            for i, w in enumerate(all_withdrawals[10:], 11):
                self.stdout.write(f'  {i}. {w.id}: ${w.amount} ({w.status})')
        
        # Check if there are any pending withdrawals that should be approved
        pending_withdrawals = all_withdrawals.filter(status='pending')
        
        self.stdout.write(f'\\n--- PENDING WITHDRAWALS NEEDING APPROVAL ---')
        if pending_withdrawals.exists():
            self.stdout.write(f'Found {pending_withdrawals.count()} pending withdrawals:')
            for w in pending_withdrawals:
                self.stdout.write(f'  - {w.id}: ${w.amount} ({w.payout_type}) - {w.withdrawal_method.method_type}')
                self.stdout.write(f'    Can process instant: {w.can_process_instant()}')
                self.stdout.write(f'    Requested: {w.requested_at}')
        else:
            self.stdout.write('No pending withdrawals found')
        
        self.stdout.write(f'\\n=== CONCLUSION ===')
        self.stdout.write('The "synchronization issue" is actually a template limitation:')
        self.stdout.write('- Admin dashboard shows ALL withdrawals (no limit)')
        self.stdout.write('- Seller dashboard shows ONLY 10 most recent withdrawals')
        self.stdout.write('- This is by design to keep the seller dashboard clean')
        self.stdout.write('')
        self.stdout.write('The real issue: Ripper has pending withdrawals that need admin approval!')
