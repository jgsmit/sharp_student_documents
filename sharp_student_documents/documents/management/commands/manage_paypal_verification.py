from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from withdrawals.models import WithdrawalMethod


class Command(BaseCommand):
    help = 'Manage PayPal withdrawal method verification'

    def add_arguments(self, parser):
        parser.add_argument(
            '--username',
            type=str,
            help='Username to check (optional, checks all if not provided)'
        )
        parser.add_argument(
            '--verify',
            action='store_true',
            help='Mark PayPal methods as verified'
        )
        parser.add_argument(
            '--list',
            action='store_true',
            help='List all PayPal methods'
        )

    def handle(self, *args, **options):
        username = options.get('username')
        verify = options.get('verify')
        list_methods = options.get('list')
        
        self.stdout.write('=== PAYPAL VERIFICATION MANAGER ===')
        
        # Get PayPal methods
        paypal_methods = WithdrawalMethod.objects.filter(method_type='paypal').order_by('user', 'created_at')
        
        if username:
            paypal_methods = paypal_methods.filter(user__username=username)
            self.stdout.write(f'\nManaging PayPal methods for user: {username}')
        else:
            self.stdout.write('\nManaging PayPal methods for all users...')
        
        if list_methods:
            self._list_methods(paypal_methods)
        elif verify:
            self._verify_methods(paypal_methods)
        else:
            self._show_status(paypal_methods)
        
        self.stdout.write('\n=== VERIFICATION COMPLETE ===')

    def _list_methods(self, paypal_methods):
        """List all PayPal methods"""
        self.stdout.write('\n--- PayPal Methods ---')
        for method in paypal_methods:
            status = 'Active' if method.is_active else 'Inactive'
            verified = 'Verified' if method.is_verified else 'Not Verified'
            self.stdout.write(
                f'  {method.user.username} | {method.paypal_email} | '
                f'{status} | {verified} | Created {method.created_at.strftime("%Y-%m-%d %H:%M")}'
            )

    def _verify_methods(self, paypal_methods):
        """Mark PayPal methods as verified"""
        self.stdout.write('\n--- Verifying PayPal Methods ---')
        updated_count = 0
        
        for method in paypal_methods:
            if not method.is_verified:
                method.is_verified = True
                method.save()
                updated_count += 1
                self.stdout.write(f'  Verified: {method.paypal_email} ({method.user.username})')
        
        if updated_count > 0:
            self.stdout.write(f'\nVerified {updated_count} PayPal methods')
        else:
            self.stdout.write('\nAll PayPal methods already verified')

    def _show_status(self, paypal_methods):
        """Show current verification status"""
        self.stdout.write('\n--- PayPal Status Summary ---')
        
        # Group by user
        users = {}
        for method in paypal_methods:
            user = method.user.username
            if user not in users:
                users[user] = {'total': 0, 'verified': 0, 'active': 0}
            users[user]['total'] += 1
            if method.is_verified:
                users[user]['verified'] += 1
            if method.is_active:
                users[user]['active'] += 1
        
        for username, stats in users.items():
            status_icon = 'Verified' if stats['verified'] > 0 else 'Not Verified'
            active_icon = 'Active' if stats['active'] > 0 else 'Inactive'
            
            self.stdout.write(
                f'  {username}: {stats["total"]} methods | '
                f'{status_icon} {stats["verified"]} verified | '
                f'{active_icon} {stats["active"]} active'
            )
