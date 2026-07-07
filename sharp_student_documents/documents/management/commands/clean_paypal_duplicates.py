from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from withdrawals.models import WithdrawalMethod


class Command(BaseCommand):
    help = 'Clean up duplicate PayPal withdrawal methods'

    def add_arguments(self, parser):
        parser.add_argument(
            '--username',
            type=str,
            help='Username to clean up (optional, cleans all if not provided)'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be cleaned without actually doing it'
        )

    def handle(self, *args, **options):
        username = options.get('username')
        dry_run = options.get('dry_run')
        
        self.stdout.write('=== CLEANING DUPLICATE PAYPAL METHODS ===')
        
        # Get all PayPal methods
        paypal_methods = WithdrawalMethod.objects.filter(method_type='paypal').order_by('user', 'created_at')
        
        if username:
            # Clean specific user
            user_methods = paypal_methods.filter(user__username=username)
            self.stdout.write(f'\nCleaning PayPal methods for user: {username}')
            self._clean_user_methods(user_methods, dry_run)
        else:
            # Clean all users
            self.stdout.write('\nCleaning PayPal methods for all users...')
            for user in get_user_model().objects.all():
                user_methods = paypal_methods.filter(user=user)
                if user_methods.exists():
                    self.stdout.write(f'\n--- User: {user.username} ---')
                    self._clean_user_methods(user_methods, dry_run)
        
        self.stdout.write('\n=== CLEANUP COMPLETE ===')
        if dry_run:
            self.stdout.write('(Dry run - no changes made)')
        else:
            self.stdout.write('Duplicate PayPal methods removed successfully!')

    def _clean_user_methods(self, user_methods, dry_run):
        """Clean PayPal methods for a specific user"""
        if not user_methods.exists():
            return
        
        # Group by email address
        emails = {}
        for method in user_methods:
            email = method.paypal_email
            if email not in emails:
                emails[email] = []
            emails[email].append(method)
        
        # Process each email group
        for email, methods in emails.items():
            if len(methods) > 1:
                self.stdout.write(f'  Found {len(methods)} duplicate PayPal methods for: {email}')
                
                # Keep the newest one, delete others
                newest_method = max(methods, key=lambda m: m.created_at)
                duplicates = [m for m in methods if m != newest_method]
                
                if duplicates:
                    self.stdout.write(f'    Keeping: Created {newest_method.created_at} (ID: {newest_method.id})')
                    self.stdout.write(f'    Removing {len(duplicates)} older duplicates:')
                    
                    for dup in duplicates:
                        self.stdout.write(f'      - Created {dup.created_at} (ID: {dup.id})')
                        if not dry_run:
                            dup.delete()
                
                # Make the kept method active and verified
                if not dry_run:
                    newest_method.is_active = True
                    newest_method.save()
            else:
                self.stdout.write(f'  Single PayPal method for {email}: OK')
