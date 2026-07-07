from django.core.management.base import BaseCommand
from django.db.models import Sum
from sales.models import Wallet
from withdrawals.models import WithdrawalRequest
from decimal import Decimal

class Command(BaseCommand):
    help = 'Sync wallet balances with actual withdrawal history'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--fix',
            action='store_true',
            help='Fix inconsistencies automatically',
        )
        parser.add_argument(
            '--user',
            type=str,
            help='Sync specific user only',
        )
    
    def handle(self, *args, **options):
        self.stdout.write('Wallet-Withdrawal Sync Tool')
        self.stdout.write('=' * 40)
        
        # Filter by user if specified
        if options['user']:
            wallets = Wallet.objects.filter(user__username=options['user'])
            self.stdout.write(f'Syncing user: {options["user"]}')
        else:
            wallets = Wallet.objects.all()
            self.stdout.write('Syncing all users...')
        
        issues_found = 0
        issues_fixed = 0
        
        for wallet in wallets:
            user = wallet.user
            withdrawals = WithdrawalRequest.objects.filter(user=user)
            
            # Calculate actual withdrawn amount
            actual_withdrawn = withdrawals.filter(status='completed').aggregate(
                total=Sum('amount')
            )['total'] or Decimal('0.00')
            
            # Calculate expected balance
            expected_balance = wallet.total_earned - actual_withdrawn
            
            # Check for inconsistencies
            has_issues = False
            issues = []
            
            if wallet.total_withdrawn != actual_withdrawn:
                issues.append(f'total_withdrawn: {wallet.total_withdrawn} != {actual_withdrawn}')
                has_issues = True
            
            if wallet.balance != expected_balance:
                issues.append(f'balance: {wallet.balance} != {expected_balance}')
                has_issues = True
            
            if has_issues:
                issues_found += 1
                self.stdout.write(f'\\nISSUE FOUND: {user.username}')
                self.stdout.write(f'  Current: Balance=${wallet.balance}, Withdrawn=${wallet.total_withdrawn}')
                self.stdout.write(f'  Expected: Balance=${expected_balance}, Withdrawn=${actual_withdrawn}')
                self.stdout.write(f'  Problems: {", ".join(issues)}')
                
                if options['fix']:
                    # Fix the wallet
                    wallet.total_withdrawn = actual_withdrawn
                    wallet.balance = expected_balance
                    wallet.save()
                    
                    issues_fixed += 1
                    self.stdout.write(f'  FIXED: New balance=${wallet.balance}')
                else:
                    self.stdout.write(f'  NOT FIXED: Use --fix to apply')
            else:
                self.stdout.write(f'OK {user.username}: Balance consistent')
        
        self.stdout.write('\\n' + '=' * 40)
        self.stdout.write(f'Issues found: {issues_found}')
        self.stdout.write(f'Issues fixed: {issues_fixed}')
        
        if issues_found > 0 and not options['fix']:
            self.stdout.write('\\nRun with --fix to correct all issues.')
        elif issues_fixed > 0:
            self.stdout.write('\\nAll issues have been fixed!')
        else:
            self.stdout.write('\\nAll wallet balances are consistent!')
