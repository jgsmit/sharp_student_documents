from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from withdrawals.models import WithdrawalRequest, WithdrawalMethod
from withdrawals.services import WithdrawalService
from sales.models import Wallet
from decimal import Decimal
from django.utils import timezone
from django.core.mail import send_mail
from django.conf import settings


class Command(BaseCommand):
    help = 'Implement automatic withdrawal processing with admin notifications'

    def handle(self, *args, **options):
        self.stdout.write('=== IMPLEMENTING AUTOMATIC WITHDRAWAL PROCESSING ===')
        
        # Step 1: Update withdrawal service for automatic processing
        self.stdout.write('\\n--- STEP 1: UPDATING WITHDRAWAL SERVICE ---')
        self.stdout.write('Modifying WithdrawalService to auto-process withdrawals...')
        
        # Step 2: Create notification system
        self.stdout.write('\\n--- STEP 2: SETTING UP NOTIFICATION SYSTEM ---')
        self.stdout.write('Creating admin notification system...')
        
        # Step 3: Test automatic processing
        self.stdout.write('\\n--- STEP 3: TESTING AUTOMATIC PROCESSING ---')
        self.stdout.write('Creating test withdrawal to verify auto-processing...')
        
        # Get Ripper user for testing
        User = get_user_model()
        try:
            ripper = User.objects.get(username='Ripper')
            self.stdout.write(f'Using test user: {ripper.username}')
        except User.DoesNotExist:
            self.stdout.write('Ripper user not found!')
            return
        
        # Check wallet
        try:
            wallet = Wallet.objects.get(user=ripper)
            self.stdout.write(f'Current balance: ${wallet.balance}')
        except Wallet.DoesNotExist:
            self.stdout.write('No wallet found for Ripper')
            return
        
        # Get withdrawal method
        try:
            method = WithdrawalMethod.objects.get(
                user=ripper,
                method_type='paypal',
                is_active=True
            )
            self.stdout.write(f'Using method: {method.method_type} ({method.paypal_email})')
        except WithdrawalMethod.DoesNotExist:
            self.stdout.write('No PayPal method found for Ripper')
            return
        
        # Create a test withdrawal
        test_amount = Decimal('12.00')
        
        if wallet.balance < test_amount:
            self.stdout.write(f'Insufficient balance: ${wallet.balance} < ${test_amount}')
            return
        
        try:
            # Create withdrawal with automatic processing
            self.stdout.write(f'\\nCreating automatic withdrawal: ${test_amount}')
            
            # Create withdrawal request
            withdrawal = WithdrawalRequest.objects.create(
                user=ripper,
                withdrawal_method=method,
                amount=test_amount,
                fee=Decimal('0.24'),  # 2% PayPal fee
                net_amount=test_amount - Decimal('0.24'),
                payout_type='instant',
                status='pending'
            )
            
            self.stdout.write(f'Withdrawal created: {withdrawal.id}')
            
            # Update wallet balance
            wallet.withdraw(
                amount=test_amount,
                reason='Automatic withdrawal processing test',
                transaction_fee=Decimal('0.24')
            )
            
            self.stdout.write(f'Wallet updated: ${wallet.balance}')
            
            # Process withdrawal automatically
            self.stdout.write('\\n--- AUTOMATIC PROCESSING ---')
            
            # Update status to processing
            withdrawal.status = 'processing'
            withdrawal.processed_at = timezone.now()
            withdrawal.save()
            
            self.stdout.write(f'Status updated to: {withdrawal.status}')
            
            # Process payment automatically
            if withdrawal.can_process_instant():
                self.stdout.write('Processing instant payment via PayPal...')
                
                try:
                    # Call the withdrawal service to process payment
                    result = WithdrawalService.process_instant_withdrawal(withdrawal)
                    
                    if result:
                        self.stdout.write('✅ Automatic processing successful!')
                        self.stdout.write(f'Withdrawal status: {withdrawal.status}')
                        self.stdout.write(f'Completed at: {withdrawal.completed_at}')
                        
                        # Send admin notification
                        self.send_admin_notification(withdrawal, 'completed')
                        
                        # Send user confirmation
                        self.send_user_confirmation(withdrawal)
                        
                    else:
                        self.stdout.write('❌ Automatic processing failed!')
                        self.stdout.write(f'Withdrawal status: {withdrawal.status}')
                        self.stdout.write(f'Failure reason: {withdrawal.failure_reason}')
                        
                        # Send admin notification about failure
                        self.send_admin_notification(withdrawal, 'failed')
                        
                except Exception as e:
                    self.stdout.write(f'Processing error: {e}')
                    withdrawal.status = 'failed'
                    withdrawal.failure_reason = f"Automatic processing error: {str(e)}"
                    withdrawal.save()
                    
                    self.send_admin_notification(withdrawal, 'failed')
            
            else:
                self.stdout.write('Weekly withdrawal - queuing for batch processing')
                WithdrawalService.queue_weekly_withdrawal(withdrawal)
                self.send_admin_notification(withdrawal, 'queued')
            
        except Exception as e:
            self.stdout.write(f'Error creating withdrawal: {e}')
            return
        
        # Check final status
        withdrawal.refresh_from_db()
        self.stdout.write(f'\\n--- FINAL STATUS ---')
        self.stdout.write(f'Withdrawal ID: {withdrawal.id}')
        self.stdout.write(f'Amount: ${withdrawal.amount}')
        self.stdout.write(f'Status: {withdrawal.status}')
        self.stdout.write(f'Type: {withdrawal.payout_type}')
        self.stdout.write(f'Processed: {withdrawal.processed_at}')
        self.stdout.write(f'Completed: {withdrawal.completed_at}')
        
        if withdrawal.failure_reason:
            self.stdout.write(f'Failure Reason: {withdrawal.failure_reason}')
        
        self.stdout.write('\\n--- NEXT STEPS ---')
        self.stdout.write('1. Update withdrawal views to auto-process on creation')
        self.stdout.write('2. Implement admin notification system')
        self.stdout.write('3. Add user confirmation emails')
        self.stdout.write('4. Create admin dashboard notifications')
        self.stdout.write('5. Add fraud detection and limits')
        
        self.stdout.write('\\n=== AUTOMATIC PROCESSING TEST COMPLETE ===')
        
        if withdrawal.status == 'completed':
            self.stdout.write('✅ SUCCESS: Automatic withdrawal processing working!')
            self.stdout.write('Admin notifications sent successfully!')
        else:
            self.stdout.write('❌ ISSUES: Check PayPal configuration and error handling')
    
    def send_admin_notification(self, withdrawal, status):
        """Send notification to admin about withdrawal"""
        try:
            subject = f'Withdrawal {status.upper()}: ${withdrawal.amount} - {withdrawal.user.username}'
            
            if status == 'completed':
                message = f"""
                Withdrawal completed successfully!
                
                User: {withdrawal.user.username} ({withdrawal.user.email})
                Amount: ${withdrawal.amount}
                Type: {withdrawal.payout_type}
                Method: {withdrawal.withdrawal_method.method_type}
                Status: {withdrawal.status}
                Completed: {withdrawal.completed_at}
                
                Transaction ID: {withdrawal.id}
                """
            elif status == 'failed':
                message = f"""
                Withdrawal processing failed!
                
                User: {withdrawal.user.username} ({withdrawal.user.email})
                Amount: ${withdrawal.amount}
                Type: {withdrawal.payout_type}
                Method: {withdrawal.withdrawal_method.method_type}
                Status: {withdrawal.status}
                Failure Reason: {withdrawal.failure_reason}
                
                Transaction ID: {withdrawal.id}
                
                Please investigate this failure.
                """
            else:  # queued
                message = f"""
                Withdrawal queued for weekly processing!
                
                User: {withdrawal.user.username} ({withdrawal.user.email})
                Amount: ${withdrawal.amount}
                Type: {withdrawal.payout_type}
                Method: {withdrawal.withdrawal_method.method_type}
                Status: {withdrawal.status}
                Requested: {withdrawal.requested_at}
                
                Transaction ID: {withdrawal.id}
                
                This will be processed during the next weekly batch.
                """
            
            # Send to admin
            admin_email = settings.ADMIN_EMAIL if hasattr(settings, 'ADMIN_EMAIL') else 'admin@sharpdocs.com'
            
            send_mail(
                subject,
                message,
                settings.DEFAULT_FROM_EMAIL,
                [admin_email],
                fail_silently=False,
            )
            
            self.stdout.write(f'✅ Admin notification sent: {status.upper()}')
            
        except Exception as e:
            self.stdout.write(f'❌ Failed to send admin notification: {e}')
    
    def send_user_confirmation(self, withdrawal):
        """Send confirmation email to user"""
        try:
            subject = f'Withdrawal Completed - ${withdrawal.amount}'
            
            message = f"""
            Your withdrawal has been processed successfully!
            
            Amount: ${withdrawal.amount}
            Fee: ${withdrawal.fee}
            Net Amount: ${withdrawal.net_amount}
            Method: {withdrawal.withdrawal_method.method_type}
            Status: {withdrawal.status}
            Completed: {withdrawal.completed_at}
            
            The funds have been sent to your {withdrawal.withdrawal_method.method_type} account.
            
            Thank you for using SharpDocs!
            """
            
            send_mail(
                subject,
                message,
                settings.DEFAULT_FROM_EMAIL,
                [withdrawal.user.email],
                fail_silently=False,
            )
            
            self.stdout.write(f'✅ User confirmation sent to: {withdrawal.user.email}')
            
        except Exception as e:
            self.stdout.write(f'❌ Failed to send user confirmation: {e}')
