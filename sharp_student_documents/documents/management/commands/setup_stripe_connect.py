from django.core.management.base import BaseCommand
from django.conf import settings
import stripe
import os


class Command(BaseCommand):
    help = 'Setup and test Stripe Connect configuration'

    def add_arguments(self, parser):
        parser.add_argument(
            '--test-mode',
            action='store_true',
            help='Test with Stripe test keys (if available)'
        )
        parser.add_argument(
            '--check-webhook',
            action='store_true',
            help='Check webhook endpoint accessibility'
        )

    def handle(self, *args, **options):
        self.stdout.write('=== STRIPE CONNECT SETUP HELPER ===')
        
        # Check current configuration
        self.stdout.write('\n1. Checking current configuration...')
        
        stripe_config = {
            'secret_key': 'SET' if settings.STRIPE_SECRET_KEY else 'NOT SET',
            'publishable_key': 'SET' if settings.STRIPE_PUBLISHABLE_KEY else 'NOT SET',
            'webhook_secret': 'SET' if settings.STRIPE_WEBHOOK_SECRET else 'NOT SET',
        }
        
        for key, status in stripe_config.items():
            status_icon = '✅' if status == 'SET' else '❌'
            self.stdout.write(f'   {key}: {status} ({status})')
        
        # Test Stripe connection
        if settings.STRIPE_SECRET_KEY:
            self.stdout.write('\n2. Testing Stripe connection...')
            try:
                stripe.api_key = settings.STRIPE_SECRET_KEY
                
                # Test basic API call
                account_info = stripe.Account.list(limit=1)
                if account_info.data:
                    account = account_info.data[0]
                    self.stdout.write(self.style.SUCCESS('   ✅ Stripe API connection successful'))
                    self.stdout.write(f'   Account Type: {account.type}')
                    self.stdout.write(f'   Country: {account.country}')
                    self.stdout.write(f'   Capabilities: {list(account.capabilities.keys())}')
                    
                    # Check if Connect is enabled
                    if 'transfers' in account.capabilities:
                        self.stdout.write(self.style.SUCCESS('   ✅ Transfers capability enabled (Connect ready)'))
                    else:
                        self.stdout.write(self.style.WARNING('   ⚠️  Transfers capability NOT enabled'))
                        self.stdout.write('       → This account is not configured for Connect')
                        
                else:
                    self.stdout.write(self.style.WARNING('   ⚠️  No accounts found'))
                    
            except Exception as e:
                self.stdout.write(self.style.ERROR(f'   ❌ Stripe connection failed: {e}'))
        
        # Provide setup instructions
        self.stdout.write('\n3. Setup Instructions:')
        self.stdout.write('   a) Sign up for Stripe Connect: https://dashboard.stripe.com/register')
        self.stdout.write('   b) Choose "Platform" account type (not "Standard")')
        self.stdout.write('   c) Get Connect API keys from Developers → API keys')
        self.stdout.write('   d) Update environment variables:')
        self.stdout.write('      export STRIPE_SECRET_KEY="sk_live_..." or "sk_test_..."')
        self.stdout.write('      export STRIPE_PUBLISHABLE_KEY="pk_live_..." or "pk_test_..."')
        self.stdout.write('      export STRIPE_WEBHOOK_SECRET="whsec_..."')
        
        # Check webhook accessibility
        if options.get('check_webhook'):
            self.stdout.write('\n4. Checking webhook endpoint...')
            webhook_url = 'http://localhost:8000/withdrawals/stripe/webhook/'
            self.stdout.write(f'   Webhook URL: {webhook_url}')
            self.stdout.write('   → Make sure this URL is accessible from the internet')
            self.stdout.write('   → Use ngrok for testing: ngrok http 8000')
        
        # Test mode specific checks
        if options.get('test_mode'):
            self.stdout.write('\n5. Test Mode Configuration:')
            if settings.STRIPE_SECRET_KEY and settings.STRIPE_SECRET_KEY.startswith('sk_test_'):
                self.stdout.write(self.style.SUCCESS('   ✅ Using test keys'))
            elif settings.STRIPE_SECRET_KEY and settings.STRIPE_SECRET_KEY.startswith('sk_live_'):
                self.stdout.write(self.style.WARNING('   ⚠️  Using live keys in test environment'))
            else:
                self.stdout.write(self.style.ERROR('   ❌ No valid Stripe keys configured'))
        
        self.stdout.write('\n6. Next Steps:')
        self.stdout.write('   1. Complete Stripe Connect platform setup')
        self.stdout.write('   2. Update environment variables with your keys')
        self.stdout.write('   3. Run: python manage.py debug_stripe')
        self.stdout.write('   4. Test the Connect flow in your browser')
        self.stdout.write('   5. Check webhook delivery in Stripe Dashboard')
        
        self.stdout.write('\n7. Common Issues & Solutions:')
        self.stdout.write('   Issue: "Connect not enabled"')
        self.stdout.write('   Solution: Use a Stripe Connect platform account, not regular Stripe')
        self.stdout.write('   Issue: "No such account"')
        self.stdout.write('   Solution: Check if account was deleted or suspended')
        self.stdout.write('   Issue: "Invalid API key"')
        self.stdout.write('   Solution: Verify key is correct and not expired')
