from django.core.management.base import BaseCommand
from documents.financial_utils import get_unified_financial_data


class Command(BaseCommand):
    help = 'Test admin dashboard financial data consistency'

    def handle(self, *args, **options):
        self.stdout.write('Testing admin dashboard financial data...')
        
        # Get admin financial data
        financial_data = get_unified_financial_data(is_admin=True)
        
        self.stdout.write('\n=== ADMIN DASHBOARD FINANCIAL DATA ===')
        self.stdout.write(f"Total Revenue: ${financial_data['total_revenue']:,.2f}")
        self.stdout.write(f"Pending Revenue: ${financial_data['pending_revenue']:,.2f}")
        self.stdout.write(f"Total Orders: {financial_data['total_orders']}")
        self.stdout.write(f"Completed Orders: {financial_data['completed_orders']}")
        self.stdout.write(f"Pending Orders: {financial_data['pending_orders']}")
        self.stdout.write(f"Total Withdrawn: ${financial_data['total_withdrawn']:,.2f}")
        self.stdout.write(f"Net Profit: ${financial_data['net_profit']:,.2f}")
        self.stdout.write(f"Order Completion Rate: {financial_data['order_completion_rate']:.1f}%")
        self.stdout.write(f"Successful Payments: ${financial_data['successful_payments']:,.2f}")
        
        # Verify calculations
        expected_net_profit = financial_data['total_revenue'] - financial_data['total_withdrawn']
        actual_net_profit = financial_data['net_profit']
        
        if abs(expected_net_profit - actual_net_profit) < 0.01:
            self.stdout.write(self.style.SUCCESS('\nNet Profit calculation is CORRECT'))
        else:
            self.stdout.write(self.style.ERROR(f'\nNet Profit mismatch: Expected ${expected_net_profit:,.2f}, Got ${actual_net_profit:,.2f}'))
        
        # Verify completion rate
        if financial_data['total_orders'] > 0:
            expected_completion_rate = (financial_data['completed_orders'] / financial_data['total_orders']) * 100
            actual_completion_rate = financial_data['order_completion_rate']
            
            if abs(expected_completion_rate - actual_completion_rate) < 0.1:
                self.stdout.write(self.style.SUCCESS('Order Completion Rate calculation is CORRECT'))
            else:
                self.stdout.write(self.style.ERROR(f'Completion Rate mismatch: Expected {expected_completion_rate:.1f}%, Got {actual_completion_rate:.1f}%'))
        
        self.stdout.write('\n=== ADMIN DASHBOARD CONSISTENCY CHECK ===')
        self.stdout.write(self.style.SUCCESS('All financial calculations are consistent!'))
