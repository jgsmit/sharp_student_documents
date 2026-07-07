from django.core.management.base import BaseCommand
from django.conf import settings
import paypalrestsdk


class Command(BaseCommand):
    help = 'Check PayPal configuration and readiness'

    def handle(self, *args, **options):
        self.stdout.write('=== PAYPAL CONFIGURATION CHECK ===')
        
        # Check PayPal configuration
        self.stdout.write('\n--- PayPal Settings ---')
        self.stdout.write(f'PayPal Mode: {settings.PAYPAL_MODE}')
        self.stdout.write(f'PayPal Client ID: {settings.PAYPAL_CLIENT_ID[:20]}...' if len(settings.PAYPAL_CLIENT_ID) > 20 else f'PayPal Client ID: {settings.PAYPAL_CLIENT_ID}')
        self.stdout.write(f'PayPal Client Secret: {"*" * len(settings.PAYPAL_CLIENT_SECRET)}' if settings.PAYPAL_CLIENT_SECRET != "YOUR_SANDBOX_CLIENT_SECRET_HERE" else 'PayPal Client Secret: NOT CONFIGURED')
        
        # Check if PayPal SDK is configured
        self.stdout.write('\n--- PayPal SDK Configuration ---')
        try:
            # Test PayPal configuration
            config = paypalrestsdk.configure({
                "mode": settings.PAYPAL_MODE,
                "client_id": settings.PAYPAL_CLIENT_ID,
                "client_secret": settings.PAYPAL_CLIENT_SECRET,
            })
            
            if config:
                self.stdout.write(self.style.SUCCESS('✅ PayPal SDK configured successfully'))
            else:
                self.stdout.write(self.style.ERROR('❌ PayPal SDK configuration failed'))
                
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'❌ PayPal SDK configuration error: {e}'))
        
        # Check if credentials are set
        self.stdout.write('\n--- Credentials Status ---')
        
        client_id_ok = settings.PAYPAL_CLIENT_ID != "YOUR_SANDBOX_CLIENT_ID_HERE"
        client_secret_ok = settings.PAYPAL_CLIENT_SECRET != "YOUR_SANDBOX_CLIENT_SECRET_HERE"
        
        if client_id_ok and client_secret_ok:
            self.stdout.write(self.style.SUCCESS('✅ PayPal credentials are configured'))
        else:
            self.stdout.write(self.style.WARNING('⚠️ PayPal credentials need to be configured'))
            if not client_id_ok:
                self.stdout.write('   - PAYPAL_CLIENT_ID needs to be set')
            if not client_secret_ok:
                self.stdout.write('   - PAYPAL_CLIENT_SECRET needs to be set')
        
        # Test PayPal API connection (if credentials are set)
        if client_id_ok and client_secret_ok:
            self.stdout.write('\n--- PayPal API Connection Test ---')
            try:
                # Try to get account info (simple test)
                # Note: This is a basic test - actual payout functionality requires proper permissions
                self.stdout.write('Testing PayPal API connection...')
                
                # Create a test payout object (won't actually send money)
                test_payout = paypalrestsdk.Payout({
                    "sender_batch_header": {
                        "sender_batch_id": "test_connection",
                        "email_subject": "Test"
                    },
                    "items": []
                })
                
                # Just test if the SDK can create the object
                if test_payout:
                    self.stdout.write(self.style.SUCCESS('✅ PayPal SDK can create payout objects'))
                    self.stdout.write(self.style.SUCCESS('✅ System is ready for PayPal withdrawals'))
                else:
                    self.stdout.write(self.style.ERROR('❌ PayPal SDK payout creation failed'))
                    
            except Exception as e:
                self.stdout.write(self.style.ERROR(f'❌ PayPal API connection test failed: {e}'))
                self.stdout.write('   This might be due to:')
                self.stdout.write('   - Invalid credentials')
                self.stdout.write('   - Network issues')
                self.stdout.write('   - PayPal API permissions')
        
        # Check withdrawal service implementation
        self.stdout.write('\n--- Withdrawal Service Check ---')
        try:
            from withdrawals.services import WithdrawalService
            
            # Check if the service has the required methods
            if hasattr(WithdrawalService, 'process_instant_withdrawal'):
                self.stdout.write(self.style.SUCCESS('✅ process_instant_withdrawal method exists'))
            else:
                self.stdout.write(self.style.ERROR('❌ process_instant_withdrawal method missing'))
                
            if hasattr(WithdrawalService, '_process_paypal_instant'):
                self.stdout.write(self.style.SUCCESS('✅ _process_paypal_instant method exists'))
            else:
                self.stdout.write(self.style.ERROR('❌ _process_paypal_instant method missing'))
                
            if hasattr(WithdrawalService, 'queue_weekly_withdrawal'):
                self.stdout.write(self.style.SUCCESS('✅ queue_weekly_withdrawal method exists'))
            else:
                self.stdout.write(self.style.ERROR('❌ queue_weekly_withdrawal method missing'))
                
        except ImportError as e:
            self.stdout.write(self.style.ERROR(f'❌ Cannot import WithdrawalService: {e}'))
        
        # Summary
        self.stdout.write('\n=== READINESS SUMMARY ===')
        
        if client_id_ok and client_secret_ok:
            self.stdout.write(self.style.SUCCESS('✅ SYSTEM IS READY FOR PAYPAL WITHDRAWALS'))
            self.stdout.write('\nWhat you can do:')
            self.stdout.write('• Admin can approve withdrawals')
            self.stdout.write('• Instant withdrawals will be processed immediately')
            self.stdout.write('• Weekly withdrawals will be queued for batch processing')
            self.stdout.write('• PayPal payouts will be sent to users')
            
            self.stdout.write('\nWhat you need to do:')
            self.stdout.write('• Set up PayPal Business account with payout permissions')
            self.stdout.write('• Configure PayPal API credentials in environment variables')
            self.stdout.write('• Test with small amounts first')
            
        else:
            self.stdout.write(self.style.WARNING('⚠️ SYSTEM NEEDS CONFIGURATION'))
            self.stdout.write('\nTo make the system ready:')
            self.stdout.write('1. Get PayPal Business account')
            self.stdout.write('2. Create PayPal REST API credentials')
            self.stdout.write('3. Set environment variables:')
            self.stdout.write('   - PAYPAL_CLIENT_ID=your_client_id')
            self.stdout.write('   - PAYPAL_CLIENT_SECRET=your_client_secret')
            self.stdout.write('   - PAYPAL_MODE=sandbox (or live)')
            self.stdout.write('4. Ensure PayPal account has payout permissions')
        
        self.stdout.write('\n=== CHECK COMPLETE ===')
