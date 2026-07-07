from django.core.management.base import BaseCommand
from documents.financial_utils import debug_financial_data, synchronize_financial_data


class Command(BaseCommand):
    help = 'Debug and synchronize financial data across all dashboards'

    def handle(self, *args, **options):
        self.stdout.write('Debugging financial data...')
        
        # Debug current state
        debug_info = debug_financial_data()
        
        # Synchronize data
        self.stdout.write('Synchronizing financial data...')
        synchronize_financial_data()
        
        # Debug again after synchronization
        self.stdout.write('\nFinal state after synchronization:')
        final_debug = debug_financial_data()
        
        if final_debug['discrepancy'] < 0.01:
            self.stdout.write(self.style.SUCCESS('Financial data is now consistent!'))
        else:
            self.stdout.write(self.style.WARNING(f'Still showing discrepancy: ${final_debug["discrepancy"]:,.2f}'))
