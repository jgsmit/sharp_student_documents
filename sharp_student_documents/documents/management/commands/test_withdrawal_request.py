from django.core.management.base import BaseCommand
from django.test import Client
from django.contrib.auth import get_user_model
from withdrawals.models import WithdrawalMethod, WithdrawalRequest
from decimal import Decimal


class Command(BaseCommand):
    help = 'Test withdrawal request creation'

    def handle(self, *args, **options):
        self.stdout.write('=== TESTING WITHDRAWAL REQUEST CREATION ===')
        
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
        
        # Create a PayPal withdrawal method for testing
        try:
            paypal_method = WithdrawalMethod.objects.get(
                user=test_user,
                method_type='paypal'
            )
        except WithdrawalMethod.DoesNotExist:
            paypal_method = WithdrawalMethod.objects.create(
                user=test_user,
                method_type='paypal',
                paypal_email='test@example.com',
                is_verified=True,
                is_active=True
            )
            self.stdout.write('Created PayPal withdrawal method for testing')
        
        # Test withdrawal request creation
        client = Client()
        client.force_login(test_user)
        
        try:
            response = client.post('/withdrawals/request/', {
                'withdrawal_method': paypal_method.id,
                'amount': '50.00',
                'payout_type': 'weekly'
            })
            
            if response.status_code == 302:
                self.stdout.write(self.style.SUCCESS('Withdrawal request created successfully'))
                
                # Check if withdrawal request was saved properly
                try:
                    withdrawal = WithdrawalRequest.objects.filter(user=test_user).first()
                    if withdrawal:
                        self.stdout.write(f'  Amount: ${withdrawal.amount}')
                        self.stdout.write(f'  Fee: ${withdrawal.fee}')
                        self.stdout.write(f'  Net Amount: ${withdrawal.net_amount}')
                        self.stdout.write(f'  Status: {withdrawal.status}')
                        self.stdout.write(f'  Payout Type: {withdrawal.payout_type}')
                        
                        # Verify net_amount calculation
                        expected_net = Decimal('50.00') - (Decimal('50.00') * Decimal('0.02'))  # 2% PayPal fee
                        if abs(withdrawal.net_amount - expected_net) < Decimal('0.01'):
                            self.stdout.write(self.style.WARNING(f'  Net amount mismatch: expected ${expected_net}, got ${withdrawal.net_amount}'))
                        else:
                            self.stdout.write(self.style.SUCCESS('  Net amount calculation correct'))
                    else:
                        self.stdout.write(self.style.ERROR('  Withdrawal request not found in database'))
                        
                except Exception as e:
                    self.stdout.write(self.style.ERROR(f'  Error checking withdrawal: {e}'))
                    
            else:
                self.stdout.write(self.style.ERROR(f'Failed to create withdrawal request: {response.status_code}'))
                if response.status_code == 200:
                    self.stdout.write('  Check form for validation errors')
                    
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Test failed: {e}'))
        
        # Clean up
        try:
            WithdrawalRequest.objects.filter(user=test_user).delete()
            WithdrawalMethod.objects.filter(user=test_user).delete()
            test_user.delete()
            self.stdout.write('\nCleaned up test data')
        except:
            pass
        
        self.stdout.write('\n=== WITHDRAWAL REQUEST TEST COMPLETE ===')
