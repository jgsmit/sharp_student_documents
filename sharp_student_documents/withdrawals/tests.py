from django.test import TestCase
from django.contrib.auth import get_user_model
from decimal import Decimal
from withdrawals.models import WithdrawalMethod, WithdrawalRequest, TwoFactorAuth
from withdrawals.services import WithdrawalService
from unittest.mock import patch
from sales.models import Wallet
from django.test import override_settings

User = get_user_model()

class WithdrawalServiceTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        
        # Create withdrawal method
        self.withdrawal_method = WithdrawalMethod.objects.create(
            user=self.user,
            method_type='stripe',
            stripe_account_id='acct_test123',
            is_verified=True
        )
        
        # Create 2FA
        self.two_fa = TwoFactorAuth.objects.create(
            user=self.user,
            is_enabled=True
        )

    def test_can_withdraw_sufficient_balance(self):
        """Test withdrawal with sufficient balance"""
        # Mock user balance
        with patch('withdrawals.services.WithdrawalService.get_user_balance') as mock_balance:
            mock_balance.return_value = Decimal('1000.00')
            
            can_withdraw, message = WithdrawalService.can_withdraw(self.user, Decimal('500.00'))
            self.assertTrue(can_withdraw)
            self.assertEqual(message, "Withdrawal allowed")

    def test_cannot_withdraw_insufficient_balance(self):
        """Test withdrawal with insufficient balance"""
        with patch('withdrawals.services.WithdrawalService.get_user_balance') as mock_balance:
            mock_balance.return_value = Decimal('100.00')
            
            can_withdraw, message = WithdrawalService.can_withdraw(self.user, Decimal('500.00'))
            self.assertFalse(can_withdraw)
            self.assertEqual(message, "Insufficient balance")

    def test_minimum_withdrawal_amount(self):
        """Test minimum withdrawal amount"""
        with patch('withdrawals.services.WithdrawalService.get_user_balance') as mock_balance:
            mock_balance.return_value = Decimal('1000.00')
            
            can_withdraw, message = WithdrawalService.can_withdraw(self.user, Decimal('5.00'))
            self.assertFalse(can_withdraw)
            self.assertEqual(message, "Minimum withdrawal amount is $10.00")

    @override_settings(WITHDRAWALS_REQUIRE_2FA_FOR_WITHDRAWALS=True)
    def test_2fa_required_when_enabled(self):
        """When the feature flag is enabled and the user has 2FA enabled, withdrawals require 2FA."""
        withdrawal_request = WithdrawalRequest.objects.create(
            user=self.user,
            withdrawal_method=self.withdrawal_method,
            amount=Decimal('50.00')
        )
        self.assertTrue(withdrawal_request.requires_two_factor_auth())

    def test_2fa_not_required_when_flag_disabled(self):
        """By default the feature flag is disabled, so withdrawals don't require 2FA."""
        withdrawal_request = WithdrawalRequest.objects.create(
            user=self.user,
            withdrawal_method=self.withdrawal_method,
            amount=Decimal('50.00')
        )
        self.assertFalse(withdrawal_request.requires_two_factor_auth())

    def test_instant_withdrawal_eligibility(self):
        """Instant withdrawals are disabled."""
        withdrawal_request = WithdrawalRequest.objects.create(
            user=self.user,
            withdrawal_method=self.withdrawal_method,
            amount=Decimal('50.00'),
            payout_type='instant'
        )
        self.assertFalse(withdrawal_request.can_process_instant())

    def test_failed_withdrawal_releases_reserved_funds_for_retry(self):
        """
        If a withdrawal is marked failed/cancelled but still has reserved funds (wallet_debited=True),
        the seller should get their available balance back so they can request another withdrawal.
        """
        wallet = Wallet.objects.create(
            user=self.user,
            balance=Decimal("0.00"),
            reserved_balance=Decimal("50.00"),
        )
        withdrawal = WithdrawalRequest.objects.create(
            user=self.user,
            amount=Decimal("50.00"),
            fee=Decimal("0.00"),
            net_amount=Decimal("50.00"),
            status="failed",
            wallet_debited=True,
            failure_reason="Test failure",
        )

        balance = WithdrawalService.get_user_balance(self.user)

        wallet.refresh_from_db()
        withdrawal.refresh_from_db()

        self.assertEqual(wallet.reserved_balance, Decimal("0.00"))
        self.assertEqual(wallet.balance, Decimal("50.00"))
        self.assertFalse(withdrawal.wallet_debited)
        self.assertEqual(balance, Decimal("50.00"))

    def test_completed_withdrawal_clears_wallet_debited_even_if_reserved_already_zero(self):
        """
        If a withdrawal is completed but `wallet_debited=True` while the wallet has no reserved funds,
        `get_user_balance()` should still clear the flag (and must not double-increment totals).
        """
        wallet = Wallet.objects.create(
            user=self.user,
            balance=Decimal("0.00"),
            reserved_balance=Decimal("0.00"),
            total_withdrawn=Decimal("0.00"),
        )
        withdrawal = WithdrawalRequest.objects.create(
            user=self.user,
            amount=Decimal("50.00"),
            fee=Decimal("0.00"),
            net_amount=Decimal("50.00"),
            status="completed",
            wallet_debited=True,
        )

        balance = WithdrawalService.get_user_balance(self.user)

        wallet.refresh_from_db()
        withdrawal.refresh_from_db()

        self.assertEqual(balance, Decimal("0.00"))
        self.assertFalse(withdrawal.wallet_debited)
        self.assertEqual(wallet.total_withdrawn, Decimal("0.00"))

class TwoFactorAuthTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        
        self.two_fa = TwoFactorAuth.objects.create(user=self.user)

    def test_generate_secret(self):
        """Test TOTP secret generation"""
        secret = self.two_fa.generate_secret()
        self.assertIsNotNone(secret)
        self.assertEqual(len(secret), 32)  # Base32 encoded secret

    def test_generate_backup_codes(self):
        """Test backup code generation"""
        codes = self.two_fa.generate_backup_codes()
        self.assertEqual(len(codes), 10)
        for code in codes:
            self.assertEqual(len(code), 8)
            self.assertTrue(code.isdigit())

    def test_verify_backup_code(self):
        """Test backup code verification"""
        codes = self.two_fa.generate_backup_codes()
        test_code = codes[0]
        
        # Verify unused code
        self.assertTrue(self.two_fa.verify_backup_code(test_code))
        
        # Try to use same code again
        self.assertFalse(self.two_fa.verify_backup_code(test_code))
        
        # Try invalid code
        self.assertFalse(self.two_fa.verify_backup_code('123456'))

class WithdrawalMethodTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )

    def test_stripe_method_creation(self):
        """Test Stripe withdrawal method creation"""
        method = WithdrawalMethod.objects.create(
            user=self.user,
            method_type='stripe',
            stripe_account_id='acct_test123'
        )
        
        self.assertEqual(method.method_type, 'stripe')
        self.assertEqual(method.stripe_account_id, 'acct_test123')
        self.assertFalse(method.is_verified)
        self.assertTrue(method.is_active)

    def test_paypal_method_creation(self):
        """Test PayPal withdrawal method creation"""
        method = WithdrawalMethod.objects.create(
            user=self.user,
            method_type='paypal',
            paypal_email='test@example.com'
        )
        
        self.assertEqual(method.method_type, 'paypal')
        self.assertEqual(method.paypal_email, 'test@example.com')
        self.assertFalse(method.is_verified)

    def test_method_string_representation(self):
        """Test method string representation"""
        method = WithdrawalMethod.objects.create(
            user=self.user,
            method_type='stripe',
            stripe_account_id='acct_test123'
        )
        
        expected = f"{self.user.username} - Stripe Connect"
        self.assertEqual(str(method), expected)
