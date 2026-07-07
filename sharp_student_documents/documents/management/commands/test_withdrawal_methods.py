from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from withdrawals.models import WithdrawalRequest
from decimal import Decimal


class Command(BaseCommand):
    help = 'Test withdrawal request methods'

    def handle(self, *args, **options):
        self.stdout.write('=== TESTING WITHDRAWAL REQUEST METHODS ===')
        
        # Get or create a test user
        User = get_user_model()
        try:
            test_user = User.objects.get(username='testuser')
        except User.DoesNotExist:
            test_user = User.objects.create_user(
                username='testuser',
                email='test@example.com',
                password='testpass123'
            )
            self.stdout.write('Created test user: testuser')
        
        # Create a test withdrawal request
        try:
            withdrawal = WithdrawalRequest.objects.create(
                user=test_user,
                amount=Decimal('50.00'),
                payout_type='weekly'
            )
            
            self.stdout.write(f'Created withdrawal request: {withdrawal.id}')
            
            # Test available methods
            methods_to_test = [
                'requires_two_factor_auth',
                'can_process_instant',
                'calculate_fee',
                '__str__',
                'save'
            ]
            
            for method_name in methods_to_test:
                if hasattr(withdrawal, method_name):
                    method = getattr(withdrawal, method_name)
                    if callable(method):
                        try:
                            result = method()
                            self.stdout.write(f'  {method_name}(): {result}')
                        except Exception as e:
                            self.stdout.write(f'  {method_name}(): ERROR - {e}')
                    else:
                        self.stdout.write(f'  {method_name}: {method}')
                else:
                    self.stdout.write(f'  {method_name}: NOT AVAILABLE')
            
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Failed to create withdrawal: {e}'))
        
        # Clean up
        try:
            WithdrawalRequest.objects.filter(user=test_user).delete()
            test_user.delete()
            self.stdout.write('\nCleaned up test data')
        except:
            pass
        
        self.stdout.write('\n=== METHOD TEST COMPLETE ===')
