from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from withdrawals.models import WithdrawalRequest
from withdrawals.services import WithdrawalService
from django.utils import timezone


class Command(BaseCommand):
    help = 'Debug PayPal processing during withdrawal approval'

    def handle(self, *args, **options):
        self.stdout.write('=== PAYPAL PROCESSING DEBUG ===')
        
        # Get a test withdrawal
        User = get_user_model()
        ripper = User.objects.get(username='Ripper')
        
        # Create a small test withdrawal
        from withdrawals.models import WithdrawalMethod
        from decimal import Decimal
        from sales.models import Wallet
        
        try:
            method = WithdrawalMethod.objects.get(user=ripper, method_type='paypal', is_active=True)
            wallet = Wallet.objects.get(user=ripper)
            
            if wallet.balance >= Decimal('10.00'):
                # Create test withdrawal
                withdrawal = WithdrawalRequest.objects.create(
                    user=ripper,
                    withdrawal_method=method,
                    amount=Decimal('10.00'),
                    fee=Decimal('0.20'),
                    net_amount=Decimal('9.80'),
                    payout_type='instant',
                    status='pending'
                )
                
                self.stdout.write(f'Created test withdrawal: {withdrawal.id}')
                
                # Test the approval process step by step
                self.stdout.write('\\n--- STEP 1: UPDATE TO PROCESSING ---')
                withdrawal.status = 'processing'
                withdrawal.processed_at = timezone.now()
                withdrawal.save()
                
                self.stdout.write(f'Status updated to: {withdrawal.status}')
                
                self.stdout.write('\\n--- STEP 2: TEST PAYPAL PROCESSING ---')
                
                try:
                    # Test PayPal configuration
                    from django.conf import settings
                    import paypalrestsdk
                    
                    paypalrestsdk.configure({
                        "mode": settings.PAYPAL_MODE,
                        "client_id": settings.PAYPAL_CLIENT_ID,
                        "client_secret": settings.PAYPAL_CLIENT_SECRET,
                    })
                    
                    self.stdout.write('PayPal SDK configured successfully')
                    
                    # Test a simple API call
                    self.stdout.write('Testing PayPal API connection...')
                    
                    # Create a test payout (this is what the approval process does)
                    payout = paypalrestsdk.Payout({
                        "sender_batch_header": {
                            "sender_batch_id": f"test_withdrawal_{withdrawal.id}",
                            "email_subject": "Test withdrawal from SharpDocs"
                        },
                        "items": [{
                            "recipient_type": "EMAIL",
                            "receiver": method.paypal_email,
                            "note": "Test withdrawal payment",
                            "sender_item_id": f"item_{withdrawal.id}",
                            "amount": {
                                "value": str(withdrawal.net_amount),
                                "currency": "USD"
                            }
                        }]
                    })
                    
                    self.stdout.write(f'Creating payout for ${withdrawal.net_amount} to {method.paypal_email}')
                    
                    if payout.create():
                        self.stdout.write('✅ PayPal payout created successfully!')
                        self.stdout.write(f'Payout ID: {payout.id}')
                        self.stdout.write(f'Batch ID: {payout.batch_header.payout_batch_id}')
                        
                        # Update withdrawal to completed
                        withdrawal.status = 'completed'
                        withdrawal.completed_at = timezone.now()
                        withdrawal.save()
                        
                        self.stdout.write(f'Withdrawal {withdrawal.id} marked as completed')
                        
                    else:
                        self.stdout.write('❌ PayPal payout creation failed!')
                        self.stdout.write(f'Error: {payout.error}')
                        
                        # Check the specific error
                        if hasattr(payout, 'error') and payout.error:
                            error = payout.error
                            self.stdout.write(f'Error details: {error}')
                            
                            # Common issues and solutions
                            if 'INSUFFICIENT_FUNDS' in str(error):
                                self.stdout.write('Issue: Insufficient funds in PayPal account')
                            elif 'RECEIVER_UNREGISTERED' in str(error):
                                self.stdout.write('Issue: Receiver email is not registered with PayPal')
                            elif 'INVALID_REQUEST' in str(error):
                                self.stdout.write('Issue: Invalid payout request format')
                            else:
                                self.stdout.write('Issue: Unknown PayPal API error')
                        
                        # Mark as failed for testing
                        withdrawal.status = 'failed'
                        withdrawal.failure_reason = f"PayPal payout failed: {payout.error}"
                        withdrawal.save()
                        
                        self.stdout.write(f'Withdrawal {withdrawal.id} marked as failed')
                
                except Exception as e:
                    self.stdout.write(f'PayPal processing error: {e}')
                    
                    # Mark as failed
                    withdrawal.status = 'failed'
                    withdrawal.failure_reason = f"PayPal processing error: {str(e)}"
                    withdrawal.save()
                
                # Check final status
                withdrawal.refresh_from_db()
                self.stdout.write(f'\\n--- FINAL STATUS ---')
                self.stdout.write(f'Withdrawal ID: {withdrawal.id}')
                self.stdout.write(f'Status: {withdrawal.status}')
                self.stdout.write(f'Processed: {withdrawal.processed_at}')
                self.stdout.write(f'Completed: {withdrawal.completed_at}')
                
                if withdrawal.failure_reason:
                    self.stdout.write(f'Failure Reason: {withdrawal.failure_reason}')
                
            else:
                self.stdout.write(f'Insufficient balance: ${wallet.balance}')
                
        except Exception as e:
            self.stdout.write(f'Test setup error: {e}')
        
        self.stdout.write('\\n=== DEBUG COMPLETE ===')
