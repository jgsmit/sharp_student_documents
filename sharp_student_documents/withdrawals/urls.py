from django.urls import path
from . import views
from . import admin_views

app_name = 'withdrawals'

urlpatterns = [
    # Main dashboard
    path('dashboard/', views.withdrawal_dashboard, name='dashboard'),
    
    # Withdrawal methods
    path('setup/', views.setup_withdrawal_method, name='setup_method'),
    path('setup/stripe/', views.setup_stripe_connect, name='setup_stripe'),
    path('setup/stripe/return/', views.stripe_return, name='stripe_return'),
    path('setup/paypal/', views.setup_paypal_method, name='setup_paypal'),
    
    # PayPal verification
    path('verify-paypal/<int:user_id>/', views.verify_paypal_account, name='verify_paypal'),
    path('verify-paypal-method/<int:method_id>/', views.verify_paypal_method_ajax, name='verify_paypal_method_ajax'),
    
    # Withdrawal requests
    path('request/', views.request_withdrawal, name='request'),
    path('verify-2fa/<uuid:withdrawal_id>/', views.verify_2fa, name='verify_2fa'),
    
    # History and details
    path('history/', views.withdrawal_history, name='history'),
    path('details/<uuid:withdrawal_id>/', views.withdrawal_details, name='details'),
    
    # Admin approval endpoints
    path('admin/approve/<uuid:withdrawal_id>/', admin_views.approve_withdrawal, name='admin_approve'),
    path('admin/reject/<uuid:withdrawal_id>/', admin_views.reject_withdrawal, name='admin_reject'),
    path('admin/details/<uuid:withdrawal_id>/', admin_views.get_withdrawal_details, name='admin_details'),
    
    # Webhooks
    path('webhook/stripe/', views.stripe_webhook, name='stripe_webhook'),
    path('webhook/paypal/', views.paypal_webhook, name='paypal_webhook'),
]
