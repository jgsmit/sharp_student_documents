from django.core.management.base import BaseCommand
from accounts.models import CustomUser


class Command(BaseCommand):
    help = 'List all sellers'

    def handle(self, *args, **options):
        sellers = CustomUser.objects.filter(is_seller=True)
        
        self.stdout.write(f'Found {sellers.count()} sellers:')
        for seller in sellers:
            self.stdout.write(f'  - {seller.username} (ID: {seller.id})')
