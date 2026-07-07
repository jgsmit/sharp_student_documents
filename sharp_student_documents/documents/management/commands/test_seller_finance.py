from django.core.management.base import BaseCommand
from documents.financial_utils import get_unified_financial_data
from accounts.models import CustomUser
from django.conf import settings


class Command(BaseCommand):
    help = 'Test seller dashboard financial data'

    def handle(self, *args, **options):
        self.stdout.write('Testing seller dashboard financial data...')
        
        # Get a test seller (Ripper)
        try:
            seller = CustomUser.objects.get(username='Ripper')
            financial_data = get_unified_financial_data(user=seller, is_admin=False)
            
            self.stdout.write(f"Seller: {seller.username}")
            self.stdout.write(f"Total Earnings: ${financial_data['total_earnings']:,.2f}")
            self.stdout.write(f"Commission Paid: ${financial_data['wallet']['total_commission_paid']:,.2f}")
            self.stdout.write(f"Available Balance: ${financial_data['wallet']['balance']:,.2f}")
            self.stdout.write(f"Total Sales: {financial_data['total_sales']}")

            commission_rate = getattr(settings, "PLATFORM_COMMISSION_RATE", 0.40)
            seller_share = getattr(settings, "SELLER_SHARE", 0.60)
            self.stdout.write(f"\nCommission Rate: {commission_rate * 100:.0f}%")
            self.stdout.write(f"Seller Share: {seller_share * 100:.0f}%")
            
        except CustomUser.DoesNotExist:
            self.stdout.write(self.style.ERROR('Seller "R Ripper" not found'))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Error: {e}'))
