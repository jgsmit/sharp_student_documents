from django.core.management.base import BaseCommand
from django.conf import settings
import stripe


class Command(BaseCommand):
    help = 'Debug Stripe Connect configuration'

    def handle(self, *args, **options):
        self.stdout.write('=== STRIPE CONFIGURATION DEBUG ===')
        
        # Check environment variables
        self.stdout.write(f'STRIPE_SECRET_KEY: {"SET" if settings.STRIPE_SECRET_KEY else "NOT SET"}')
        self.stdout.write(f'STRIPE_PUBLISHABLE_KEY: {"SET" if settings.STRIPE_PUBLISHABLE_KEY else "NOT SET"}')
        self.stdout.write(f'STRIPE_WEBHOOK_SECRET: {"SET" if settings.STRIPE_WEBHOOK_SECRET else "NOT SET"}')
        
        if settings.STRIPE_SECRET_KEY:
            # Test Stripe connection
            try:
                stripe.api_key = settings.STRIPE_SECRET_KEY
                
                # Test basic Stripe API call
                account_info = stripe.Account.list(limit=1)
                self.stdout.write(self.style.SUCCESS('Stripe API connection successful'))
                self.stdout.write(f'   Connected to Stripe as: {account_info.data[0].business_profile.name if account_info.data else "Test Account"}')
                
                # Test creating an Express account link
                try:
                    account = stripe.Account.create(
                        type='express',
                        country='US',
                        email='test@example.com',
                        capabilities={
                            'card_payments': {'requested': True},
                            'transfers': {'requested': True},
                        },
                        business_type='individual',
                    )
                    
                    account_link = stripe.AccountLink.create(
                        account=account.id,
                        refresh_url='http://localhost:8000/withdrawals/stripe/refresh/',
                        return_url='http://localhost:8000/withdrawals/stripe/return/',
                        type='account_onboarding',
                    )
                    
                    self.stdout.write(self.style.SUCCESS('Stripe Express account creation successful'))
                    self.stdout.write(f'   Account ID: {account.id}')
                    self.stdout.write(f'   Account Link: {account_link.url}')
                    
                    # Clean up test account
                    stripe.Account.delete(account.id)
                    
                except Exception as e:
                    self.stdout.write(self.style.ERROR(f'Stripe Express account creation failed: {e}'))
                
            except Exception as e:
                self.stdout.write(self.style.ERROR(f'Stripe API Error: {e}'))
                self.stdout.write(f'   Error Type: {type(e).__name__}')
                self.stdout.write(f'   Error Code: {getattr(e, "code", "N/A")}')
                
            except Exception as e:
                self.stdout.write(self.style.ERROR('General Error: {e}'))
        else:
            self.stdout.write(self.style.ERROR('STRIPE_SECRET_KEY is not configured'))
            self.stdout.write('   Please set the STRIPE_SECRET_KEY environment variable')
        
        self.stdout.write('\n=== RECOMMENDATIONS ===')
        self.stdout.write('1. Ensure STRIPE_SECRET_KEY is set in your environment')
        self.stdout.write('2. Use a valid Stripe secret key (not publishable key)')
        self.stdout.write('3. Configure your Stripe account for Express Connect')
        self.stdout.write('4. Set up webhook endpoints in Stripe Dashboard')
