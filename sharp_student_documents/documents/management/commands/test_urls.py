from django.core.management.base import BaseCommand
from django.urls import reverse


class Command(BaseCommand):
    help = 'Test URL resolution for payments'

    def handle(self, *args, **options):
        self.stdout.write('=== TESTING URL RESOLUTION ===')
        
        try:
            url = reverse('documents:my_purchases')
            self.stdout.write(f'SUCCESS: my_purchases URL = {url}')
        except Exception as e:
            self.stdout.write(f'ERROR: {e}')
        
        try:
            url = reverse('documents:document_list')
            self.stdout.write(f'SUCCESS: document_list URL = {url}')
        except Exception as e:
            self.stdout.write(f'ERROR: {e}')
        
        try:
            url = reverse('payments:checkout', args=[1])
            self.stdout.write(f'SUCCESS: checkout URL = {url}')
        except Exception as e:
            self.stdout.write(f'ERROR: {e}')
