from decimal import Decimal

from django.test import TestCase
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile

from documents.models import Document, Order
from sales.models import Wallet
from sales.utils import create_sale_record


User = get_user_model()


class CommissionSplitTests(TestCase):
    def setUp(self):
        self.seller = User.objects.create_user(
            username="seller",
            email="seller@example.com",
            password="pass12345",
            is_seller=True,
        )
        self.buyer = User.objects.create_user(
            username="buyer",
            email="buyer@example.com",
            password="pass12345",
        )

        self.document = Document.objects.create(
            seller=self.seller,
            title="Test Doc",
            description="Test",
            file=SimpleUploadedFile("test.pdf", b"%PDF-1.4\n%", content_type="application/pdf"),
            price=Decimal("100.00"),
        )

        self.order = Order.objects.create(
            buyer=self.buyer,
            document=self.document,
            status="paid",
            payment_method="paypal",
            amount_paid=Decimal("100.00"),
        )

    def test_sale_uses_60_40_split_and_credits_wallet_once(self):
        sale = create_sale_record(self.order)
        sale.refresh_from_db()

        self.assertEqual(sale.gross_amount, Decimal("100.00"))
        self.assertEqual(sale.commission_rate, Decimal("0.4000"))
        self.assertEqual(sale.commission_amount, Decimal("40.00"))
        self.assertEqual(sale.net_amount, Decimal("60.00"))

        wallet = Wallet.objects.get(user=self.seller)
        # Earnings are held for 14 days before becoming withdrawable.
        self.assertEqual(wallet.balance, Decimal("0.00"))
        self.assertEqual(wallet.pending_balance, Decimal("60.00"))
        self.assertEqual(wallet.total_earned, Decimal("0.00"))
        self.assertEqual(wallet.total_commission_paid, Decimal("40.00"))

        # Idempotent: calling again shouldn't create a second sale or re-credit the wallet.
        _sale_again = create_sale_record(self.order)
        wallet.refresh_from_db()
        self.assertEqual(wallet.balance, Decimal("0.00"))
        self.assertEqual(wallet.pending_balance, Decimal("60.00"))


class RefundDebtOffsetTests(TestCase):
    def setUp(self):
        self.seller = User.objects.create_user(
            username="seller2",
            email="seller2@example.com",
            password="pass12345",
            is_seller=True,
        )
        self.wallet = Wallet.objects.create(
            user=self.seller,
            balance=Decimal("0.00"),
            pending_balance=Decimal("60.00"),
            reserved_balance=Decimal("0.00"),
            debt_balance=Decimal("50.00"),
            total_earned=Decimal("0.00"),
            total_commission_paid=Decimal("0.00"),
            total_withdrawn=Decimal("0.00"),
        )

    def test_release_pending_earnings_repays_debt_first(self):
        # Release $60 of held earnings; $50 repays debt, $10 becomes available.
        self.wallet.release_pending_earnings(Decimal("60.00"), commission_amount=Decimal("0.00"))
        self.wallet.refresh_from_db()
        self.assertEqual(self.wallet.pending_balance, Decimal("0.00"))
        self.assertEqual(self.wallet.debt_balance, Decimal("0.00"))
        self.assertEqual(self.wallet.balance, Decimal("10.00"))
