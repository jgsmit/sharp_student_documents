from django.core.management.base import BaseCommand
from django.db import models
from documents.models import Order
from payments.models import Payment
from withdrawals.models import WithdrawalRequest


class Command(BaseCommand):
    help = 'Clean up problematic financial data'

    def handle(self, *args, **options):
        self.stdout.write('=== CLEANING FINANCIAL DATA ===')
        
        # Find and fix orders marked as paid without successful payments
        self.stdout.write('\\n--- Fixing Payment Data Inconsistency ---')
        
        paid_orders_without_payments = Order.objects.filter(status='paid').exclude(
            id__in=Payment.objects.filter(status='success').values('order_id')
        )
        
        self.stdout.write(f'Found {paid_orders_without_payments.count()} orders to fix:')
        
        for order in paid_orders_without_payments:
            self.stdout.write(f'  - Order #{order.id}: ${order.amount_paid} - {order.status}')
            
            # Check if there's a payment record with different status
            payment = Payment.objects.filter(order=order).first()
            if payment:
                self.stdout.write(f'    Payment exists: {payment.status} - ${payment.amount}')
                # Update order status to match payment status
                if payment.status != 'success':
                    order.status = 'pending' if payment.status == 'pending' else 'failed'
                    order.save()
                    self.stdout.write(f'    Updated order status to: {order.status}')
            else:
                self.stdout.write(f'    No payment record found - marking as pending')
                order.status = 'pending'
                order.save()
        
        # Find and clean up very large test orders
        self.stdout.write('\\n--- Cleaning Up Large Test Orders ---')
        
        large_orders = Order.objects.filter(amount_paid__gt=10000)
        self.stdout.write(f'Found {large_orders.count()} large orders:')
        
        for order in large_orders:
            self.stdout.write(f'  - Order #{order.id}: ${order.amount_paid} - {order.document.title if order.document else "No Document"}')
            
            # If it's clearly test data, mark it as pending
            if order.amount_paid > 50000:  # Very large amounts are likely test data
                order.status = 'pending'
                order.save()
                self.stdout.write(f'    Marked as pending (likely test data)')
        
        # Clean up failed withdrawals
        self.stdout.write('\\n--- Cleaning Up Failed Withdrawals ---')
        
        failed_withdrawals = WithdrawalRequest.objects.filter(status='failed')
        self.stdout.write(f'Found {failed_withdrawals.count()} failed withdrawals:')
        
        for withdrawal in failed_withdrawals:
            self.stdout.write(f'  - Withdrawal {str(withdrawal.id)[:8]}...: ${withdrawal.amount} - {withdrawal.failure_reason}')
        
        # Check for withdrawal requests with very large amounts
        large_withdrawals = WithdrawalRequest.objects.filter(amount__gt=10000)
        self.stdout.write(f'\\nFound {large_withdrawals.count()} large withdrawal requests:')
        
        for withdrawal in large_withdrawals:
            self.stdout.write(f'  - Withdrawal {str(withdrawal.id)[:8]}...: ${withdrawal.amount} - {withdrawal.status}')
            if withdrawal.status == 'pending':
                # Mark large pending withdrawals as failed to prevent processing
                withdrawal.status = 'failed'
                withdrawal.failure_reason = 'Large amount - likely test data'
                withdrawal.save()
                self.stdout.write(f'    Marked as failed (test data)')
        
        # Show updated statistics
        self.stdout.write('\\n--- Updated Statistics ---')
        
        orders = Order.objects.all()
        total_orders = orders.count()
        completed_orders = orders.filter(status='paid').count()
        
        total_revenue = orders.filter(status='paid').aggregate(
            total=models.Sum('amount_paid')
        )['total'] or 0
        
        withdrawals = WithdrawalRequest.objects.all()
        total_withdrawn = withdrawals.filter(status='completed').aggregate(
            total=models.Sum('amount')
        )['total'] or 0
        
        self.stdout.write(f'Total orders: {total_orders}')
        self.stdout.write(f'Completed orders: {completed_orders}')
        self.stdout.write(f'Total revenue: ${total_revenue}')
        self.stdout.write(f'Total withdrawn: ${total_withdrawn}')
        self.stdout.write(f'Net profit: ${total_revenue - total_withdrawn}')
        
        self.stdout.write('\\n=== CLEANING COMPLETE ===')
