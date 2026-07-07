from django.core.management.base import BaseCommand
from django.urls import reverse
from django.contrib.auth import get_user_model
from withdrawals.models import WithdrawalRequest


class Command(BaseCommand):
    help = 'Test withdrawal URL patterns'

    def handle(self, *args, **options):
        self.stdout.write('=== TESTING WITHDRAWAL URLS ===')
        
        # Test URL pattern resolution
        try:
            # Get a pending withdrawal
            withdrawal = WithdrawalRequest.objects.filter(status='pending').first()
            if withdrawal:
                self.stdout.write(f'Found withdrawal: {withdrawal.id}')
                
                # Test URL resolution
                url = reverse('withdrawals:admin_approve', kwargs={'withdrawal_id': withdrawal.id})
                self.stdout.write(f'Admin approve URL: {url}')
                
                # Test reject URL
                url = reverse('withdrawals:admin_reject', kwargs={'withdrawal_id': withdrawal.id})
                self.stdout.write(f'Admin reject URL: {url}')
                
                # Test details URL
                url = reverse('withdrawals:admin_details', kwargs={'withdrawal_id': withdrawal.id})
                self.stdout.write(f'Admin details URL: {url}')
                
            else:
                self.stdout.write('No pending withdrawals found')
        except Exception as e:
            self.stdout.write(f'ERROR: {e}')
        
        self.stdout.write('\\n=== URL TEST COMPLETE ===')
