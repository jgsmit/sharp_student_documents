from django.core.management.base import BaseCommand
from django.db.models import Sum
from sales.models import Wallet, Sale
from withdrawals.models import WithdrawalRequest
from decimal import Decimal

class Command(BaseCommand):
    help = 'Fix seller wallet inconsistencies and prevent over-withdrawals'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--fix',
            action='store_true',
            help='Fix all inconsistencies automatically',
        )
        parser.add_argument(
            '--user',
            type=str,
            help='Fix specific user only',
        )
    
    def handle(self, *args, **options):
        self.stdout.write('Seller Wallet Fix Tool')
        self.stdout.write('=' * 40)
        
        # Filter by user if specified
        if options['user']:
            wallets = Wallet.objects.filter(user__username=options['user'])
            self.stdout.write(f'Fixing user: {options["user"]}')
        else:
            wallets = Wallet.objects.all()
            self.stdout.write('Checking all sellers...')
        
        issues_found = 0
        issues_fixed = 0
        
        for wallet in wallets:
            user = wallet.user
            
            # Get actual sales data
            sales = Sale.objects.filter(seller=user)
            total_gross = sales.aggregate(total=Sum('gross_amount'))['total'] or Decimal('0.00')
            total_commission = sales.aggregate(total=Sum('commission_amount'))['total'] or Decimal('0.00')
            total_net = sales.aggregate(total=Sum('net_amount'))['total'] or Decimal('0.00')
            
            # Get actual withdrawal data
            withdrawals = WithdrawalRequest.objects.filter(user=user, status='completed')
            total_withdrawn = withdrawals.aggregate(total=Sum('amount'))['total'] or Decimal('0.00')
            
            # Calculate expected values
            expected_total_earned = total_net  # Should be net amount, not gross
            expected_balance = expected_total_earned - total_withdrawn
            
            # Check for inconsistencies
            has_issues = False
            issues = []
            
            if wallet.total_earned != expected_total_earned:
                issues.append(f'total_earned: {wallet.total_earned} != {expected_total_earned}')
                has_issues = True
            
            if wallet.total_commission_paid != total_commission:
                issues.append(f'total_commission_paid: {wallet.total_commission_paid} != {total_commission}')
                has_issues = True
            
            if wallet.total_withdrawn != total_withdrawn:
                issues.append(f'total_withdrawn: {wallet.total_withdrawn} != {total_withdrawn}')
                has_issues = True
            
            if wallet.balance != expected_balance:
                issues.append(f'balance: {wallet.balance} != {expected_balance}')
                has_issues = True
            
            # Check for over-withdrawal
            if total_withdrawn > total_net:
                issues.append(f'OVER_WITHDRAWN: withdrew {total_withdrawn} but earned {total_net}')
                has_issues = True
            
            if has_issues:
                issues_found += 1
                self.stdout.write(f'\\nISSUE FOUND: {user.username}')
                self.stdout.write(f'  Sales: Gross=${total_gross}, Commission=${total_commission}, Net=${total_net}')
                self.stdout.write(f'  Withdrawals: ${total_withdrawn}')
                self.stdout.write(f'  Current: Earned=${wallet.total_earned}, Withdrawn=${wallet.total_withdrawn}, Balance=${wallet.balance}')
                self.stdout.write(f'  Expected: Earned=${expected_total_earned}, Withdrawn=${total_withdrawn}, Balance=${expected_balance}')
                self.stdout.write(f'  Problems: {", ".join(issues)}')
                
                if options['fix']:
                    # Fix the wallet
                    wallet.total_earned = expected_total_earned
                    wallet.total_commission_paid = total_commission
                    wallet.total_withdrawn = total_withdrawn
                    wallet.balance = expected_balance
                    wallet.save()
                    
                    issues_fixed += 1
                    self.stdout.write(f'  FIXED: New balance=${wallet.balance}')
                else:
                    self.stdout.write(f'  NOT FIXED: Use --fix to apply')
            else:
                self.stdout.write(f'OK {user.username}: Wallet consistent')
        
        self.stdout.write('\\n' + '=' * 40)
        self.stdout.write(f'Issues found: {issues_found}')
        self.stdout.write(f'Issues fixed: {issues_fixed}')
        
        if issues_found > 0 and not options['fix']:
            self.stdout.write('\\nRun with --fix to correct all issues.')
        elif issues_fixed > 0:
            self.stdout.write('\\nAll seller wallet issues have been fixed!')
        else:
            self.stdout.write('\\nAll seller wallets are consistent!')
        
        # Add warning about over-withdrawals
        over_withdrawn = Wallet.objects.filter(
            balance__lt=Decimal('0.00')
        ).count()
        if over_withdrawn > 0:
            self.stdout.write(f'\\nWARNING: {over_withdrawn} sellers have negative balances (over-withdrawn)')
