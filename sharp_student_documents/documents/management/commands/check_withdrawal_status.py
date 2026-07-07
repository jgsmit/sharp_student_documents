from django.core.management.base import BaseCommand
from withdrawals.models import WithdrawalRequest, WithdrawalMethod


class Command(BaseCommand):
    help = 'Check withdrawal status'

    def handle(self, *args, **options):
        self.stdout.write('=== WITHDRAWAL STATUS ===')
        
        self.stdout.write('Withdrawal Requests:')
        for withdrawal in WithdrawalRequest.objects.all().order_by('-requested_at')[:5]:
            self.stdout.write(f'Withdrawal #{withdrawal.id}: ${withdrawal.amount} - Status: {withdrawal.status} - Type: {withdrawal.payout_type}')
        
        self.stdout.write('Withdrawal Methods:')
        for method in WithdrawalMethod.objects.all()[:5]:
            self.stdout.write(f'Method: {method.method_type} - Email: {method.paypal_email} - User: {method.user.username}')
