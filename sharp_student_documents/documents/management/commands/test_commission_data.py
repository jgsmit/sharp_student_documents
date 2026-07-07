from django.core.management.base import BaseCommand
from django.db import models
from sales.models import Sale
from documents.models import Order
from withdrawals.models import WithdrawalRequest


class Command(BaseCommand):
    help = 'Test commission data for admin financial templates'

    def handle(self, *args, **options):
        self.stdout.write('=== TESTING COMMISSION DATA ===')
        
        # Test sales data
        sales = Sale.objects.all()
        self.stdout.write(f'\\n--- Sales Data ---')
        self.stdout.write(f'Total sales: {sales.count()}')
        
        for sale in sales[:5]:
            rate_percentage = sale.commission_rate * 100
            self.stdout.write(f'  - Sale #{sale.id}: ${sale.gross_amount} - Commission: ${sale.commission_amount} ({rate_percentage:.2f}%) - Net: ${sale.net_amount}')
        
        # Test commission calculations
        total_commission = sales.aggregate(
            total=models.Sum('commission_amount')
        )['total'] or 0
        
        seller_earnings = sales.aggregate(
            total=models.Sum('net_amount')
        )['total'] or 0
        
        total_sales = sales.aggregate(
            total=models.Sum('gross_amount')
        )['total'] or 0
        
        self.stdout.write(f'\\n--- Commission Summary ---')
        self.stdout.write(f'Total sales: ${total_sales}')
        self.stdout.write(f'Total commission: ${total_commission}')
        self.stdout.write(f'Seller earnings: ${seller_earnings}')
        self.stdout.write(f'Commission rate: {(total_commission / total_sales * 100) if total_sales > 0 else 0:.2f}%')
        
        # Test commission rate statistics
        commission_stats = sales.values('commission_rate').annotate(
            count=models.Count('id'),
            total_commission=models.Sum('commission_amount'),
            total_sales=models.Sum('gross_amount')
        ).order_by('-total_commission')
        
        self.stdout.write(f'\\n--- Commission Rate Statistics ---')
        for stat in commission_stats:
            rate_percentage = stat['commission_rate'] * 100
            self.stdout.write(f'  - {rate_percentage:.2f}%: {stat["count"]} sales, ${stat["total_sales"]} total, ${stat["total_commission"]} commission')
        
        # Test order data for comparison
        orders = Order.objects.filter(status='paid')
        order_revenue = orders.aggregate(
            total=models.Sum('amount_paid')
        )['total'] or 0
        
        self.stdout.write(f'\\n--- Order vs Sales Comparison ---')
        self.stdout.write(f'Paid orders revenue: ${order_revenue}')
        self.stdout.write(f'Sales gross amount: ${total_sales}')
        self.stdout.write(f'Difference: ${abs(order_revenue - total_sales)}')
        
        # Test withdrawal data
        withdrawals = WithdrawalRequest.objects.all()
        total_withdrawn = withdrawals.filter(status='completed').aggregate(
            total=models.Sum('amount')
        )['total'] or 0
        
        self.stdout.write(f'\\n--- Withdrawal Data ---')
        self.stdout.write(f'Total withdrawals: {withdrawals.count()}')
        self.stdout.write(f'Completed withdrawals: ${total_withdrawn}')
        self.stdout.write(f'Seller earnings: ${seller_earnings}')
        self.stdout.write(f'Withdrawals vs earnings difference: ${abs(total_withdrawn - seller_earnings)}')
        
        # Test commission calculation logic
        self.stdout.write(f'\\n--- Commission Calculation Test ---')
        for sale in sales[:3]:
            expected_commission = sale.gross_amount * sale.commission_rate
            expected_net = sale.gross_amount - expected_commission
            
            self.stdout.write(f'  Sale #{sale.id}:')
            self.stdout.write(f'    Gross: ${sale.gross_amount}')
            self.stdout.write(f'    Rate: {sale.commission_rate * 100:.2f}%')
            self.stdout.write(f'    Expected commission: ${expected_commission}')
            self.stdout.write(f'    Actual commission: ${sale.commission_amount}')
            self.stdout.write(f'    Expected net: ${expected_net}')
            self.stdout.write(f'    Actual net: ${sale.net_amount}')
            self.stdout.write(f'    Match: {"PASS" if abs(expected_commission - sale.commission_amount) < 0.01 else "FAIL"}')
        
        self.stdout.write('\\n=== TEMPLATE DATA READY ===')
        self.stdout.write('\\nThe admin templates should now show:')
        self.stdout.write(f'- Total commission: ${total_commission}')
        self.stdout.write(f'- Seller earnings: ${seller_earnings}')
        self.stdout.write(f'- Commission rate: 40%')
        self.stdout.write(f'- Commission breakdown table with {commission_stats.count()} rate(s)')
        self.stdout.write('\\nTemplates updated:')
        self.stdout.write('- admin_view_financials.html')
        self.stdout.write('- admin_manage_withdrawals.html')
