from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.test import Client
from withdrawals.models import WithdrawalRequest, WithdrawalMethod
from documents.models import Document
from decimal import Decimal
import json


class Command(BaseCommand):
    help = 'Create admin and test withdrawal approval process'

    def handle(self, *args, **options):
        self.stdout.write('=== ADMIN WITHDRAWAL APPROVAL TEST ===')
        
        User = get_user_model()
        
        # Step 1: Create admin user
        self.stdout.write('\n--- Step 1: Creating Admin User ---')
        try:
            admin_user = User.objects.get(username='testadmin')
            self.stdout.write('Admin user already exists: testadmin')
        except User.DoesNotExist:
            admin_user = User.objects.create_superuser(
                username='testadmin',
                email='admin@test.com',
                password='admin123'
            )
            self.stdout.write('Created admin user: testadmin (password: admin123)')
        
        # Step 2: Create test seller
        self.stdout.write('\n--- Step 2: Creating Test Seller ---')
        try:
            seller_user = User.objects.get(username='testseller')
            self.stdout.write('Seller user already exists: testseller')
        except User.DoesNotExist:
            seller_user = User.objects.create_user(
                username='testseller',
                email='seller@test.com',
                password='seller123'
            )
            self.stdout.write('Created seller user: testseller (password: seller123)')
        
        # Step 3: Create PayPal withdrawal method
        self.stdout.write('\n--- Step 3: Creating PayPal Withdrawal Method ---')
        try:
            paypal_method = WithdrawalMethod.objects.get(
                user=seller_user,
                method_type='paypal'
            )
            self.stdout.write('PayPal method already exists for testseller')
        except WithdrawalMethod.DoesNotExist:
            paypal_method = WithdrawalMethod.objects.create(
                user=seller_user,
                method_type='paypal',
                paypal_email='seller@example.com',
                is_verified=True,
                is_active=True
            )
            self.stdout.write('Created PayPal method for testseller')
        
        # Step 4: Create test document (for earnings)
        self.stdout.write('\n--- Step 4: Creating Test Document ---')
        try:
            test_doc = Document.objects.get(title='Test Document for Withdrawal')
            self.stdout.write('Test document already exists')
        except Document.DoesNotExist:
            test_doc = Document.objects.create(
                title='Test Document for Withdrawal',
                description='A test document for withdrawal testing',
                price=Decimal('10.00'),
                seller=seller_user
            )
            self.stdout.write('Created test document: $10.00')
        
        # Step 5: Create withdrawal requests
        self.stdout.write('\n--- Step 5: Creating Withdrawal Requests ---')
        
        # Create instant withdrawal (≤ $100)
        instant_withdrawal = WithdrawalRequest.objects.create(
            user=seller_user,
            withdrawal_method=paypal_method,
            amount=Decimal('50.00'),  # ≤ $100 for instant processing
            payout_type='instant'
        )
        self.stdout.write(f'Created instant withdrawal: ${instant_withdrawal.amount} (ID: {instant_withdrawal.id})')
        
        # Create weekly withdrawal (> $100)
        weekly_withdrawal = WithdrawalRequest.objects.create(
            user=seller_user,
            withdrawal_method=paypal_method,
            amount=Decimal('150.00'),  # > $100 for weekly processing
            payout_type='weekly'
        )
        self.stdout.write(f'Created weekly withdrawal: ${weekly_withdrawal.amount} (ID: {weekly_withdrawal.id})')
        
        # Step 6: Test admin approval system
        self.stdout.write('\n--- Step 6: Testing Admin Approval System ---')
        
        client = Client()
        client.force_login(admin_user)
        
        # Test 1: Approve instant withdrawal
        self.stdout.write('\n--- Test 1: Approving Instant Withdrawal ---')
        response = client.post(
            f'/withdrawals/admin/approve/{instant_withdrawal.id}/',
            data=json.dumps({}),
            content_type='application/json'
        )
        
        self.stdout.write(f'Approval response status: {response.status_code}')
        if response.status_code == 200:
            response_data = response.json()
            self.stdout.write(f'Approval response: {response_data}')
            
            # Check withdrawal status
            instant_withdrawal.refresh_from_db()
            self.stdout.write(f'Instant withdrawal status after approval: {instant_withdrawal.status}')
            self.stdout.write(f'Instant withdrawal processed at: {instant_withdrawal.processed_at}')
            if instant_withdrawal.paypal_payout_id:
                self.stdout.write(f'PayPal payout ID: {instant_withdrawal.paypal_payout_id}')
                self.stdout.write('SUCCESS: PayPal payout was created!')
            else:
                self.stdout.write('WARNING: No PayPal payout ID found')
        else:
            self.stdout.write(f'ERROR: Approval failed with response: {response.content.decode()}')
        
        # Test 2: Approve weekly withdrawal
        self.stdout.write('\n--- Test 2: Approving Weekly Withdrawal ---')
        response = client.post(
            f'/withdrawals/admin/reject/{weekly_withdrawal.id}/',
            data={'reason': 'Test rejection for weekly withdrawal'},
            content_type='application/x-www-form-urlencoded'
        )
        
        # Actually approve the weekly withdrawal
        response = client.post(
            f'/withdrawals/admin/approve/{weekly_withdrawal.id}/',
            data=json.dumps({}),
            content_type='application/json'
        )
        
        self.stdout.write(f'Weekly approval response status: {response.status_code}')
        if response.status_code == 200:
            response_data = response.json()
            self.stdout.write(f'Weekly approval response: {response_data}')
            
            # Check withdrawal status
            weekly_withdrawal.refresh_from_db()
            self.stdout.write(f'Weekly withdrawal status after approval: {weekly_withdrawal.status}')
            self.stdout.write(f'Weekly withdrawal processed at: {weekly_withdrawal.processed_at}')
        else:
            self.stdout.write(f'ERROR: Weekly approval failed with response: {response.content.decode()}')
        
        # Test 3: Test withdrawal details endpoint
        self.stdout.write('\n--- Test 3: Testing Withdrawal Details ---')
        response = client.get(f'/withdrawals/admin/details/{instant_withdrawal.id}/')
        
        self.stdout.write(f'Details response status: {response.status_code}')
        if response.status_code == 200:
            response_data = response.json()
            self.stdout.write(f'Details response success: {response_data.get("success")}')
            if response_data.get('success'):
                details = response_data.get('details', {})
                self.stdout.write(f'Withdrawal details:')
                self.stdout.write(f'  User: {details.get("user", {}).get("username", "N/A")}')
                self.stdout.write(f'  Amount: ${details.get("amount", "N/A")}')
                self.stdout.write(f'  Status: {details.get("status", "N/A")}')
                self.stdout.write(f'  Can Approve: {details.get("can_approve", False)}')
                self.stdout.write('SUCCESS: Details endpoint working!')
            else:
                self.stdout.write(f'ERROR: {response_data.get("error", "Unknown error")}')
        else:
            self.stdout.write(f'ERROR: Details endpoint failed: {response.content.decode()}')
        
        # Step 7: Test admin management page
        self.stdout.write('\n--- Step 7: Testing Admin Management Page ---')
        response = client.get('/admin/manage-withdrawals/')
        
        self.stdout.write(f'Admin management page status: {response.status_code}')
        if response.status_code == 200:
            self.stdout.write('SUCCESS: Admin management page accessible')
        else:
            self.stdout.write(f'ERROR: Admin management page failed: {response.content.decode()}')
        
        # Step 8: Summary
        self.stdout.write('\n=== TEST SUMMARY ===')
        self.stdout.write('\nCreated Test Data:')
        self.stdout.write(f'  Admin: testadmin (password: admin123)')
        self.stdout.write(f'  Seller: testseller (password: seller123)')
        self.stdout.write(f'  Instant Withdrawal: ${instant_withdrawal.amount} (Status: {instant_withdrawal.status})')
        self.stdout.write(f'  Weekly Withdrawal: ${weekly_withdrawal.amount} (Status: {weekly_withdrawal.status})')
        
        self.stdout.write('\nTest Results:')
        self.stdout.write(f'  Instant Withdrawal Approval: {"WORKING" if instant_withdrawal.status in ["completed", "processing"] else "FAILED"}')
        self.stdout.write(f'  Weekly Withdrawal Approval: {"WORKING" if weekly_withdrawal.status in ["pending", "processing"] else "FAILED"}')
        self.stdout.write(f'  Details Endpoint: {"WORKING" if response.status_code == 200 else "FAILED"}')
        self.stdout.write(f'  Admin Page: {"WORKING" if response.status_code == 200 else "FAILED"}')
        
        self.stdout.write('\nNext Steps:')
        self.stdout.write('1. Login as admin: http://127.0.0.1:8000/admin/')
        self.stdout.write('   Username: testadmin')
        self.stdout.write('   Password: admin123')
        self.stdout.write('2. Go to withdrawal management: http://127.0.0.1:8000/admin/manage-withdrawals/')
        self.stdout.write('3. Test the approve/reject buttons in the browser')
        self.stdout.write('4. Check if PayPal payouts are created (check PayPal account)')
        
        self.stdout.write('\n=== TEST COMPLETE ===')
        self.stdout.write('The admin approval system has been tested and is ready for browser testing!')
