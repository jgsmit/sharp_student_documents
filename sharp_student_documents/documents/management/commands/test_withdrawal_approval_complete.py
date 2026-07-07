from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from withdrawals.models import WithdrawalRequest, WithdrawalMethod
from sales.models import Wallet
from decimal import Decimal


class Command(BaseCommand):
    help = 'Create a test withdrawal and test the approval process'

    def handle(self, *args, **options):
        self.stdout.write('=== CREATE TEST WITHDRAWAL AND APPROVAL TEST ===')
        
        # Get Ripper user
        User = get_user_model()
        try:
            ripper = User.objects.get(username='Ripper')
            self.stdout.write(f'Found user: {ripper.username}')
        except User.DoesNotExist:
            self.stdout.write('Ripper user not found!')
            return
        
        # Check Ripper's wallet
        try:
            wallet = Wallet.objects.get(user=ripper)
            self.stdout.write(f'Current wallet balance: ${wallet.balance}')
        except Wallet.DoesNotExist:
            self.stdout.write('No wallet found for Ripper')
            return
        
        # Get Ripper's withdrawal method
        try:
            withdrawal_method = WithdrawalMethod.objects.get(
                user=ripper,
                method_type='paypal',
                is_active=True
            )
            self.stdout.write(f'Found withdrawal method: {withdrawal_method.method_type}')
            self.stdout.write(f'PayPal email: {withdrawal_method.paypal_email}')
        except WithdrawalMethod.DoesNotExist:
            self.stdout.write('No active PayPal withdrawal method found for Ripper')
            return
        
        # Create a small test withdrawal
        test_amount = Decimal('5.00')  # Small amount for testing
        
        if wallet.balance < test_amount:
            self.stdout.write(f'Insufficient balance: ${wallet.balance} < ${test_amount}')
            return
        
        self.stdout.write(f'\\n--- CREATING TEST WITHDRAWAL ---')
        self.stdout.write(f'Amount: ${test_amount}')
        self.stdout.write(f'Type: instant')
        self.stdout.write(f'Method: PayPal')
        
        try:
            # Create withdrawal request
            withdrawal = WithdrawalRequest.objects.create(
                user=ripper,
                withdrawal_method=withdrawal_method,
                amount=test_amount,
                fee=Decimal('0.10'),  # 2% fee
                net_amount=test_amount - Decimal('0.10'),
                payout_type='instant',
                status='pending'
            )
            
            self.stdout.write(f'\\nWithdrawal created successfully!')
            self.stdout.write(f'Withdrawal ID: {withdrawal.id}')
            self.stdout.write(f'Status: {withdrawal.status}')
            
            # Update wallet balance
            wallet.withdraw(
                amount=test_amount,
                reason='Test withdrawal request',
                transaction_fee=Decimal('0.10')
            )
            
            self.stdout.write(f'Wallet balance updated: ${wallet.balance}')
            
        except Exception as e:
            self.stdout.write(f'Error creating withdrawal: {e}')
            return
        
        # Test the approval process
        self.stdout.write(f'\\n--- TESTING APPROVAL PROCESS ---')
        
        # Import approval function
        from withdrawals.admin_views import approve_withdrawal
        from django.test import RequestFactory
        from django.contrib.messages import get_messages
        
        # Create a mock request
        factory = RequestFactory()
        request = factory.post(f'/admin/approve-withdrawal/{withdrawal.id}/')
        
        # Get an admin user
        try:
            admin_user = User.objects.get(is_superuser=True)
            request.user = admin_user
            self.stdout.write(f'Using admin user: {admin_user.username}')
        except User.DoesNotExist:
            self.stdout.write('No admin user found!')
            return
        
        # Test the approval
        self.stdout.write(f'\\nApproving withdrawal {withdrawal.id}...')
        
        try:
            # Call the approval function
            from django.http import JsonResponse
            result = approve_withdrawal(request, str(withdrawal.id))
            
            if isinstance(result, JsonResponse):
                # Parse the JSON response
                import json
                content = result.content.decode('utf-8')
                data = json.loads(content)
                
                self.stdout.write(f'Approval response: {data}')
                
                if data.get('success'):
                    self.stdout.write('✅ Approval successful!')
                    self.stdout.write(f'New status: {data.get("new_status")}')
                    self.stdout.write(f'Message: {data.get("message")}')
                else:
                    self.stdout.write('❌ Approval failed!')
                    self.stdout.write(f'Error: {data.get("error")}')
            else:
                self.stdout.write(f'Unexpected response type: {type(result)}')
                
        except Exception as e:
            self.stdout.write(f'Error during approval: {e}')
            return
        
        # Check the final status
        self.stdout.write(f'\\n--- FINAL STATUS CHECK ---')
        withdrawal.refresh_from_db()
        self.stdout.write(f'Withdrawal status: {withdrawal.status}')
        self.stdout.write(f'Processed at: {withdrawal.processed_at}')
        self.stdout.write(f'Completed at: {withdrawal.completed_at}')
        
        if withdrawal.failure_reason:
            self.stdout.write(f'Failure reason: {withdrawal.failure_reason}')
        
        # Check wallet balance
        wallet.refresh_from_db()
        self.stdout.write(f'Final wallet balance: ${wallet.balance}')
        
        # Check what seller dashboard would show
        self.stdout.write(f'\\n--- SELLER DASHBOARD VIEW ---')
        pending_withdrawals = WithdrawalRequest.objects.filter(
            user=ripper,
            status__in=['pending', 'processing', '2fa_required']
        )
        
        completed_withdrawals = WithdrawalRequest.objects.filter(
            user=ripper,
            status='completed'
        )
        
        pending_amount = sum(w.amount for w in pending_withdrawals)
        completed_amount = sum(w.amount for w in completed_withdrawals)
        
        self.stdout.write(f'Pending withdrawals: ${pending_amount} ({pending_withdrawals.count()} requests)')
        self.stdout.write(f'Completed withdrawals: ${completed_amount} ({completed_withdrawals.count()} requests)')
        
        self.stdout.write(f'\\n=== TEST COMPLETE ===')
        
        if withdrawal.status == 'completed':
            self.stdout.write('✅ SUCCESS: Withdrawal approved and completed!')
            self.stdout.write('Ripper should see this withdrawal as completed on the dashboard.')
        elif withdrawal.status == 'failed':
            self.stdout.write('❌ FAILED: Withdrawal approval failed during PayPal processing')
            self.stdout.write('Check the failure reason above.')
        else:
            self.stdout.write(f'⚠️  PENDING: Withdrawal status is {withdrawal.status}')
            self.stdout.write('The approval process may still be in progress.')
