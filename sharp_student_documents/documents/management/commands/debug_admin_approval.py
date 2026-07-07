from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from withdrawals.models import WithdrawalRequest
from withdrawals.admin_views import approve_withdrawal
from django.test import RequestFactory
from django.contrib.sessions.middleware import SessionMiddleware
from django.contrib.messages.middleware import MessageMiddleware
from django.contrib.auth.middleware import AuthenticationMiddleware

User = get_user_model()


class Command(BaseCommand):
    help = 'Debug admin approval process for Ripper withdrawals'

    def handle(self, *args, **options):
        self.stdout.write('=== ADMIN APPROVAL DEBUG ===')
        
        # Get Ripper's pending withdrawals
        pending_withdrawals = WithdrawalRequest.objects.filter(
            user__username='Ripper',
            status='pending'
        ).order_by('-requested_at')
        
        if not pending_withdrawals.exists():
            self.stdout.write('No pending withdrawals found for Ripper')
            return
        
        self.stdout.write(f'Found {pending_withdrawals.count()} pending withdrawals for Ripper:')
        
        for withdrawal in pending_withdrawals:
            self.stdout.write(f'\\n--- Withdrawal #{withdrawal.id} ---')
            self.stdout.write(f'Amount: ${withdrawal.amount}')
            self.stdout.write(f'Type: {withdrawal.payout_type}')
            self.stdout.write(f'Status: {withdrawal.status}')
            self.stdout.write(f'Method: {withdrawal.withdrawal_method.method_type}')
            self.stdout.write(f'Requested: {withdrawal.requested_at}')
            self.stdout.write(f'Processed: {withdrawal.processed_at}')
            self.stdout.write(f'Completed: {withdrawal.completed_at}')
            self.stdout.write(f'Can Process Instant: {withdrawal.can_process_instant()}')
            
            # Check withdrawal method details
            method = withdrawal.withdrawal_method
            self.stdout.write(f'Withdrawal Method Details:')
            self.stdout.write(f'  Type: {method.method_type}')
            self.stdout.write(f'  PayPal Email: {method.paypal_email}')
            self.stdout.write(f'  Stripe Account: {method.stripe_account_id}')
            self.stdout.write(f'  Is Active: {method.is_active}')
            
            # Check if there are any issues with the withdrawal
            self.stdout.write(f'\\nWithdrawal Validation:')
            self.stdout.write(f'  Status is pending: {withdrawal.status == "pending"}')
            self.stdout.write(f'  Has withdrawal method: {withdrawal.withdrawal_method is not None}')
            self.stdout.write(f'  Method is active: {method.is_active}')
            self.stdout.write(f'  Amount > 0: {withdrawal.amount > 0}')
            
            # Check for potential issues
            issues = []
            if withdrawal.status != 'pending':
                issues.append(f'Status is not pending: {withdrawal.status}')
            if not withdrawal.withdrawal_method:
                issues.append('No withdrawal method')
            if not method.is_active:
                issues.append('Withdrawal method is not active')
            if withdrawal.amount <= 0:
                issues.append('Amount is not positive')
            
            if issues:
                self.stdout.write(f'  ISSUES FOUND: {", ".join(issues)}')
            else:
                self.stdout.write(f'  No issues found - should be approvable')
        
        # Check if there are any admin users
        self.stdout.write(f'\\n--- ADMIN USERS ---')
        admin_users = User.objects.filter(is_superuser=True)
        self.stdout.write(f'Admin users: {admin_users.count()}')
        for admin in admin_users:
            self.stdout.write(f'  - {admin.username} ({admin.email})')
        
        # Check the admin approval URL
        self.stdout.write(f'\\n--- ADMIN APPROVAL URL ---')
        for withdrawal in pending_withdrawals:
            url = f'/documents/admin/approve-withdrawal/{withdrawal.id}/'
            self.stdout.write(f'Withdrawal {withdrawal.id}: {url}')
        
        # Check what happens when we simulate approval
        self.stdout.write(f'\\n--- SIMULATE APPROVAL PROCESS ---')
        for withdrawal in pending_withdrawals:
            self.stdout.write(f'\\nSimulating approval for withdrawal {withdrawal.id}:')
            
            # Check initial state
            original_status = withdrawal.status
            self.stdout.write(f'  Initial status: {original_status}')
            
            # Check if it can be processed instantly
            can_instant = withdrawal.can_process_instant()
            self.stdout.write(f'  Can process instant: {can_instant}')
            
            if can_instant:
                self.stdout.write(f'  Expected flow: pending -> processing -> completed')
            else:
                self.stdout.write(f'  Expected flow: pending -> processing -> pending (weekly)')
            
            # Check for any potential processing errors
            try:
                # Check PayPal configuration
                from django.conf import settings
                paypal_configured = hasattr(settings, 'PAYPAL_REST_API') and settings.PAYPAL_REST_API
                self.stdout.write(f'  PayPal configured: {paypal_configured}')
                
                if not paypal_configured and withdrawal.withdrawal_method.method_type == 'paypal':
                    self.stdout.write(f'  WARNING: PayPal not configured - approval may fail')
                
            except Exception as e:
                self.stdout.write(f'  Configuration check error: {e}')
        
        # Check recent approval attempts
        self.stdout.write(f'\\n--- RECENT APPROVAL ATTEMPTS ---')
        processed_withdrawals = WithdrawalRequest.objects.filter(
            user__username='Ripper',
            processed_at__isnull=False
        ).order_by('-processed_at')[:5]
        
        for withdrawal in processed_withdrawals:
            self.stdout.write(f'Withdrawal {withdrawal.id}:')
            self.stdout.write(f'  Status: {withdrawal.status}')
            self.stdout.write(f'  Processed: {withdrawal.processed_at}')
            self.stdout.write(f'  Completed: {withdrawal.completed_at}')
            if withdrawal.failure_reason:
                self.stdout.write(f'  Failure Reason: {withdrawal.failure_reason}')
        
        # Check for JavaScript or frontend issues
        self.stdout.write(f'\\n--- POTENTIAL FRONTEND ISSUES ---')
        self.stdout.write('Common issues with approval button:')
        self.stdout.write('1. JavaScript errors preventing AJAX call')
        self.stdout.write('2. CSRF token issues')
        self.stdout.write('3. Network connectivity problems')
        self.stdout.write('4. Browser caching issues')
        self.stdout.write('5. Permission issues (user not superadmin)')
        
        # Provide troubleshooting steps
        self.stdout.write(f'\\n--- TROUBLESHOOTING STEPS ---')
        self.stdout.write('1. Check browser console for JavaScript errors')
        self.stdout.write('2. Verify admin user is superuser')
        self.stdout.write('3. Check network tab for failed AJAX requests')
        self.stdout.write('4. Try hard refresh (Ctrl+F5) on admin page')
        self.stdout.write('5. Check if withdrawal status actually changes in database')
        self.stdout.write('6. Verify PayPal API configuration')
        
        # Create a test approval command
        self.stdout.write(f'\\n--- MANUAL APPROVAL TEST ---')
        self.stdout.write('To manually test approval:')
        for withdrawal in pending_withdrawals:
            self.stdout.write(f'python manage.py manual_approve_withdrawal {withdrawal.id}')
        
        self.stdout.write(f'\\n=== RECOMMENDATIONS ===')
        self.stdout.write('1. Check browser console for JavaScript errors when clicking approve')
        self.stdout.write('2. Verify the AJAX request is being sent to the correct URL')
        self.stdout.write('3. Check if the admin user has proper permissions')
        self.stdout.write('4. Test manual approval to bypass frontend issues')
        self.stdout.write('5. Check PayPal API configuration for instant withdrawals')
