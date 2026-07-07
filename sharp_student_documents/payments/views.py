# payments/views.py
import logging
import requests
import stripe
from decimal import Decimal
import json

from django.conf import settings
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.template.loader import render_to_string
from django.views.decorators.csrf import csrf_exempt
from django.core.mail import send_mail
from notifications.utils import send_payment_notification

from documents.models import Order
from payments.models import Payment
from sharp_student_documents.paypal import (
    paypal_access_token,
    paypal_api_base,
    verify_paypal_webhook_signature,
)

logger = logging.getLogger(__name__)
# ---------------------------
# Stripe Setup
# ---------------------------
stripe.api_key = settings.STRIPE_SECRET_KEY


# ---------------------------
# Email Receipt Helper
# ---------------------------
def _send_payment_receipt(order, request=None):
    """Send email receipt after successful payment."""
    if not order.buyer.email:
        return

    context = {
        "order": order,
        "buyer": order.buyer,
        "document": order.document,
        "site_name": getattr(settings, "SITE_NAME", "My Site"),
        "site_url": request.build_absolute_uri("/") if request else "http://localhost:8000",
    }

    subject = f"Receipt for your purchase: {order.document.title}"
    message = render_to_string("payments/receipt_email.txt", context)

    send_mail(
        subject,
        message,
        settings.DEFAULT_FROM_EMAIL,
        [order.buyer.email],
        fail_silently=True,  # Don't fail the payment if email fails
    )


def _finalize_paypal_order(order, paypal_order_id, *, request=None, verify_payment=True):
    """
    Finalize a PayPal payment in an idempotent way so both the return flow
    and webhook flow can safely process the same order.
    
    CRITICAL: Emails are ONLY sent after successful payment verification.
    
    Args:
        order: The order to finalize
        paypal_order_id: PayPal order ID
        request: HTTP request (optional)
        verify_payment: Whether to verify payment status before finalizing (default: True)
    """
    payment_verified = False
    
    # ALWAYS verify payment status before proceeding - no exceptions
    if verify_payment:
        try:
            token = _paypal_get_token()
            base = _get_paypal_base()
            headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
            resp = requests.get(f"{base}/v2/checkout/orders/{paypal_order_id}", headers=headers, timeout=20)
            resp.raise_for_status()
            order_data = resp.json()
            
            # Check if the order is actually completed and paid
            if order_data.get("status") != "COMPLETED":
                logger.error(f"PAYMENT NOT COMPLETED: PayPal order {paypal_order_id} status: {order_data.get('status')}")
                return False
                
            # Verify capture was successful
            purchase_units = order_data.get("purchase_units", [])
            if not purchase_units:
                logger.error(f"PAYMENT VERIFICATION FAILED: PayPal order {paypal_order_id} has no purchase units")
                return False
                
            payments = purchase_units[0].get("payments", {})
            captures = payments.get("captures", [])
            if not captures:
                logger.error(f"PAYMENT VERIFICATION FAILED: PayPal order {paypal_order_id} has no captures")
                return False
                
            capture_status = captures[0].get("status")
            if capture_status != "COMPLETED":
                logger.error(f"PAYMENT NOT CAPTURED: PayPal order {paypal_order_id} capture status: {capture_status}")
                return False
            
            # Verify payment amount matches expected amount
            capture_amount = captures[0].get("amount", {}).get("value")
            if capture_amount:
                try:
                    actual_amount = Decimal(str(capture_amount))
                    expected_amount = Decimal(str(order.document.price))
                    if actual_amount != expected_amount:
                        logger.error(f"PAYMENT AMOUNT MISMATCH: PayPal order {paypal_order_id} captured ${actual_amount}, expected ${expected_amount}")
                        return False
                except Exception as e:
                    logger.error(f"PAYMENT AMOUNT VERIFICATION ERROR: PayPal order {paypal_order_id}: {e}")
                    return False
            
            # All verifications passed
            payment_verified = True
            logger.info(f"PAYMENT VERIFIED: PayPal order {paypal_order_id} successfully completed and captured")
                
        except Exception as e:
            logger.error(f"PAYMENT VERIFICATION CRITICAL ERROR: PayPal order {paypal_order_id}: {e}")
            return False
    else:
        # Only skip verification if explicitly disabled (for return flow where capture was already verified)
        payment_verified = True
    
    # ONLY proceed with order finalization if payment is verified
    if not payment_verified:
        logger.error(f"PAYMENT FINALIZATION BLOCKED: PayPal order {paypal_order_id} - payment verification failed")
        return False
    
    # Update order status
    order.status = "paid"
    order.paypal_payment_id = paypal_order_id
    order.amount_paid = order.document.price
    order.save(update_fields=["status", "paypal_payment_id", "amount_paid"])

    # Create payment record
    payment = Payment.objects.update_or_create(
        order=order,
        defaults={
            "payment_method": "paypal",
            "transaction_id": paypal_order_id,
            "amount": order.amount_paid,
            "status": "success",
        },
    )[0]

    # Create sale record
    from sales.utils import create_sale_record
    create_sale_record(order)

    # ONLY SEND EMAILS AFTER ALL VERIFICATIONS PASSED
    logger.info(f"SENDING EMAILS: PayPal order {paypal_order_id} - payment verified, sending notifications")
    
    try:
        send_payment_notification(payment)
        logger.info(f"PAYMENT NOTIFICATION SENT: PayPal order {paypal_order_id}")
    except Exception:
        logger.exception("Failed to send payment notification (paypal)")

    try:
        _send_payment_receipt(order, request)
        logger.info(f"PAYMENT RECEIPT SENT: PayPal order {paypal_order_id}")
    except Exception:
        logger.exception("Failed to send payment receipt (paypal)")
    
    logger.info(f"PAYMENT FINALIZATION COMPLETED: PayPal order {paypal_order_id}")
    return True


# ---------------------------
# Checkout Page
# ---------------------------
@login_required
def checkout(request, order_id):
    order = get_object_or_404(Order, id=order_id, buyer=request.user)
    if order.status == "paid":
        messages.info(request, "This order is already paid.")
        return redirect("payments:success", order_id=order.id)
    return render(request, "payments/checkout.html", {"order": order})


# ---------------------------
# Stripe Checkout
# ---------------------------
@login_required
def stripe_checkout(request, order_id):
    order = get_object_or_404(Order, id=order_id, buyer=request.user)

    if order.status == "paid":
        messages.info(request, "Order already paid.")
        return redirect("payments:success", order_id=order.id)
    
    # Direct card payments coming soon
    messages.info(request, 
        'Direct card payments are coming soon! For now, please use PayPal which accepts all major cards (Visa, Mastercard, Amex, Discover, Apple Pay, Google Pay, and more). No PayPal account required!'
    )
    return redirect("payments:checkout", order_id=order.id)


@login_required
def stripe_success(request, order_id):
    """Temporary success page (webhook will finalize the payment)."""
    session_id = request.GET.get("session_id")
    order = get_object_or_404(Order, id=order_id, buyer=request.user)

    if not session_id:
        messages.error(request, "Stripe session missing.")
        return redirect("payments:failed", order_id=order.id)

    try:
        session = stripe.checkout.Session.retrieve(session_id)
        if session.payment_status == "paid":
            messages.success(request, "Payment successful. Thank you!")
            return redirect("payments:success", order_id=order.id)
    except Exception as e:
        messages.error(request, f"Stripe error: {e}")
    return redirect("payments:failed", order_id=order.id)


# ---------------------------
# Stripe Webhook
# ---------------------------
@csrf_exempt
def stripe_webhook(request):
    payload = request.body
    sig_header = request.META.get("HTTP_STRIPE_SIGNATURE")
    endpoint_secret = settings.STRIPE_WEBHOOK_SECRET

    try:
        event = stripe.Webhook.construct_event(payload, sig_header, endpoint_secret)
    except (ValueError, stripe.error.SignatureVerificationError):
        return HttpResponse(status=400)

    if event["type"] == "checkout.session.completed":
        session = event["data"]["object"]
        _handle_stripe_checkout(session)

    return HttpResponse(status=200)


def _handle_stripe_checkout(session):
    """Update order + create Payment + Sale when Stripe confirms payment via webhook."""
    order_id = session.get("metadata", {}).get("order_id")
    if not order_id:
        return

    try:
        order = Order.objects.get(id=order_id)
        if order.status != "paid":
            order.status = "paid"
            order.stripe_payment_intent = session.get("payment_intent")
            amount_total = session.get("amount_total", None)
            if amount_total is None:
                # Fallback: keep the order price if Stripe doesn't provide amount_total
                order.amount_paid = order.document.price
            else:
                order.amount_paid = amount_total / 100
            order.save()

            # Create payment record
            Payment.objects.update_or_create(
                order=order,
                defaults={
                    "payment_method": "stripe",
                    "transaction_id": order.stripe_payment_intent,
                    "amount": order.amount_paid,
                    "status": "success",
                },
            )

            # Create sale record and update seller wallet
            from sales.utils import create_sale_record
            create_sale_record(order)

            # Send payment confirmation notification to admin
            try:
                send_payment_notification(Payment.objects.get(order=order))
            except Exception:
                logger.exception("Failed to send payment notification (stripe)")

            _send_payment_receipt(order)
    except Order.DoesNotExist:
        pass


# ---------------------------
# PayPal Checkout
# ---------------------------
def _get_paypal_base():
    return paypal_api_base()


def _paypal_get_token():
    return paypal_access_token()


@login_required
def paypal_checkout(request, order_id):
    order = get_object_or_404(Order, id=order_id, buyer=request.user)
    if order.status == "paid":
        messages.info(request, "Order already paid.")
        return redirect("payments:success", order_id=order.id)

    try:
        token = _paypal_get_token()
        base = _get_paypal_base()
        payload = {
            "intent": "CAPTURE",
            "purchase_units": [{
                "amount": {"currency_code": "USD", "value": str(order.document.price)},
                "description": order.document.title,
            }],
            "application_context": {
                "return_url": request.build_absolute_uri(reverse("payments:paypal_return", args=[order.id])),
                "cancel_url": request.build_absolute_uri(reverse("payments:failed", args=[order.id])),
            },
        }
        headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
        resp = requests.post(f"{base}/v2/checkout/orders", json=payload, headers=headers, timeout=20)
        resp.raise_for_status()
        data = resp.json()

        paypal_order_id = data.get("id")
        if paypal_order_id:
            order.paypal_payment_id = paypal_order_id
            order.save()

        for link in data.get("links", []):
            if link.get("rel") == "approve":
                return redirect(link.get("href"))

        messages.error(request, "Could not start PayPal flow.")
    except Exception as e:
        messages.error(request, f"PayPal error: {e}")

    return redirect("payments:failed", order_id=order.id)


@login_required
def paypal_return(request, order_id):
    order = get_object_or_404(Order, id=order_id, buyer=request.user)
    paypal_order_id = request.GET.get("token")

    if not paypal_order_id:
        messages.error(request, "PayPal token missing.")
        return redirect("payments:failed", order_id=order.id)

    try:
        token = _paypal_get_token()
        base = _get_paypal_base()
        headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
        resp = requests.post(f"{base}/v2/checkout/orders/{paypal_order_id}/capture", headers=headers, timeout=20)
        resp.raise_for_status()
        data = resp.json()

        if data.get("status") == "COMPLETED":
            try:
                amount_value = (
                    data.get("purchase_units", [{}])[0]
                    .get("payments", {})
                    .get("captures", [{}])[0]
                    .get("amount", {})
                    .get("value")
                )
                if amount_value and Decimal(str(amount_value)) != Decimal(str(order.document.price)):
                    messages.error(request, "PayPal amount mismatch.")
                    return redirect("payments:failed", order_id=order.id)
            except Exception:
                logger.exception("Failed to validate PayPal capture amount")

            if _finalize_paypal_order(order, paypal_order_id, request=request, verify_payment=True):
                messages.success(request, "PayPal payment captured successfully.")
                return redirect("payments:success", order_id=order.id)
            else:
                messages.error(request, "PayPal payment verification failed.")
                return redirect("payments:failed", order_id=order.id)
    except Exception as e:
        messages.error(request, f"PayPal capture error: {e}")

    return redirect("payments:failed", order_id=order.id)


# ---------------------------
# Payment Status Pages
# ---------------------------



@login_required
def payment_success(request, order_id):
    order = get_object_or_404(Order, id=order_id, buyer=request.user)
    document = order.document

    if order.status != "paid":
        messages.error(request, "Your payment has not been confirmed yet.")
        return render(request, "payments/failed.html", {"order": order})

    if not document.file:
        messages.error(request, "No file found for this document.")
        return render(request, "payments/failed.html", {"order": order})

    # Use local Django download URL
    download_url = reverse("documents:download_document", args=[order.id])

    messages.success(request, "Payment successful! Your download is ready.")
    return render(
        request,
        "payments/success.html",
        {"order": order, "download_url": download_url},
    )

@login_required
def payment_failed(request, order_id):
    order = get_object_or_404(Order, id=order_id, buyer=request.user)
    return render(request, "payments/failed.html", {"order": order})


# ---------------------------
# PayPal Webhook
# ---------------------------
@csrf_exempt
def paypal_webhook(request):
    try:
        data = json.loads(request.body.decode("utf-8"))
    except Exception:
        return HttpResponse(status=400)

    if not verify_paypal_webhook_signature(request=request, webhook_event=data):
        return HttpResponse(status=400)

    event_type = data.get("event_type")
    resource = data.get("resource", {}) or {}

    if event_type not in {"CHECKOUT.ORDER.COMPLETED", "PAYMENT.CAPTURE.COMPLETED"}:
        return HttpResponse(status=200)

    if resource.get("status") != "COMPLETED":
        return HttpResponse(status=200)

    paypal_order_id = (
        resource.get("supplementary_data", {}).get("related_ids", {}).get("order_id")
        or resource.get("id")
    )
    if not paypal_order_id:
        return HttpResponse(status=400)

    try:
        order = Order.objects.filter(paypal_payment_id=paypal_order_id).first()
        if order and order.status != "paid":
            _finalize_paypal_order(order, paypal_order_id, verify_payment=True)
    except Exception:
        logger.exception("PayPal webhook handling error")

    return HttpResponse(status=200)
