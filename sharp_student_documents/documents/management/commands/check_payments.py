from django.core.management.base import BaseCommand
from django.db.models import Sum
from payments.models import Payment


class Command(BaseCommand):
    help = 'Check payment status'

    def handle(self, *args, **options):
        self.stdout.write('Checking payment status...')
        
        # All payments
        all_payments = Payment.objects.all()
        self.stdout.write(f'Total payments: {all_payments.count()}')
        
        # By status
        pending = Payment.objects.filter(status='pending')
        success = Payment.objects.filter(status='success')
        failed = Payment.objects.filter(status='failed')
        
        self.stdout.write(f'Pending payments: {pending.count()}')
        self.stdout.write(f'Successful payments: {success.count()}')
        self.stdout.write(f'Failed payments: {failed.count()}')
        
        # Successful payment amounts
        successful_total = success.aggregate(total=Sum('amount'))['total'] or 0
        self.stdout.write(f'Successful payment total: ${successful_total:,.2f}')
        
        # Show recent successful payments
        self.stdout.write('\nRecent successful payments:')
        for payment in success.order_by('-created_at')[:5]:
            self.stdout.write(f'  - ${payment.amount:,.2f} on {payment.created_at.strftime("%Y-%m-%d %H:%M")} (Order: {payment.order.id if payment.order else "N/A"})')
