# payments/services.py
import stripe
import paypalrestsdk
from django.conf import settings

# Stripe setup
stripe.api_key = settings.STRIPE_SECRET_KEY

def create_stripe_session(order):
    session = stripe.checkout.Session.create(
        payment_method_types=["card"],
        line_items=[{
            "price_data": {
                "currency": "usd",
                "product_data": {"name": order.document.title},
                "unit_amount": int(order.document.price * 100),
            },
            "quantity": 1,
        }],
        mode="payment",
        success_url=f"{settings.SITE_URL}/payments/success/{order.id}/",
        cancel_url=f"{settings.SITE_URL}/payments/cancel/{order.id}/",
    )
    return session

# PayPal setup
paypalrestsdk.configure({
    "mode": settings.PAYPAL_MODE,
    "client_id": settings.PAYPAL_CLIENT_ID,
    "client_secret": settings.PAYPAL_CLIENT_SECRET,
})

def create_paypal_payment(order):
    payment = paypalrestsdk.Payment({
        "intent": "sale",
        "payer": {"payment_method": "paypal"},
        "redirect_urls": {
            "return_url": f"{settings.SITE_URL}/payments/paypal-success/{order.id}/",
            "cancel_url": f"{settings.SITE_URL}/payments/paypal-cancel/{order.id}/",
        },
        "transactions": [{
            "item_list": {
                "items": [{
                    "name": order.document.title,
                    "sku": str(order.document.id),
                    "price": str(order.document.price),
                    "currency": "USD",
                    "quantity": 1,
                }]
            },
            "amount": {
                "total": str(order.document.price),
                "currency": "USD"
            },
            "description": f"Purchase of {order.document.title}"
        }]
    })
    if payment.create():
        return payment
    return None
