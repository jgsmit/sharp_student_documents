from django.core.management.base import BaseCommand
from documents.models import Order
from payments.models import Payment


class Command(BaseCommand):
    help = 'Check current payment status'

    def handle(self, *args, **options):
        self.stdout.write('=== CURRENT PAYMENT STATUS ===')
        
        self.stdout.write('Recent Orders:')
        for order in Order.objects.all().order_by('-created_at')[:5]:
            doc_title = order.document.title if order.document else 'No Document'
            self.stdout.write(f'Order #{order.id}: {doc_title} - Status: {order.status}')
        
        self.stdout.write('Recent Payments:')
        for payment in Payment.objects.all().order_by('-created_at')[:5]:
            self.stdout.write(f'Payment: {payment.payment_method} - Status: {payment.status}')
