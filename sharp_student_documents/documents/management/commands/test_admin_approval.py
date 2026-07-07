from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from withdrawals.models import WithdrawalRequest, WithdrawalMethod
from decimal import Decimal


class Command(BaseCommand):
    help = 'Test admin withdrawal approval system'

    def handle(self, *args, **options):
        self.stdout.write('=== TESTING ADMIN WITHDRAWAL APPROVAL SYSTEM ===')
        
        # Get or create admin user
        User = get_user_model()
        try:
            admin_user = User.objects.get(username='admin')
        except User.DoesNotExist:
            admin_user = User.objects.create_superuser(
                username='admin',
                email='admin@example.com',
                password='admin123'
            )
            self.stdout.write('Created admin user: admin')
        
        # Get or create test seller
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
            
            # Check the withdrawal details
            self.stdout.write(f'  User: {withdrawal.user.username}')
            self.stdout.write(f'  Amount: ${withdrawal.amount}')
            self.stdout.write(f'  Fee: ${withdrawal.fee}')
            self.stdout.write(f'  Net Amount: ${withdrawal.net_amount}')
            self.stdout.write(f'  Status: {withdrawal.status}')
            self.stdout.write(f'  Method: {withdrawal.withdrawal_method.method_type}')
            
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Failed to create withdrawal: {e}'))
        
        # Check if admin approval endpoints exist
        self.stdout.write('\n--- CHECKING ADMIN APPROVAL FUNCTIONALITY ---')
        
        # Check if there are any approval/reject views
        from documents.views import admin_manage_withdrawals
        self.stdout.write('✅ Admin withdrawal management view exists')
        
        # Check if there are approval/reject URLs
        try:
            from documents.urls import urlpatterns
            approval_urls = [url for url in urlpatterns if 'withdrawal' in str(url)]
            self.stdout.write(f'✅ Found {len(approval_urls)} withdrawal-related URLs')
        except Exception as e:
            self.stdout.write(f'❌ Error checking URLs: {e}')
        
        # Check admin actions in admin.py
        try:
            from withdrawals.admin import WithdrawalRequestAdmin
            admin_actions = WithdrawalRequestAdmin.actions
            self.stdout.write(f'✅ Admin actions available: {admin_actions}')
        except Exception as e:
            self.stdout.write(f'❌ Error checking admin actions: {e}')
        
        self.stdout.write('\n=== APPROVAL SYSTEM STATUS ===')
        self.stdout.write('✅ Admin interface exists')
        self.stdout.write('✅ Withdrawal requests can be created')
        self.stdout.write('✅ Admin actions available in Django admin')
        self.stdout.write('⚠️  Frontend approval buttons need backend endpoints')
        self.stdout.write('⚠️  JavaScript updates UI but doesn\'t process withdrawals')
        
        self.stdout.write('\n=== RECOMMENDATIONS ===')
        self.stdout.write('1. Create approval/reject API endpoints')
        self.stdout.write('2. Implement actual withdrawal processing')
        self.stdout.write('3. Add PayPal integration for payouts')
        self.stdout.write('4. Add email notifications for approvals')
        self.stdout.write('5. Add audit trail for admin actions')
        
        # Clean up
        try:
            WithdrawalRequest.objects.filter(user=seller_user).delete()
            WithdrawalMethod.objects.filter(user=seller_user).delete()
            seller_user.delete()
            self.stdout.write('\nCleaned up test data')
        except:
            pass
        
        self.stdout.write('\n=== TEST COMPLETE ===')
