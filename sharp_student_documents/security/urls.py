from django.urls import path
from . import views
from . import api_views

app_name = 'security'

urlpatterns = [
    # Security Dashboard
    path('dashboard/', views.security_dashboard, name='dashboard'),
    path('trust-security/', views.trust_security, name='trust_security'),
    
    # Two-Factor Authentication
    path('2fa/setup/', views.generate_qr_code, name='2fa_setup'),
    path('2fa/enable/', views.enable_2fa, name='enable_2fa'),
    path('2fa/disable/', views.disable_2fa, name='disable_2fa'),
    path('2fa/manage/', views.manage_2fa, name='manage_2fa'),
    path('2fa/verify/', views.two_factor_verify, name='two_factor_verify'),
    
    # 2FA Management API
    path('api/user-2fa-details/<int:user_id>/', api_views.user_2fa_details, name='api_user_2fa_details'),
    path('api/enable-user-2fa/<int:user_id>/', api_views.enable_user_2fa, name='api_enable_user_2fa'),
    path('api/disable-user-2fa/<int:user_id>/', api_views.disable_user_2fa, name='api_disable_user_2fa'),
    path('api/reset-user-2fa/<int:user_id>/', api_views.reset_user_2fa, name='api_reset_user_2fa'),
    
    # Identity Verification
    path('verify/', views.verify_identity, name='verify_identity'),
    path('verify/status/', views.verification_status, name='verification_status'),
    path('verify/review/', views.verification_review, name='verification_review'),
    
    # Verification Management API
    path('api/verification-details/<int:verification_id>/', api_views.verification_details, name='api_verification_details'),
    path('api/process-verification-action/', api_views.process_verification_action, name='api_process_verification_action'),
    path('api/resubmit-verification/<int:verification_id>/', api_views.resubmit_verification, name='api_resubmit_verification'),
    
    # Fraud Cases Management
    path('fraud/cases/', views.fraud_cases_review, name='fraud_cases_review'),
    
    # Fraud Cases API
    path('api/fraud-case-details/<int:case_id>/', api_views.fraud_case_details, name='api_fraud_case_details'),
    path('api/resolve-fraud-case/<int:case_id>/', api_views.resolve_fraud_case, name='api_resolve_fraud_case'),
    path('api/escalate-fraud-case/<int:case_id>/', api_views.escalate_fraud_case, name='api_escalate_fraud_case'),
    
    # User Account Management API
    path('api/disable-user-account/<int:user_id>/', api_views.disable_user_account, name='api_disable_user_account'),
    path('api/enable-user-account/<int:user_id>/', api_views.enable_user_account, name='api_enable_user_account'),
    
    # Security Settings
    path('settings/', views.security_settings, name='settings'),
    path('logs/', views.security_logs, name='logs'),
]
