from django.core.management.base import BaseCommand
from django.db.models import Sum
from documents.financial_utils import get_unified_financial_data
from accounts.models import CustomUser
from documents.models import Order
from decimal import Decimal


class Command(BaseCommand):
    help = 'Comprehensive data consistency check between admin and seller dashboards'

    def handle(self, *args, **options):
        self.stdout.write('=== COMPREHENSIVE DATA CONSISTENCY CHECK ===')
        
        # Get admin dashboard data
        admin_data = get_unified_financial_data(is_admin=True)
        
        self.stdout.write('\nADMIN DASHBOARD DATA:')
        self.stdout.write(f"  Total Revenue: ${admin_data['total_revenue']:,.2f}")
        self.stdout.write(f"  Pending Revenue: ${admin_data['pending_revenue']:,.2f}")
        self.stdout.write(f"  Total Orders: {admin_data['total_orders']}")
        self.stdout.write(f"  Completed Orders: {admin_data['completed_orders']}")
        self.stdout.write(f"  Pending Orders: {admin_data['pending_orders']}")
        self.stdout.write(f"  Total Withdrawn: ${admin_data['total_withdrawn']:,.2f}")
        self.stdout.write(f"  Net Profit: ${admin_data['net_profit']:,.2f}")
        
        # Get all sellers and their individual data
        all_sellers = CustomUser.objects.filter(is_seller=True)
        self.stdout.write(f'\nSELLER DASHBOARD DATA ({all_sellers.count()} sellers):')
        
        total_seller_earnings = Decimal('0.00')
        total_seller_pending = Decimal('0.00')
        total_seller_orders = 0
        total_seller_completed = 0
        total_seller_pending_count = 0
        
        for seller in all_sellers:
            seller_data = get_unified_financial_data(user=seller, is_admin=False)
            
            self.stdout.write(f"\n  {seller.username}:")
            self.stdout.write(f"    Total Earnings: ${seller_data['total_earnings']:,.2f}")
            self.stdout.write(f"    Pending Earnings: ${seller_data['pending_earnings']:,.2f}")
            self.stdout.write(f"    Total Sales: {seller_data['total_sales']}")
            self.stdout.write(f"    Pending Sales: {seller_data['pending_sales']}")
            self.stdout.write(f"    Commission Paid: ${seller_data['wallet']['total_commission_paid']:,.2f}")
            self.stdout.write(f"    Available Balance: ${seller_data['wallet']['balance']:,.2f}")
            
            # Accumulate totals
            total_seller_earnings += Decimal(str(seller_data['total_earnings']))
            total_seller_pending += Decimal(str(seller_data['pending_earnings']))
            total_seller_orders += seller_data['total_sales'] + seller_data['pending_sales']
            total_seller_completed += seller_data['total_sales']
            total_seller_pending_count += seller_data['pending_sales']
        
        # Consistency checks
        self.stdout.write('\nCONSISTENCY CHECKS:')
        
        # Check 1: Total earnings should match
        earnings_match = abs(admin_data['total_revenue'] - total_seller_earnings) < Decimal('0.01')
        self.stdout.write(f"  Total Earnings Match: {earnings_match}")
        if not earnings_match:
            self.stdout.write(f"     Admin: ${admin_data['total_revenue']:,.2f}")
            self.stdout.write(f"     Sellers: ${total_seller_earnings:,.2f}")
            self.stdout.write(f"     Difference: ${abs(admin_data['total_revenue'] - total_seller_earnings):,.2f}")
        
        # Check 2: Pending earnings should match
        pending_match = abs(admin_data['pending_revenue'] - total_seller_pending) < Decimal('0.01')
        self.stdout.write(f"  Pending Earnings Match: {pending_match}")
        if not pending_match:
            self.stdout.write(f"     Admin: ${admin_data['pending_revenue']:,.2f}")
            self.stdout.write(f"     Sellers: ${total_seller_pending:,.2f}")
            self.stdout.write(f"     Difference: ${abs(admin_data['pending_revenue'] - total_seller_pending):,.2f}")
        
        # Check 3: Order counts should match
        orders_match = admin_data['total_orders'] == total_seller_orders
        self.stdout.write(f"  Total Orders Match: {orders_match}")
        if not orders_match:
            self.stdout.write(f"     Admin: {admin_data['total_orders']}")
            self.stdout.write(f"     Sellers: {total_seller_orders}")
            self.stdout.write(f"     Difference: {abs(admin_data['total_orders'] - total_seller_orders)}")
        
        # Check 4: Completed orders should match
        completed_match = admin_data['completed_orders'] == total_seller_completed
        self.stdout.write(f"  Completed Orders Match: {completed_match}")
        if not completed_match:
            self.stdout.write(f"     Admin: {admin_data['completed_orders']}")
            self.stdout.write(f"     Sellers: {total_seller_completed}")
            self.stdout.write(f"     Difference: {abs(admin_data['completed_orders'] - total_seller_completed)}")
        
        # Check 5: Pending orders should match
        pending_orders_match = admin_data['pending_orders'] == total_seller_pending_count
        self.stdout.write(f"  Pending Orders Match: {pending_orders_match}")
        if not pending_orders_match:
            self.stdout.write(f"     Admin: {admin_data['pending_orders']}")
            self.stdout.write(f"     Sellers: {total_seller_pending_count}")
            self.stdout.write(f"     Difference: {abs(admin_data['pending_orders'] - total_seller_pending_count)}")
        
        # Overall consistency
        all_checks_pass = all([earnings_match, pending_match, orders_match, completed_match, pending_orders_match])
        
        self.stdout.write('\nFINAL RESULT:')
        if all_checks_pass:
            self.stdout.write(self.style.SUCCESS('ALL DATA CONSISTENCY CHECKS PASSED!'))
            self.stdout.write(self.style.SUCCESS('   Admin and Seller dashboards are perfectly aligned.'))
        else:
            self.stdout.write(self.style.ERROR('DATA INCONSISTENCIES DETECTED!'))
            self.stdout.write(self.style.ERROR('   Admin and Seller dashboards show different data.'))
        
        # Additional verification: Direct database query
        self.stdout.write('\nDIRECT DATABASE VERIFICATION:')
        direct_paid_orders = Order.objects.filter(status='paid')
        direct_total = direct_paid_orders.aggregate(total=Sum('amount_paid'))['total'] or 0
        direct_count = direct_paid_orders.count()
        
        self.stdout.write(f"  Direct DB Query - Total Revenue: ${direct_total:,.2f}")
        self.stdout.write(f"  Direct DB Query - Paid Orders: {direct_count}")
        
        db_match_admin = abs(admin_data['total_revenue'] - direct_total) < Decimal('0.01')
        db_match_sellers = abs(total_seller_earnings - direct_total) < Decimal('0.01')
        
        self.stdout.write(f"  DB vs Admin Match: {db_match_admin}")
        self.stdout.write(f"  DB vs Sellers Match: {db_match_sellers}")
        
        if db_match_admin and db_match_sellers:
            self.stdout.write(self.style.SUCCESS('Database verification confirms consistency!'))
        else:
            self.stdout.write(self.style.ERROR('Database verification shows inconsistencies!'))
