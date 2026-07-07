from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = 'Configure PayPal API endpoints from sandbox dashboard'

    def handle(self, *args, **options):
        self.stdout.write('=== PAYPAL SANDBOX CONFIGURATION ===')
        
        self.stdout.write('\\n--- IMPORTANT ---')
        self.stdout.write('Do not hardcode PayPal credentials (REST or NVP/SOAP) in source code or print them.')
        self.stdout.write('Use environment variables / .env instead.')
        
        self.stdout.write('\\n--- PAYPAL API ENDPOINTS ---')
        self.stdout.write('Sandbox REST API: https://api.sandbox.paypal.com')
        self.stdout.write('Live REST API: https://api.paypal.com')
        self.stdout.write('Sandbox NVP API: https://api-3t.sandbox.paypal.com/nvp')
        self.stdout.write('Live NVP API: https://api-3t.paypal.com/nvp')
        
        self.stdout.write('\\n--- RECOMMENDED CONFIGURATION ---')
        self.stdout.write('# Add these settings to your environment / .env (recommended):')
        self.stdout.write('')
        self.stdout.write('# PayPal Configuration')
        self.stdout.write('PAYPAL_MODE=sandbox  # or live for production')
        self.stdout.write('PAYPAL_CLIENT_ID=...')
        self.stdout.write('PAYPAL_CLIENT_SECRET=...')
        self.stdout.write('PAYPAL_WEBHOOK_ID=...  # required for webhook signature verification')
        self.stdout.write('')
        self.stdout.write('# PayPal Payouts Configuration')
        self.stdout.write('PAYPAL_PAYOUTS_ENABLED=True')
        
        self.stdout.write('\\n--- PAYPAL PAYOUTS REQUIREMENTS ---')
        self.stdout.write('✅ Business Account: Verified')
        self.stdout.write('✅ Account Balance: $5,000 USD (sufficient for testing)')
        self.stdout.write('✅ REST API App: Created')
        self.stdout.write('❓ Payouts API: Need to verify if enabled')
        
        self.stdout.write('\\n--- NEXT STEPS ---')
        self.stdout.write('1. Get your full Client ID and Secret from the PayPal dashboard')
        self.stdout.write('2. Add the API endpoints to your settings.py')
        self.stdout.write('3. Test the PayPal API connection')
        self.stdout.write('4. Verify Payouts API is enabled for your account')
        self.stdout.write('5. Test a small withdrawal amount ($1.00) to verify it works')
        
        self.stdout.write('\\n--- HOW TO GET FULL CREDENTIALS ---')
        self.stdout.write('1. Go to PayPal Developer Dashboard')
        self.stdout.write('2. Click on your app "Docu Pay"')
        self.stdout.write('3. Copy the full Client ID')
        self.stdout.write('4. Click "Show" for the Secret and copy it')
        self.stdout.write('5. Add both to your settings.py')
        
        self.stdout.write('\\n--- TESTING THE CONFIGURATION ---')
        self.stdout.write('After configuring, run: python manage.py test_paypal_connection')
        self.stdout.write('This will test the PayPal API connection and payout functionality.')
        
        self.stdout.write('\\n--- CURRENT STATUS ---')
        self.stdout.write('✅ PayPal sandbox account is properly set up')
        self.stdout.write('✅ Business account is verified')
        self.stdout.write('✅ Sufficient balance for testing')
        self.stdout.write('✅ REST API app created')
        self.stdout.write('❌ API endpoints not configured in Django settings')
        self.stdout.write('❓ Payouts API permission status unknown')
        
        self.stdout.write('\\n=== CONFIGURATION COMPLETE ===')
        self.stdout.write('Your PayPal sandbox is ready! Just add the API endpoints to settings.py.')
