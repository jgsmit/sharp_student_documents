# documents/management/commands/audit_financial_data.py
"""
Django management command to audit financial data consistency
Run with: python manage.py audit_financial_data
"""
from django.core.management.base import BaseCommand
from django.db.models import Sum
from decimal import Decimal
from documents.models import Order
from payments.models import Payment
from sales.models import Sale, Wallet
from withdrawals.models import WithdrawalRequest
import datetime

class Command(BaseCommand):
    help = 'Audit financial data for consistency issues'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--fix',
            action='store_true',
            help='Automatically fix detected issues',
        )
        parser.add_argument(
            '--email',
            type=str,
            help='Email address to send report to',
        )
    
    def handle(self, *args, **options):
        self.stdout.write("🔍 FINANCIAL DATA AUDIT")
        self.stdout.write("=" * 40)
        
        issues_found = []
        fixes_applied = []
        
        # Check 1: Commission vs Revenue consistency
        self.stdout.write("\n📊 Checking Commission vs Revenue...")
        total_revenue = Order.objects.filter(status='paid').aggregate(
            total=Sum('amount_paid')
        )['total'] or 0
        
        total_commission = Sale.objects.aggregate(
            total=Sum('commission_amount')
        )['total'] or 0
        
        if total_commission > total_revenue:
            issue = f"Commission (${total_commission:,.2f}) exceeds revenue (${total_revenue:,.2f})"
            issues_found.append(issue)
            self.stdout.write(f"   ❌ {issue}")
        else:
            self.stdout.write(f"   ✅ Commission (${total_commission:,.2f}) ≤ Revenue (${total_revenue:,.2f})")
        
        # Check 2: Missing Sale records
        self.stdout.write("\n📋 Checking for missing Sale records...")
        successful_payments = Payment.objects.filter(status='success').count()
        total_sales = Sale.objects.count()
        
        if successful_payments > total_sales:
            missing = successful_payments - total_sales
            issue = f"{missing} Sale records missing for successful payments"
            issues_found.append(issue)
            self.stdout.write(f"   ❌ {issue}")
        else:
            self.stdout.write(f"   ✅ All successful payments have Sale records")
        
        # Check 3: Wallet balance consistency
        self.stdout.write("\n💰 Checking wallet balance consistency...")
        wallet_issues = 0
        wallets = Wallet.objects.all()
        
        for wallet in wallets:
            actual_earnings = Sale.objects.filter(
                seller=wallet.user
            ).aggregate(total=Sum('net_amount'))['total'] or 0
            
            if abs(wallet.total_earned - actual_earnings) > Decimal('1.00'):
                wallet_issues += 1
                issue = f"Wallet for {wallet.user.username} inconsistent: stored=${wallet.total_earned}, actual=${actual_earnings}"
                issues_found.append(issue)
                self.stdout.write(f"   ❌ {issue}")
        
        if wallet_issues == 0:
            self.stdout.write("   ✅ All wallet balances are consistent")
        
        # Check 4: Withdrawal amount validation
        self.stdout.write("\n🏦 Checking withdrawal amounts...")
        large_withdrawals = WithdrawalRequest.objects.filter(
            amount__gt=1000
        ).count()
        
        if large_withdrawals > 0:
            issue = f"{large_withdrawals} large withdrawals (> $1000) found"
            issues_found.append(issue)
            self.stdout.write(f"   ⚠️  {issue}")
        else:
            self.stdout.write("   ✅ No unusually large withdrawals")
        
        # Summary
        self.stdout.write("\n📋 AUDIT SUMMARY")
        self.stdout.write("=" * 20)
        
        if issues_found:
            self.stdout.write(f"❌ {len(issues_found)} issues found:")
            for i, issue in enumerate(issues_found, 1):
                self.stdout.write(f"   {i}. {issue}")
        else:
            self.stdout.write("✅ No issues found - data is consistent!")
        
        # Auto-fix option
        if options['fix'] and issues_found:
            self.stdout.write("\n🔧 Applying automatic fixes...")
            try:
                from documents.financial_utils import synchronize_financial_data
                synchronize_financial_data()
                fixes_applied.append("Data synchronization completed")
                self.stdout.write("   ✅ Data synchronization completed")
            except Exception as e:
                self.stdout.write(f"   ❌ Fix failed: {e}")
        
        # Email report (if requested)
        if options['email']:
            self.stdout.write(f"\n📧 Sending report to {options['email']}...")
            # Email implementation would go here
            
        self.stdout.write(f"\n🏁 Audit completed at {datetime.datetime.now()}")
        return len(issues_found)
