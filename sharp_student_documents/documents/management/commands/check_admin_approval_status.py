from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from withdrawals.models import WithdrawalRequest
from django.utils import timezone


class Command(BaseCommand):
    help = 'Check current admin approval status and debug issues'

    def handle(self, *args, **options):
        self.stdout.write('=== ADMIN APPROVAL STATUS CHECK ===')
        
        # Check all pending withdrawals
        pending_withdrawals = WithdrawalRequest.objects.filter(status='pending').order_by('-requested_at')
        
        self.stdout.write(f'\\n--- PENDING WITHDRAWALS ({pending_withdrawals.count()}) ---')
        
        if not pending_withdrawals.exists():
            self.stdout.write('No pending withdrawals found.')
            self.stdout.write('All withdrawals have been processed!')
            return
        
        for withdrawal in pending_withdrawals:
            self.stdout.write(f'\\n--- Withdrawal #{withdrawal.id} ---')
            self.stdout.write(f'User: {withdrawal.user.username}')
            self.stdout.write(f'Amount: ${withdrawal.amount}')
            self.stdout.write(f'Type: {withdrawal.payout_type}')
            self.stdout.write(f'Method: {withdrawal.withdrawal_method.method_type}')
            self.stdout.write(f'Status: {withdrawal.status}')
            self.stdout.write(f'Requested: {withdrawal.requested_at}')
            self.stdout.write(f'Processed: {withdrawal.processed_at}')
            self.stdout.write(f'Completed: {withdrawal.completed_at}')
            
            if withdrawal.failure_reason:
                self.stdout.write(f'Failure Reason: {withdrawal.failure_reason}')
            
            # Check if it can be processed instantly
            can_instant = withdrawal.can_process_instant()
            self.stdout.write(f'Can Process Instant: {can_instant}')
            
            # Check withdrawal method details
            method = withdrawal.withdrawal_method
            self.stdout.write(f'Withdrawal Method: {method.method_type}')
            self.stdout.write(f'  PayPal Email: {method.paypal_email}')
            self.stdout.write(f'  Is Active: {method.is_active}')
        
        # Check recent approval attempts
        self.stdout.write(f'\\n--- RECENT APPROVAL ATTEMPTS ---')
        recent_withdrawals = WithdrawalRequest.objects.filter(
            processed_at__isnull=False
        ).order_by('-processed_at')[:10]
        
        for withdrawal in recent_withdrawals:
            self.stdout.write(f'\\n{withdrawal.processed_at.strftime("%Y-%m-%d %H:%M:%S")} - {withdrawal.id}')
            self.stdout.write(f'  User: {withdrawal.user.username}')
            self.stdout.write(f'  Amount: ${withdrawal.amount}')
            self.stdout.write(f'  Status: {withdrawal.status}')
            self.stdout.write(f'  Type: {withdrawal.payout_type}')
            
            if withdrawal.failure_reason:
                self.stdout.write(f'  Failure: {withdrawal.failure_reason}')
        
        # Check admin users
        self.stdout.write(f'\\n--- ADMIN USERS ---')
        User = get_user_model()
        admin_users = User.objects.filter(is_superuser=True)
        self.stdout.write(f'Admin users: {admin_users.count()}')
        
        for admin in admin_users:
            self.stdout.write(f'  - {admin.username} ({admin.email})')
        
        # Test PayPal configuration
        self.stdout.write(f'\\n--- PAYPAL CONFIGURATION ---')
        try:
            from django.conf import settings
            paypal_configured = (
                hasattr(settings, 'PAYPAL_CLIENT_ID') and 
                hasattr(settings, 'PAYPAL_CLIENT_SECRET') and
                hasattr(settings, 'PAYPAL_SANDBOX_REST_API')
            )
            self.stdout.write(f'PayPal Configured: {paypal_configured}')
            
            if paypal_configured:
                self.stdout.write(f'Client ID: {settings.PAYPAL_CLIENT_ID[:20]}...')
                self.stdout.write(f'Secret: {"***" if settings.PAYPAL_CLIENT_SECRET else "Missing"}')
                self.stdout.write(f'Sandbox API: {settings.PAYPAL_SANDBOX_REST_API}')
            else:
                self.stdout.write('PayPal not properly configured')
                
        except Exception as e:
            self.stdout.write(f'Configuration check error: {e}')
        
        # Check withdrawal service
        self.stdout.write(f'\\n--- WITHDRAWAL SERVICE CHECK ---')
        try:
            from withdrawals.services import WithdrawalService
            
            # Test if the service has the required methods
            has_instant = hasattr(WithdrawalService, 'process_instant_withdrawal')
            has_weekly = hasattr(WithdrawalService, 'queue_weekly_withdrawal')
            has_paypal = hasattr(WithdrawalService, '_process_paypal_instant')
            
            self.stdout.write(f'process_instant_withdrawal: {has_instant}')
            self.stdout.write(f'queue_weekly_withdrawal: {has_weekly}')
            self.stdout.write(f'_process_paypal_instant: {has_paypal}')
            
        except Exception as e:
            self.stdout.write(f'Service check error: {e}')
        
        # Manual approval test
        self.stdout.write(f'\\n--- MANUAL APPROVAL TEST ---')
        if pending_withdrawals.exists():
            test_withdrawal = pending_withdrawals.first()
            self.stdout.write(f'Testing approval for: {test_withdrawal.id}')
            
            try:
                # Simulate the approval process
                original_status = test_withdrawal.status
                self.stdout.write(f'Original status: {original_status}')
                
                # Check what should happen
                if test_withdrawal.can_process_instant():
                    self.stdout.write('Expected: Should process instantly via PayPal')
                else:
                    self.stdout.write('Expected: Should queue for weekly processing')
                
                # Check for potential issues
                issues = []
                
                if not test_withdrawal.withdrawal_method.is_active:
                    issues.append('Withdrawal method is not active')
                
                if test_withdrawal.amount <= 0:
                    issues.append('Invalid amount')
                
                if not hasattr(settings, 'PAYPAL_CLIENT_ID'):
                    issues.append('PayPal not configured')
                
                if issues:
                    self.stdout.write('Potential issues:')
                    for issue in issues:
                        self.stdout.write(f'  - {issue}')
                else:
                    self.stdout.write('No obvious issues found')
                    
            except Exception as e:
                self.stdout.write(f'Manual test error: {e}')
        
        self.stdout.write(f'\\n=== RECOMMENDATIONS ===')
        
        if pending_withdrawals.exists():
            self.stdout.write('1. Check browser console for JavaScript errors when clicking approve')
            self.stdout.write('2. Verify the AJAX request is being sent to the correct URL')
            self.stdout.write('3. Check network tab for failed requests')
            self.stdout.write('4. Try manual approval via command line')
            self.stdout.write('5. Check PayPal API connection')
        else:
            self.stdout.write('No pending withdrawals - system appears to be working!')
        
        self.stdout.write('\\nTo manually approve a withdrawal:')
        self.stdout.write('python manage.py manual_approve_withdrawal <withdrawal_id>')
