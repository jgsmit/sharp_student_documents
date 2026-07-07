from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from withdrawals.models import WithdrawalRequest, WithdrawalMethod
from withdrawals.services import WithdrawalService
from decimal import Decimal


class Command(BaseCommand):
    help = 'Debug withdrawal service methods'

    def handle(self, *args, **options):
        self.stdout.write('=== DEBUGGING WITHDRAWAL SERVICE ===')
        
        # Get or create test user
        User = get_user_model()
        try:
            seller_user = User.objects.get(username='testuser')
        except User.DoesNotExist:
            seller_user = User.objects.create_user(
                username='testuser',
                email='test@example.com',
                password='testpass123'
            )
            self.stdout.write('Created test user: testuser')
        
        # Create PayPal withdrawal method
        try:
            paypal_method = WithdrawalMethod.objects.get(
                user=seller_user,
                method_type='paypal'
            )
        except WithdrawalMethod.DoesNotExist:
            paypal_method = WithdrawalMethod.objects.create(
                user=seller_user,
                method_type='paypal',
                paypal_email='test@example.com',
                is_verified=True,
                is_active=True
            )
            self.stdout.write('Created PayPal withdrawal method')
        
        # Create a withdrawal request
        try:
            withdrawal = WithdrawalRequest.objects.create(
                user=seller_user,
                withdrawal_method=paypal_method,
                amount=Decimal('50.00'),
                payout_type='weekly'
            )
            self.stdout.write(f'Created withdrawal request: {withdrawal.id}')
            self.stdout.write(f'  Status: {withdrawal.status}')
            
            # Test can_process_instant method
            self.stdout.write('\n--- TESTING can_process_instant ---')
            try:
                can_instant = withdrawal.can_process_instant()
                self.stdout.write(f'Can process instant: {can_instant}')
            except Exception as e:
                self.stdout.write(f'Error in can_process_instant: {e}')
            
            # Test process_instant_withdrawal method
            self.stdout.write('\n--- TESTING process_instant_withdrawal ---')
            try:
                result = WithdrawalService.process_instant_withdrawal(withdrawal)
                self.stdout.write(f'Process instant result: {result}')
                withdrawal.refresh_from_db()
                self.stdout.write(f'Withdrawal status after process_instant: {withdrawal.status}')
            except Exception as e:
                self.stdout.write(f'Error in process_instant_withdrawal: {e}')
                import traceback
                self.stdout.write(traceback.format_exc())
            
            # Create another withdrawal for weekly test
            withdrawal2 = WithdrawalRequest.objects.create(
                user=seller_user,
                withdrawal_method=paypal_method,
                amount=Decimal('25.00'),
                payout_type='weekly'
            )
            
            # Test queue_weekly_withdrawal method
            self.stdout.write('\n--- TESTING queue_weekly_withdrawal ---')
            try:
                result = WithdrawalService.queue_weekly_withdrawal(withdrawal2)
                self.stdout.write(f'Queue weekly result: {result}')
                withdrawal2.refresh_from_db()
                self.stdout.write(f'Withdrawal status after queue_weekly: {withdrawal2.status}')
            except Exception as e:
                self.stdout.write(f'Error in queue_weekly_withdrawal: {e}')
                import traceback
                self.stdout.write(traceback.format_exc())
            
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Error during testing: {e}'))
            import traceback
            self.stdout.write(traceback.format_exc())
        
        # Clean up
        try:
            WithdrawalRequest.objects.filter(user=seller_user).delete()
            WithdrawalMethod.objects.filter(user=seller_user).delete()
            seller_user.delete()
            self.stdout.write('\nCleaned up test data')
        except:
            pass
        
        self.stdout.write('\n=== DEBUG COMPLETE ===')
