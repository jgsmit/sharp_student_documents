from django.core.management.base import BaseCommand
import requests
from django.conf import settings

class Command(BaseCommand):
    help = 'Test PayPal API credentials'

    def handle(self, *args, **options):
        self.stdout.write("=== PayPal Environment Variables ===")
        self.stdout.write(f"PAYPAL_CLIENT_ID: {getattr(settings, 'PAYPAL_CLIENT_ID', 'NOT_FOUND')}")
        self.stdout.write(f"PAYPAL_CLIENT_SECRET: {'SET' if getattr(settings, 'PAYPAL_CLIENT_SECRET', None) else 'NOT_FOUND'}")
        self.stdout.write(f"PAYPAL_MODE: {getattr(settings, 'PAYPAL_MODE', 'NOT_FOUND')}")

        client_id = getattr(settings, 'PAYPAL_CLIENT_ID', None)
        client_secret = getattr(settings, 'PAYPAL_CLIENT_SECRET', None)

        if client_id and client_secret:
            try:
                resp = requests.post(
                    "https://api-m.sandbox.paypal.com/v1/oauth2/token",
                    auth=(client_id, client_secret),
                    data={"grant_type": "client_credentials"},
                )
                self.stdout.write(f"\n=== PayPal API Test ===")
                self.stdout.write(f"Status Code: {resp.status_code}")
                if resp.status_code == 200:
                    self.stdout.write(self.style.SUCCESS("PayPal API connection successful!"))
                else:
                    self.stdout.write(self.style.ERROR(f"Error: {resp.text}"))
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"Exception: {e}"))
        else:
            self.stdout.write(self.style.ERROR("Missing PayPal credentials in settings"))
