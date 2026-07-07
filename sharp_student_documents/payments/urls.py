# payments/urls.py
from django.urls import path
from . import views

app_name = "payments"

urlpatterns = [
    path("checkout/<int:order_id>/", views.checkout, name="checkout"),
    path("stripe/<int:order_id>/", views.stripe_checkout, name="stripe_checkout"),
    path("stripe/success/<int:order_id>/", views.stripe_success, name="stripe_success"),
    path("paypal/<int:order_id>/", views.paypal_checkout, name="paypal_checkout"),
    path("paypal/return/<int:order_id>/", views.paypal_return, name="paypal_return"),
    path("success/<int:order_id>/", views.payment_success, name="success"),
    path("failed/<int:order_id>/", views.payment_failed, name="failed"),
    path("stripe/webhook/", views.stripe_webhook, name="stripe_webhook"),
    path("paypal/webhook/", views.paypal_webhook, name="paypal_webhook"),
     
]




