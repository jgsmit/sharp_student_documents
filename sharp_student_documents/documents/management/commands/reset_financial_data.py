from django.core.management.base import BaseCommand
from django.db import transaction
from documents.models import Order
from payments.models import Payment
from sales.models import Sale, Wallet, Transaction
from withdrawals.models import WithdrawalRequest, WithdrawalMethod, WithdrawalTransaction

class Command(BaseCommand):
    help = 'Reset financial data only (preserves users and documents)'
    
    def handle(self, *args, **options):
        self.stdout.write('SAFE DATABASE RESET - FINANCIAL DATA ONLY')
        self.stdout.write('=' * 60)
        self.stdout.write('Deleting ALL financial data...')
        self.stdout.write('PRESERVED: User accounts and documents')
        
        try:
            with transaction.atomic():
                counts = {}
                
                # Delete in correct order
                counts['withdrawal_transactions'] = WithdrawalTransaction.objects.count()
                WithdrawalTransaction.objects.all().delete()
                self.stdout.write(f'   Deleted {counts["withdrawal_transactions"]} withdrawal transactions')
                
                counts['withdrawal_requests'] = WithdrawalRequest.objects.count()
                WithdrawalRequest.objects.all().delete()
                self.stdout.write(f'   Deleted {counts["withdrawal_requests"]} withdrawal requests')
                
                counts['withdrawal_methods'] = WithdrawalMethod.objects.count()
                WithdrawalMethod.objects.all().delete()
                self.stdout.write(f'   Deleted {counts["withdrawal_methods"]} withdrawal methods')
                
                counts['transactions'] = Transaction.objects.count()
                Transaction.objects.all().delete()
                self.stdout.write(f'   Deleted {counts["transactions"]} wallet transactions')
                
                counts['wallets'] = Wallet.objects.count()
                Wallet.objects.all().delete()
                self.stdout.write(f'   Deleted {counts["wallets"]} wallets')
                
                counts['sales'] = Sale.objects.count()
                Sale.objects.all().delete()
                self.stdout.write(f'   Deleted {counts["sales"]} sales records')
                
                counts['payments'] = Payment.objects.count()
                Payment.objects.all().delete()
                self.stdout.write(f'   Deleted {counts["payments"]} payments')
                
                counts['orders'] = Order.objects.count()
                Order.objects.all().delete()
                self.stdout.write(f'   Deleted {counts["orders"]} orders')
                
                self.stdout.write('=' * 40)
                self.stdout.write('SAFE RESET COMPLETED')
                self.stdout.write('   User accounts and documents preserved')
                self.stdout.write('   Financial data cleared - fresh start')
                self.stdout.write('   Ready for testing with clean data')
                
        except Exception as e:
            self.stdout.write(f'ERROR during reset: {e}')
