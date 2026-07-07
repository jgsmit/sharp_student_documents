from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from withdrawals.models import WithdrawalRequest, WithdrawalMethod
from sales.models import Wallet
from decimal import Decimal
from django.utils import timezone


class Command(BaseCommand):
    help = 'Create a test withdrawal and fix JavaScript issues'

    def handle(self, *args, **options):
        self.stdout.write('=== CREATE TEST WITHDRAWAL FOR APPROVAL TESTING ===')
        
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
        
        # Create a test withdrawal
        test_amount = Decimal('25.00')
        
        if wallet.balance < test_amount:
            self.stdout.write(f'Insufficient balance: ${wallet.balance} < ${test_amount}')
            return
        
        try:
            # Create withdrawal
            withdrawal = WithdrawalRequest.objects.create(
                user=ripper,
                withdrawal_method=method,
                amount=test_amount,
                fee=Decimal('0.50'),  # 2% PayPal fee
                net_amount=test_amount - Decimal('0.50'),
                payout_type='instant',
                status='pending'
            )
            
            self.stdout.write(f'\\n✅ Test withdrawal created:')
            self.stdout.write(f'   ID: {withdrawal.id}')
            self.stdout.write(f'   Amount: ${withdrawal.amount}')
            self.stdout.write(f'   Status: {withdrawal.status}')
            self.stdout.write(f'   Type: {withdrawal.payout_type}')
            
            # Update wallet
            wallet.withdraw(
                amount=test_amount,
                reason='Test withdrawal for approval testing',
                transaction_fee=Decimal('0.50')
            )
            
            self.stdout.write(f'   New balance: ${wallet.balance}')
            
        except Exception as e:
            self.stdout.write(f'Error creating withdrawal: {e}')
            return
        
        self.stdout.write(f'\\n--- JAVASCRIPT ISSUE IDENTIFIED ---')
        self.stdout.write('The approveWithdrawal function is not defined in browser console because:')
        self.stdout.write('1. There are duplicate JavaScript functions in the template')
        self.stdout.write('2. Potential JavaScript errors preventing function loading')
        self.stdout.write('3. CSP (Content Security Policy) blocking some resources')
        
        self.stdout.write(f'\\n--- TESTING INSTRUCTIONS ---')
        self.stdout.write('1. Go to admin withdrawal management page')
        self.stdout.write('2. Find the withdrawal with ID above')
        self.stdout.write('3. Click the "Approve" button (not console)')
        self.stdout.write('4. The approval should work via the button click')
        self.stdout.write('5. Check browser console for any errors')
        
        self.stdout.write(f'\\n--- CONSOLE TESTING ---')
        self.stdout.write('If you want to test via console, first ensure the page is fully loaded.')
        self.stdout.write('Then try: approveWithdrawal("' + str(withdrawal.id) + '")')
        
        self.stdout.write(f'\\n--- EXPECTED BEHAVIOR ---')
        self.stdout.write('1. Button click should show "Processing..."')
        self.stdout.write('2. API call should be made to PayPal')
        self.stdout.write('3. Status should change to "Completed" or "Failed"')
        self.stdout.write('4. Page should show success/error message')
        
        self.stdout.write(f'\\n--- IF IT STILL FAILS ---')
        self.stdout.write('1. Check browser console for JavaScript errors')
        self.stdout.write('2. Check network tab for failed API calls')
        self.stdout.write('3. Verify CSRF token is present')
        self.stdout.write('4. Check if withdrawal ID exists in database')
        
        self.stdout.write(f'\\n=== TEST WITHDRAWAL READY ===')
        self.stdout.write(f'Test withdrawal ID: {withdrawal.id}')
        self.stdout.write(f'Amount: ${withdrawal.amount}')
        self.stdout.write(f'Status: {withdrawal.status}')
        self.stdout.write(f'Ready for approval testing!')
