from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from withdrawals.models import WithdrawalRequest, WithdrawalMethod
from sales.models import Wallet
from decimal import Decimal
from django.utils import timezone


class Command(BaseCommand):
    help = 'Create a pending instant withdrawal for approval testing'

    def handle(self, *args, **options):
        self.stdout.write('=== CREATE PENDING INSTANT WITHDRAWAL ===')
        
        # Get Ripper user
        User = get_user_model()
        try:
            ripper = User.objects.get(username='Ripper')
            self.stdout.write(f'Using user: {ripper.username}')
        except User.DoesNotExist:
            self.stdout.write('Ripper user not found!')
            return
        
        # Check wallet
        try:
            wallet = Wallet.objects.get(user=ripper)
            self.stdout.write(f'Current balance: ${wallet.balance}')
        except Wallet.DoesNotExist:
            self.stdout.write('No wallet found for Ripper')
            return
        
        # Get withdrawal method
        try:
            method = WithdrawalMethod.objects.get(
                user=ripper,
                method_type='paypal',
                is_active=True
            )
            self.stdout.write(f'Using method: {method.method_type} ({method.paypal_email})')
        except WithdrawalMethod.DoesNotExist:
            self.stdout.write('No PayPal method found for Ripper')
            return
        
        # Create a pending instant withdrawal without automatic processing
        test_amount = Decimal('35.00')
        
        if wallet.balance < test_amount:
            self.stdout.write(f'Insufficient balance: ${wallet.balance} < ${test_amount}')
            return
        
        try:
            # Create withdrawal directly without triggering processing
            withdrawal = WithdrawalRequest.objects.create(
                user=ripper,
                withdrawal_method=method,
                amount=test_amount,
                fee=Decimal('0.70'),  # 2% PayPal fee
                net_amount=test_amount - Decimal('0.70'),
                payout_type='instant',
                status='pending',
                processed_at=None,  # Ensure not processed
                completed_at=None   # Ensure not completed
            )
            
            self.stdout.write(f'\\n✅ Created PENDING INSTANT withdrawal:')
            self.stdout.write(f'   ID: {withdrawal.id}')
            self.stdout.write(f'   Amount: ${withdrawal.amount}')
            self.stdout.write(f'   Status: {withdrawal.status}')
            self.stdout.write(f'   Type: {withdrawal.payout_type}')
            self.stdout.write(f'   Can Process Instant: {withdrawal.can_process_instant()}')
            
            # Update wallet
            wallet.withdraw(
                amount=test_amount,
                reason='Test instant withdrawal for approval testing',
                transaction_fee=Decimal('0.70')
            )
            
            self.stdout.write(f'   New balance: ${wallet.balance}')
            
        except Exception as e:
            self.stdout.write(f'Error creating withdrawal: {e}')
            return
        
        self.stdout.write(f'\\n--- EXPLANATION OF THE ISSUE ---')
        self.stdout.write('The weekly withdrawal you tried to approve (938b8fa9-f119-4104-9285-48b52e3278cb):')
        self.stdout.write('- Type: WEEKLY')
        self.stdout.write('- Behavior: Stays pending until weekly batch processing')
        self.stdout.write('- This is NORMAL behavior for weekly withdrawals')
        
        self.stdout.write(f'\\n--- TESTING INSTRUCTIONS ---')
        self.stdout.write('Now try approving this INSTANT withdrawal:')
        self.stdout.write(f'1. Go to admin withdrawal management page')
        self.stdout.write(f'2. Find withdrawal ID: {withdrawal.id}')
        self.stdout.write(f'3. Click "Approve" button')
        self.stdout.write(f'4. Status should change to "Completed" immediately')
        
        self.stdout.write(f'\\n--- EXPECTED BEHAVIOR FOR INSTANT ---')
        self.stdout.write('- Status: pending → processing → completed')
        self.stdout.write('- PayPal payment should process immediately')
        self.stdout.write('- Admin dashboard should show "Completed"')
        self.stdout.write('- Seller dashboard should show "Completed"')
        
        self.stdout.write(f'\\n--- IF IT STILL FAILS ---')
        self.stdout.write('1. Check browser console for JavaScript errors')
        self.stdout.write('2. Check network tab for API call failures')
        self.stdout.write('3. Verify PayPal API connection')
        self.stdout.write('4. Check withdrawal method is active')
        
        self.stdout.write(f'\\n=== TEST WITHDRAWAL READY ===')
        self.stdout.write(f'Instant withdrawal ID: {withdrawal.id}')
        self.stdout.write(f'Amount: ${withdrawal.amount}')
        self.stdout.write(f'Status: {withdrawal.status}')
        self.stdout.write(f'Type: {withdrawal.payout_type}')
        self.stdout.write(f'Ready for approval testing!')
        
        self.stdout.write(f'\\n--- KEY DIFFERENCE ---')
        self.stdout.write('WEEKLY withdrawals: Stay pending (normal behavior)')
        self.stdout.write('INSTANT withdrawals: Should complete immediately')
        self.stdout.write(f'Try approving the INSTANT withdrawal above!')
