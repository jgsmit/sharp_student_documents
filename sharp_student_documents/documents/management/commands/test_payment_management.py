from django.core.management.base import BaseCommand
from django.db.models import Q
from documents.models import Order
from payments.models import Payment


class Command(BaseCommand):
    help = 'Test payment management page data'

    def handle(self, *args, **options):
        self.stdout.write('=== TESTING PAYMENT MANAGEMENT DATA ===')
        
        # Test orders data
        orders = Order.objects.all().order_by("-created_at")
        self.stdout.write(f'\\n--- Orders Data ---')
        self.stdout.write(f'Total orders: {orders.count()}')
        
        for order in orders[:5]:
            self.stdout.write(f'  - Order #{order.id}: {order.document.title if order.document else "No Document"} - ${order.amount_paid} - {order.status}')
        
        # Test payments data
        payments = Payment.objects.all()
        self.stdout.write(f'\\n--- Payments Data ---')
        self.stdout.write(f'Total payments: {payments.count()}')
        
        for payment in payments[:5]:
            self.stdout.write(f'  - Payment #{payment.id}: ${payment.amount} - {payment.status} - Order #{payment.order_id if payment.order else "No Order"}')
        
        # Test statistics
        self.stdout.write(f'\\n--- Statistics ---')
        self.stdout.write(f'Completed payments: {payments.filter(status="success").count()}')
        self.stdout.write(f'Pending payments: {payments.filter(status="pending").count()}')
        self.stdout.write(f'Failed payments: {payments.filter(status="failed").count()}')
        
        # Test order-payment relationship
        self.stdout.write(f'\\n--- Order-Payment Relationship ---')
        paid_orders = orders.filter(status='paid')
        self.stdout.write(f'Paid orders: {paid_orders.count()}')
        
        successful_payments = payments.filter(status='success')
        self.stdout.write(f'Successful payments: {successful_payments.count()}')
        
        # Check for mismatches
        paid_orders_without_payments = paid_orders.exclude(
            id__in=successful_payments.values('order_id')
        )
        if paid_orders_without_payments.exists():
            self.stdout.write(f'WARNING: {paid_orders_without_payments.count()} paid orders without successful payments')
            for order in paid_orders_without_payments[:3]:
                self.stdout.write(f'  - Order #{order.id}: {order.status} but no successful payment')
        
        payments_without_orders = successful_payments.exclude(
            order_id__in=paid_orders.values('id')
        )
        if payments_without_orders.exists():
            self.stdout.write(f'WARNING: {payments_without_orders.count()} successful payments without paid orders')
            for payment in payments_without_orders[:3]:
                self.stdout.write(f'  - Payment #{payment.id}: {payment.status} but no paid order')
        
        # Test search functionality
        self.stdout.write(f'\\n--- Search Test ---')
        search_results = orders.filter(
            Q(document__title__icontains='test') |
            Q(buyer__username__icontains='test') |
            Q(payment_method__icontains='paypal')
        )
        self.stdout.write(f'Search results for "test" or "paypal": {search_results.count()}')
        
        self.stdout.write('\\n=== TEST COMPLETE ===')
        self.stdout.write('\\nThe payment management page should now show:')
        self.stdout.write(f'- Total transactions: {orders.count()}')
        self.stdout.write(f'- Completed payments: {payments.filter(status="success").count()}')
        self.stdout.write(f'- Pending payments: {payments.filter(status="pending").count()}')
        self.stdout.write(f'- Failed payments: {payments.filter(status="failed").count()}')
        self.stdout.write(f'- Detailed orders table with {orders.count()} items')
