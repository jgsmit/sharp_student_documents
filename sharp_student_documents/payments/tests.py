import json
from decimal import Decimal
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import reverse

from documents.models import Document, Order
from payments.models import Payment
from sales.models import Sale


User = get_user_model()


class PayPalPaymentFlowTests(TestCase):
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
            title="Physics Notes",
            description="Useful revision notes",
            file=SimpleUploadedFile("notes.pdf", b"%PDF-1.4\n%", content_type="application/pdf"),
            price=Decimal("25.00"),
        )

    def test_success_page_does_not_mark_unpaid_order_as_paid(self):
        order = Order.objects.create(
            buyer=self.buyer,
            document=self.document,
            status="pending",
            payment_method="paypal",
        )
        self.client.force_login(self.buyer)

        response = self.client.get(reverse("payments:success", args=[order.id]))

        order.refresh_from_db()
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "payments/failed.html")
        self.assertEqual(order.status, "pending")

    @patch("payments.views._send_payment_receipt")
    @patch("payments.views.send_payment_notification")
    @patch("payments.views.verify_paypal_webhook_signature", return_value=True)
    def test_paypal_webhook_marks_order_paid_and_creates_payment(
        self,
        _verify_signature,
        _notify,
        _send_receipt,
    ):
        order = Order.objects.create(
            buyer=self.buyer,
            document=self.document,
            status="pending",
            payment_method="paypal",
            paypal_payment_id="PAYPAL-ORDER-123",
        )

        payload = {
            "event_type": "CHECKOUT.ORDER.COMPLETED",
            "resource": {
                "id": "PAYPAL-ORDER-123",
                "status": "COMPLETED",
            },
        }

        response = self.client.post(
            reverse("payments:paypal_webhook"),
            data=json.dumps(payload),
            content_type="application/json",
            **{
                "HTTP_PAYPAL_AUTH_ALGO": "SHA256withRSA",
                "HTTP_PAYPAL_CERT_URL": "https://api-m.paypal.com/certs/cert.pem",
                "HTTP_PAYPAL_TRANSMISSION_ID": "transmission-id",
                "HTTP_PAYPAL_TRANSMISSION_SIG": "signature",
                "HTTP_PAYPAL_TRANSMISSION_TIME": "2026-04-10T10:00:00Z",
            },
        )

        order.refresh_from_db()
        payment = Payment.objects.get(order=order)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(order.status, "paid")
        self.assertEqual(order.amount_paid, Decimal("25.00"))
        self.assertEqual(payment.status, "success")
        self.assertEqual(payment.transaction_id, "PAYPAL-ORDER-123")
        self.assertTrue(Sale.objects.filter(order=order).exists())
