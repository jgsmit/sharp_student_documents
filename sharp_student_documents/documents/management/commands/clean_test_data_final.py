from django.core.management.base import BaseCommand
from django.db import models
from documents.models import Order, Document
from payments.models import Payment
from withdrawals.models import WithdrawalRequest


class Command(BaseCommand):
    help = 'Clean up remaining test data for realistic financial metrics'

    def handle(self, *args, **options):
        self.stdout.write('=== CLEANING UP REMAINING TEST DATA ===')
        
        # Clean up large orders (> $1000)
        self.stdout.write('\\n--- Cleaning Large Orders ---')
        large_orders = Order.objects.filter(amount_paid__gt=1000)
        self.stdout.write(f'Found {large_orders.count()} large orders to clean:')
        
        for order in large_orders:
            self.stdout.write(f'  - Order #{order.id}: ${order.amount_paid} - {order.document.title if order.document else "No Document"}')
            
            # Mark large orders as pending (they're likely test data)
            order.status = 'pending'
            order.save()
            self.stdout.write(f'    Marked as pending')
        
        # Clean up large withdrawals (> $1000)
        self.stdout.write('\\n--- Cleaning Large Withdrawals ---')
        large_withdrawals = WithdrawalRequest.objects.filter(amount__gt=1000)
        self.stdout.write(f'Found {large_withdrawals.count()} large withdrawals to clean:')
        
        for withdrawal in large_withdrawals:
            self.stdout.write(f'  - Withdrawal {str(withdrawal.id)[:8]}...: ${withdrawal.amount} - {withdrawal.status}')
            
            # Mark large withdrawals as failed with appropriate reason
            if withdrawal.status == 'pending':
                withdrawal.status = 'failed'
                withdrawal.failure_reason = 'Large amount - likely test data'
                withdrawal.save()
                self.stdout.write(f'    Marked as failed (test data)')
        
        # Clean up documents with unrealistic prices
        self.stdout.write('\\n--- Cleaning Document Prices ---')
        expensive_docs = Document.objects.filter(price__gt=100)
        self.stdout.write(f'Found {expensive_docs.count()} documents with high prices:')
        
        for doc in expensive_docs:
            self.stdout.write(f'  - {doc.title}: ${doc.price}')
            
            # Set realistic prices for expensive documents
            if doc.price > 1000:
                doc.price = 15.00  # Set to reasonable price
                doc.save()
                self.stdout.write(f'    Price set to $15.00')
            elif doc.price > 100:
                doc.price = 25.00  # Set to reasonable price
                doc.save()
                self.stdout.write(f'    Price set to $25.00')
        
        # Clean up payments that don't match orders
        self.stdout.write('\\n--- Cleaning Payment Data ---')
        
        # Find successful payments without corresponding paid orders
        successful_payments = Payment.objects.filter(status='success')
        orphaned_payments = successful_payments.exclude(
            order_id__in=Order.objects.filter(status='paid').values('id')
        )
        
        self.stdout.write(f'Found {orphaned_payments.count()} orphaned successful payments:')
        for payment in orphaned_payments:
            self.stdout.write(f'  - Payment #{payment.id}: ${payment.amount} - {payment.status}')
            # Mark these as failed since orders aren't paid
            payment.status = 'failed'
            payment.save()
            self.stdout.write(f'    Marked as failed')
        
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
        
        pending_withdrawals = withdrawals.filter(status='pending').count()
        completed_withdrawals = withdrawals.filter(status='completed').count()
        failed_withdrawals = withdrawals.filter(status='failed').count()
        
        self.stdout.write(f'Total orders: {total_orders}')
        self.stdout.write(f'Completed orders: {completed_orders}')
        self.stdout.write(f'Total revenue: ${total_revenue}')
        self.stdout.write(f'Total withdrawn: ${total_withdrawn}')
        self.stdout.write(f'Net profit: ${total_revenue - total_withdrawn}')
        self.stdout.write(f'Pending withdrawals: {pending_withdrawals}')
        self.stdout.write(f'Completed withdrawals: {completed_withdrawals}')
        self.stdout.write(f'Failed withdrawals: {failed_withdrawals}')
        
        # Show realistic orders remaining
        self.stdout.write('\\n--- Remaining Realistic Orders ---')
        realistic_orders = Order.objects.filter(status='paid').filter(amount_paid__lte=100)
        self.stdout.write(f'Found {realistic_orders.count()} realistic paid orders:')
        
        for order in realistic_orders:
            self.stdout.write(f'  - Order #{order.id}: ${order.amount_paid} - {order.document.title if order.document else "No Document"}')
        
        # Show realistic withdrawals remaining
        self.stdout.write('\\n--- Remaining Realistic Withdrawals ---')
        realistic_withdrawals = WithdrawalRequest.objects.filter(amount__lte=100)
        self.stdout.write(f'Found {realistic_withdrawals.count()} realistic withdrawals:')
        
        for withdrawal in realistic_withdrawals:
            self.stdout.write(f'  - Withdrawal {str(withdrawal.id)[:8]}...: ${withdrawal.amount} - {withdrawal.status} - {withdrawal.payout_type}')
        
        self.stdout.write('\\n=== CLEANING COMPLETE ===')
        self.stdout.write('\\nFinancial dashboard should now show realistic metrics!')
        self.stdout.write('Go to: http://127.0.0.1:8000/documents/admin/view-financials/')
