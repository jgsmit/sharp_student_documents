from django.core.management.base import BaseCommand
from django.test import Client
from django.contrib.auth import get_user_model
from withdrawals.models import WithdrawalRequest


class Command(BaseCommand):
    help = 'Verify WithdrawalRequest model methods'

    def handle(self, *args, **options):
        self.stdout.write('=== VERIFYING WITHDRAWALREQUEST MODEL ===')
        
        # Check available methods
        available_methods = []
        for attr in dir(WithdrawalRequest):
            if not attr.startswith('_') and callable(getattr(WithdrawalRequest, attr)):
                available_methods.append(attr)
        
        self.stdout.write(f"Available methods: {available_methods}")
        
        # Check if requires_two_factor_auth exists
        has_requires_2fa = hasattr(WithdrawalRequest, 'requires_two_factor_auth')
        self.stdout.write(f"Has requires_two_factor_auth: {has_requires_2fa}")
        
        # Check if can_process_instant exists
        has_can_process_instant = hasattr(WithdrawalRequest, 'can_process_instant')
        self.stdout.write(f"Has can_process_instant: {has_can_process_instant}")
        
        # Check if calculate_fee exists
        has_calculate_fee = hasattr(WithdrawalRequest, 'calculate_fee')
        self.stdout.write(f"Has calculate_fee: {has_calculate_fee}")
        
        # Check if __str__ exists
        has___str__ = hasattr(WithdrawalRequest, '__str__')
        self.stdout.write(f"Has __str__: {has___str__}")
        
        # Check if save exists
        has_save = hasattr(WithdrawalRequest, 'save')
        self.stdout.write(f"Has save: {has_save}")
        
        # Test creating a withdrawal request to see what methods are available
        try:
            User = get_user_model()
            test_user = User.objects.get(username='testuser')
            
            client = Client()
            client.force_login(test_user)
            
            # Create a withdrawal request
            response = client.post('/withdrawals/request/', {
                'withdrawal_method': 1,  # Use a dummy ID
                'amount': '50.00',
                'payout_type': 'weekly'
            })
            
            if response.status_code == 302:
                self.stdout.write(self.style.SUCCESS('Withdrawal request created successfully'))
                
                # Check the created object
                withdrawal = WithdrawalRequest.objects.filter(user=test_user).first()
                if withdrawal:
                    self.stdout.write(f"Created withdrawal ID: {withdrawal.id}")
                    self.stdout.write(f"Available methods on object:")
                    for method in available_methods:
                        if hasattr(withdrawal, method):
                            result = getattr(withdrawal, method)
                            self.stdout.write(f"  {method}: {result}")
                        else:
                            self.stdout.write(f"  {method}: NOT AVAILABLE")
            else:
                self.stdout.write(self.style.ERROR(f'Failed to create withdrawal request: {response.status_code}'))
                
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Test failed: {e}'))
        
        self.stdout.write('\n=== VERIFICATION COMPLETE ===')
