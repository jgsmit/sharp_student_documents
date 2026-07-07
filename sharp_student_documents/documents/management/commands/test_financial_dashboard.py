from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from documents.models import Order
from payments.models import Payment
from withdrawals.models import WithdrawalRequest
from django.db.models import Sum, Count
from decimal import Decimal


class Command(BaseCommand):
    help = 'Test financial dashboard data and identify issues'

    def handle(self, *args, **options):
        self.stdout.write('=== TESTING FINANCIAL DASHBOARD DATA ===')
        
        # Test basic data retrieval
        self.stdout.write('\\n--- Basic Statistics ---')
        
        # Order statistics
        orders = Order.objects.all().order_by("-created_at")
        total_orders = orders.count()
        completed_orders = orders.filter(status='paid').count()
        
        self.stdout.write(f'Total orders: {total_orders}')
        self.stdout.write(f'Completed orders: {completed_orders}')
        self.stdout.write(f'Completion rate: {(completed_orders / total_orders * 100) if total_orders > 0 else 0:.1f}%')
        
        # Revenue calculation
        total_revenue = orders.filter(status='paid').aggregate(
            total=Sum('amount_paid')
        )['total'] or 0
        
        self.stdout.write(f'Total revenue: ${total_revenue}')
        
        # Payment statistics
        payments = Payment.objects.all().order_by("-created_at")
        pending_payments = payments.filter(status='pending').count()
        
        self.stdout.write(f'Pending payments: {pending_payments}')
        
        # Withdrawal statistics
        withdrawals = WithdrawalRequest.objects.all().order_by("-requested_at")
        total_withdrawn = withdrawals.filter(status='completed').aggregate(
            total=Sum('amount')
        )['total'] or 0
        pending_withdrawals = withdrawals.filter(status='pending').count()
        
        self.stdout.write(f'Total withdrawn: ${total_withdrawn}')
        self.stdout.write(f'Pending withdrawals: {pending_withdrawals}')
        
        # Net profit
        net_profit = total_revenue - total_withdrawn
        self.stdout.write(f'Net profit: ${net_profit}')
        
        # Test payment method breakdown
        self.stdout.write('\\n--- Payment Method Breakdown ---')
        payment_methods = orders.filter(status='paid').values('payment_method').annotate(
            count=Count('id'),
            total=Sum('amount_paid')
        ).order_by('-total')
        
        for method in payment_methods:
            self.stdout.write(f'{method["payment_method"]}: {method["count"]} orders, ${method["total"]}')
        
        # Test withdrawal status breakdown
        self.stdout.write('\\n--- Withdrawal Status Breakdown ---')
        withdrawal_status = withdrawals.values('status').annotate(
            count=Count('id'),
            total=Sum('amount')
        ).order_by('-total')
        
        for status in withdrawal_status:
            self.stdout.write(f'{status["status"]}: {status["count"]} withdrawals, ${status["total"]}')
        
        # Test recent transactions
        self.stdout.write('\\n--- Recent Transactions ---')
        
        recent_orders = orders[:5]
        for order in recent_orders:
            self.stdout.write(f'Order #{order.id}: {order.document.title if order.document else "No Document"} - ${order.amount_paid} - {order.status}')
        
        recent_withdrawals = withdrawals[:5]
        for withdrawal in recent_withdrawals:
            self.stdout.write(f'Withdrawal {str(withdrawal.id)[:8]}...: ${withdrawal.amount} - {withdrawal.status} - {withdrawal.payout_type}')
        
        # Test potential issues
        self.stdout.write('\\n--- Potential Issues ---')
        
        # Check for orders without payments
        orders_without_payments = orders.filter(status='paid').exclude(
            id__in=Payment.objects.filter(status='success').values('order_id')
        )
        if orders_without_payments.exists():
            self.stdout.write(f'WARNING: {orders_without_payments.count()} paid orders without successful payments')
            for order in orders_without_payments[:3]:
                self.stdout.write(f'  - Order #{order.id}: {order.status} but no successful payment')
        
        # Check for payments without orders
        payments_without_orders = Payment.objects.exclude(
            order_id__in=Order.objects.values('id')
        )
        if payments_without_orders.exists():
            self.stdout.write(f'WARNING: {payments_without_orders.count()} payments without orders')
        
        # Check for negative amounts
        negative_orders = orders.filter(amount_paid__lt=0)
        if negative_orders.exists():
            self.stdout.write(f'WARNING: {negative_orders.count()} orders with negative amounts')
        
        # Check for very large amounts (potential errors)
        large_orders = orders.filter(amount_paid__gt=10000)
        if large_orders.exists():
            self.stdout.write(f'INFO: {large_orders.count()} orders with amounts > $10,000')
            for order in large_orders[:3]:
                self.stdout.write(f'  - Order #{order.id}: ${order.amount_paid}')
        
        # Test monthly revenue calculation
        self.stdout.write('\\n--- Monthly Revenue Test ---')
        from datetime import datetime, timedelta
        from django.utils import timezone
        
        monthly_revenue = []
        for i in range(3):  # Test last 3 months
            month_start = timezone.now().replace(day=1) - timedelta(days=i*30)
            month_end = month_start + timedelta(days=30)
            revenue = orders.filter(
                status='paid',
                created_at__gte=month_start,
                created_at__lt=month_end
            ).aggregate(total=Sum('amount_paid'))['total'] or 0
            monthly_revenue.append({
                'month': month_start.strftime('%B %Y'),
                'revenue': revenue
            })
        
        for month_data in monthly_revenue[::-1]:  # Show oldest to newest
            self.stdout.write(f'{month_data["month"]}: ${month_data["revenue"]}')
        
        self.stdout.write('\\n=== FINANCIAL DASHBOARD TEST COMPLETE ===')
