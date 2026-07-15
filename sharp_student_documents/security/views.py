from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.http import JsonResponse, HttpResponse
from django.contrib.auth import login, authenticate
from django.core.mail import send_mail
from django.conf import settings
from django.utils import timezone
from django.db.models import Count, Q, Avg
import pyotp
import qrcode
from io import BytesIO
import base64
import uuid
import logging

from accounts.models import CustomUser

logger = logging.getLogger(__name__)
from .models import TwoFactorAuth, IdentityVerification, SecurityLog, FraudDetection, Watermark
from withdrawals.models import AdminNotification
from notifications.utils import send_admin_notification

def is_admin(user):
    """Check if user is admin or superuser"""
    return user.is_superuser or user.is_staff

@login_required
@user_passes_test(is_admin)
def security_dashboard(request):
    """Comprehensive security dashboard for administrators"""
    
    # Security Statistics
    total_2fa_users = TwoFactorAuth.objects.filter(is_enabled=True).count()
    total_users = CustomUser.objects.count()
    two_fa_adoption_rate = (total_2fa_users / total_users * 100) if total_users > 0 else 0
    
    # Identity Verification Statistics
    pending_verifications = IdentityVerification.objects.filter(status='pending').count()
    approved_verifications = IdentityVerification.objects.filter(status='approved').count()
    rejected_verifications = IdentityVerification.objects.filter(status='rejected').count()
    expired_verifications = IdentityVerification.objects.filter(status='expired').count()
    total_verifications = IdentityVerification.objects.count()
    
    # Fraud Detection Statistics
    fraud_cases = FraudDetection.objects.filter(is_confirmed=False).count()
    confirmed_fraud_cases = FraudDetection.objects.filter(is_confirmed=True).count()
    high_risk_cases = FraudDetection.objects.filter(risk_score__gte=70, is_confirmed=False).count()
    medium_risk_cases = FraudDetection.objects.filter(risk_score__gte=40, risk_score__lt=70, is_confirmed=False).count()
    low_risk_cases = FraudDetection.objects.filter(risk_score__lt=40, is_confirmed=False).count()
    
    # Security Log Statistics
    total_security_events = SecurityLog.objects.count()
    critical_events = SecurityLog.objects.filter(severity='critical').count()
    recent_logins = SecurityLog.objects.filter(event_type='login_success').order_by("-created_at")[:10]
    security_events = SecurityLog.objects.filter(severity__in=['medium', 'high', 'critical']).order_by("-created_at")[:10]
    
    # Recent Activities
    recent_fraud_cases = FraudDetection.objects.filter(is_confirmed=False).order_by("-created_at")[:5]
    recent_verifications = IdentityVerification.objects.filter(status='pending').order_by("-created_at")[:5]
    
    # Watermark Statistics
    total_watermarks = Watermark.objects.count()
    enabled_watermarks = Watermark.objects.filter(is_enabled=True).count()
    
    context = {
        # 2FA Statistics
        'total_2fa_users': total_2fa_users,
        'total_users': total_users,
        'two_fa_adoption_rate': round(two_fa_adoption_rate, 1),
        
        # Verification Statistics
        'pending_verifications': pending_verifications,
        'approved_verifications': approved_verifications,
        'rejected_verifications': rejected_verifications,
        'expired_verifications': expired_verifications,
        'total_verifications': total_verifications,
        
        # Fraud Detection Statistics
        'fraud_cases': fraud_cases,
        'confirmed_fraud_cases': confirmed_fraud_cases,
        'high_risk_cases': high_risk_cases,
        'medium_risk_cases': medium_risk_cases,
        'low_risk_cases': low_risk_cases,
        
        # Security Log Statistics
        'total_security_events': total_security_events,
        'critical_events': critical_events,
        
        # Recent Activities
        'recent_logins': recent_logins,
        'security_events': security_events,
        'recent_fraud_cases': recent_fraud_cases,
        'recent_verifications': recent_verifications,
        
        # Watermark Statistics
        'total_watermarks': total_watermarks,
        'enabled_watermarks': enabled_watermarks,
        
        # Admin Links
        'admin_2fa_url': '/admin/security/twofactorauth/',
        'admin_verification_url': '/admin/security/identityverification/',
        'admin_fraud_url': '/admin/security/frauddetection/',
        'admin_logs_url': '/admin/security/securitylog/',
        'admin_watermark_url': '/admin/security/watermark/',
    }
    
    return render(request, 'security/security_dashboard.html', context)

def generate_qr_code(request):
    """Generate QR code for 2FA setup"""
    if not request.user.is_authenticated:
        return JsonResponse({'error': 'Authentication required'}, status=401)
    
    # Generate secret key
    secret = pyotp.random_base32()
    
    # Create or update 2FA record
    two_factor, created = TwoFactorAuth.objects.get_or_create(user=request.user)
    two_factor.secret_key = secret
    two_factor.save()
    
    # Generate QR code
    totp_uri = pyotp.totp.TOTP(secret).provisioning_uri(
        name=request.user.email,
        issuer_name="SharpDocs"
    )
    
    qr = qrcode.QRCode(version=1, box_size=10, border=5)
    qr.add_data(totp_uri)
    qr.make(fit=True)
    
    # Convert to image
    img = qr.make_image(fill_color="black", back_color="white")
    buffer = BytesIO()
    img.save(buffer, format='PNG')
    buffer.seek(0)
    
    # Convert to base64 for display
    qr_image = base64.b64encode(buffer.getvalue()).decode()
    
    return render(request, 'security/2fa_setup.html', {
        'qr_image': qr_image,
        'secret_key': secret,
        'backup_codes': two_factor.generate_backup_codes()
    })

@login_required
def enable_2fa(request):
    """Enable two-factor authentication"""
    if request.method == 'POST':
        code = request.POST.get('code')
        secret = request.POST.get('secret')
        
        if not code or not secret:
            messages.error(request, 'Verification code and secret are required')
            return redirect('security:2fa_setup')
        
        # Verify the code
        totp = pyotp.TOTP(secret)
        if totp.verify(code):
            # Enable 2FA for user
            two_factor, created = TwoFactorAuth.objects.get_or_create(user=request.user)
            two_factor.secret_key = secret
            two_factor.is_enabled = True
            two_factor.save()
            
            # Log security event
            SecurityLog.objects.create(
                user=request.user,
                event_type='2fa_enabled',
                ip_address=request.META.get('REMOTE_ADDR'),
                user_agent=request.META.get('HTTP_USER_AGENT', ''),
                details={'method': 'totp'}
            )
            
            messages.success(request, 'Two-factor authentication enabled successfully!')
            # Send email notification
            try:
                send_mail(
                    subject='2FA Enabled - SharpDocs',
                    message=f'Two-factor authentication has been enabled on your SharpDocs account.\n'
                            f'If you did not do this, please contact support immediately.',
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=[request.user.email],
                    fail_silently=True,
                )
            except Exception:
                pass
            return redirect('accounts:profile')
        else:
            messages.error(request, 'Invalid verification code')
            return redirect('security:2fa_setup')
    
    return redirect('security:2fa_setup')

@login_required
def disable_2fa(request):
    """Disable two-factor authentication"""
    if request.method == 'POST':
        password = request.POST.get('password')
        
        if not request.user.check_password(password):
            messages.error(request, 'Invalid password')
            return redirect('security:disable_2fa')
        
        # Disable 2FA
        two_factor = TwoFactorAuth.objects.filter(user=request.user).first()
        if two_factor:
            two_factor.is_enabled = False
            two_factor.save()
            
            # Log security event
            SecurityLog.objects.create(
                user=request.user,
                event_type='2fa_disabled',
                ip_address=request.META.get('REMOTE_ADDR'),
                user_agent=request.META.get('HTTP_USER_AGENT', ''),
                details={'method': 'user_request'}
            )
            
            messages.success(request, 'Two-factor authentication disabled')
            # Send email notification
            try:
                send_mail(
                    subject='2FA Disabled - SharpDocs',
                    message=f'Two-factor authentication has been disabled on your SharpDocs account.\n'
                            f'If you did not do this, please contact support immediately.',
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=[request.user.email],
                    fail_silently=True,
                )
            except Exception:
                pass
        
        return redirect('accounts:profile')
    
    return render(request, 'security/disable_2fa.html')

@login_required
def verify_identity(request):
    """Submit identity verification"""
    if request.method == 'POST':
        verification_type = request.POST.get('verification_type')
        documents = request.FILES.getlist('documents')
        
        if not verification_type or not documents:
            messages.error(request, 'Verification type and documents are required')
            return redirect('security:verify_identity')
        
        # Create verification record
        verification = IdentityVerification.objects.create(
            user=request.user,
            verification_type=verification_type,
            status='pending',
            documents=[{
                'name': doc.name,
                'size': doc.size,
                'type': doc.content_type
            } for doc in documents]
        )
        
        # Log security event
        SecurityLog.objects.create(
            user=request.user,
            event_type='verification_submitted',
            ip_address=request.META.get('REMOTE_ADDR'),
            user_agent=request.META.get('HTTP_USER_AGENT', ''),
            details={
                'verification_type': verification_type,
                'document_count': len(documents)
            }
        )
        
        messages.success(request, 'Identity verification submitted for review')
        # Notify admin about new verification request
        try:
            send_admin_notification(
                subject=f'New Identity Verification: {request.user.username}',
                message=f'User {request.user.username} ({request.user.email}) submitted a '
                        f'{verification_type} verification with {len(documents)} document(s).'
            )
        except Exception:
            pass
        return redirect('security:verification_status')
    
    return render(request, 'security/verify_identity.html')

@login_required
def verification_status(request):
    """Show identity verification status"""
    verifications = IdentityVerification.objects.filter(user=request.user).order_by('-created_at')
    
    # Check if user is verified
    is_verified = verifications.filter(status='approved', expires_at__gt=timezone.now()).exists()
    
    return render(request, 'security/verification_status.html', {
        'verifications': verifications,
        'is_verified': is_verified
    })

def two_factor_verify(request):
    """Verify 2FA code during login"""
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        two_factor_code = request.POST.get('two_factor_code')
        
        # Authenticate user
        user = authenticate(username=username, password=password)
        if user is None:
            return JsonResponse({'error': 'Invalid credentials'}, status=400)
        
        # Check if 2FA is enabled
        two_factor = TwoFactorAuth.objects.filter(user=user, is_enabled=True).first()
        if two_factor:
            totp = pyotp.TOTP(two_factor.secret_key)
            if not totp.verify(two_factor_code):
                # Check backup codes
                if two_factor.verify_backup_code(two_factor_code):
                    two_factor.last_used = timezone.now()
                    two_factor.save()
                    login(request, user)
                    return JsonResponse({'success': True, 'message': 'Login successful with backup code'})
                else:
                    return JsonResponse({'error': 'Invalid 2FA code'}, status=400)
            else:
                two_factor.last_used = timezone.now()
                two_factor.save()
                login(request, user)
                return JsonResponse({'success': True, 'message': 'Login successful'})
        else:
            # No 2FA required, proceed with normal login
            login(request, user)
            return JsonResponse({'success': True, 'message': 'Login successful'})
    
    return JsonResponse({'error': 'Invalid request'}, status=400)

@login_required
def security_settings(request):
    """Manage security settings"""
    watermark_settings, created = Watermark.objects.get_or_create(user=request.user)
    
    # Check identity verification status
    verifications = IdentityVerification.objects.filter(user=request.user).order_by('-created_at')
    is_verified = verifications.filter(status='approved', expires_at__gt=timezone.now()).exists()
    
    if request.method == 'POST':
        watermark_settings.is_enabled = request.POST.get('is_enabled') == 'on'
        watermark_settings.watermark_text = request.POST.get('watermark_text', '')
        watermark_settings.watermark_opacity = int(request.POST.get('watermark_opacity', 30))
        watermark_settings.watermark_position = request.POST.get('watermark_position', 'center')
        watermark_settings.include_user_info = request.POST.get('include_user_info') == 'on'
        watermark_settings.include_timestamp = request.POST.get('include_timestamp') == 'on'
        
        # New watermark fields
        watermark_settings.auto_watermark = request.POST.get('auto_watermark') == 'on'
        watermark_settings.watermark_size = int(request.POST.get('watermark_size', 20))
        watermark_settings.watermark_color = request.POST.get('watermark_color', '#CCCCCC')
        watermark_settings.watermark_rotation = int(request.POST.get('watermark_rotation', 45))
        
        watermark_settings.save()
        
        messages.success(request, 'Security settings updated successfully')
        return redirect('security:settings')
    
    return render(request, 'security/settings.html', {
        'watermark_settings': watermark_settings,
        'is_verified': is_verified
    })

@login_required
def security_logs(request):
    """View security logs"""
    logs = SecurityLog.objects.filter(user=request.user).order_by('-created_at')[:50]
    
    return render(request, 'security/logs.html', {
        'logs': logs
    })

@login_required
@user_passes_test(is_admin)
def manage_2fa(request):
    """Manage 2FA settings for all users"""
    
    # Get statistics
    total_2fa_users = TwoFactorAuth.objects.filter(is_enabled=True).count()
    total_users = CustomUser.objects.count()
    two_fa_adoption_rate = (total_2fa_users / total_users * 100) if total_users > 0 else 0
    
    # Count backup codes
    total_backup_codes = TwoFactorAuth.objects.exclude(backup_codes='').count()
    
    # Get all 2FA records with pagination
    user_2fa_list = TwoFactorAuth.objects.select_related('user').order_by('-created_at')
    
    # Simple pagination (you can replace with Django Paginator)
    page = request.GET.get('page', 1)
    
    context = {
        'total_users': total_users,
        'total_2fa_users': total_2fa_users,
        'two_fa_adoption_rate': round(two_fa_adoption_rate, 1),
        'total_backup_codes': total_backup_codes,
        'user_2fa_list': user_2fa_list,
        'is_paginated': False,  # Set to True if implementing pagination
        'page_obj': None,
    }
    
    return render(request, 'security/manage_2fa.html', context)

@login_required
@user_passes_test(is_admin)
def verification_review(request):
    """Review and manage identity verification requests"""
    
    # Get statistics
    from django.db.models import Count, Q
    from datetime import timedelta
    from django.utils import timezone
    
    one_week_ago = timezone.now() - timedelta(days=7)
    
    total_verifications = IdentityVerification.objects.count()
    approved_verifications = IdentityVerification.objects.filter(status='approved').count()
    rejected_verifications = IdentityVerification.objects.filter(status='rejected').count()
    pending_verifications = IdentityVerification.objects.filter(status='pending').count()
    expired_verifications = IdentityVerification.objects.filter(status='expired').count()
    new_verifications = IdentityVerification.objects.filter(created_at__gte=one_week_ago).count()
    
    approval_rate = (approved_verifications / total_verifications * 100) if total_verifications > 0 else 0
    rejection_rate = (rejected_verifications / total_verifications * 100) if total_verifications > 0 else 0
    
    # Get all verifications with filtering
    verifications = IdentityVerification.objects.select_related('user', 'verified_by').order_by('-created_at')
    
    # Apply filters
    status_filter = request.GET.get('status', '')
    type_filter = request.GET.get('type', '')
    search_query = request.GET.get('search', '')
    
    if status_filter:
        verifications = verifications.filter(status=status_filter)
    
    if type_filter:
        verifications = verifications.filter(verification_type=type_filter)
    
    if search_query:
        verifications = verifications.filter(
            Q(user__username__icontains=search_query) |
            Q(user__email__icontains=search_query)
        )
    
    # Simple pagination (you can replace with Django Paginator)
    page = request.GET.get('page', 1)
    
    context = {
        'total_verifications': total_verifications,
        'approved_verifications': approved_verifications,
        'rejected_verifications': rejected_verifications,
        'pending_verifications': pending_verifications,
        'expired_verifications': expired_verifications,
        'new_verifications': new_verifications,
        'approval_rate': round(approval_rate, 1),
        'rejection_rate': round(rejection_rate, 1),
        'verifications': verifications,
        'is_paginated': False,  # Set to True if implementing pagination
        'page_obj': None,
    }
    
    return render(request, 'security/verification_review.html', context)

@user_passes_test(is_admin)
def trust_security(request):
    """Trust & Security dashboard overview"""
    from django.db.models import Count, Q
    from django.contrib.auth import get_user_model
    
    User = get_user_model()
    
    # Two-Factor Authentication Stats
    users_with_2fa = TwoFactorAuth.objects.filter(is_enabled=True).count()
    total_users = User.objects.filter(is_active=True).count()
    twofa_percentage = round((users_with_2fa / total_users * 100), 1) if total_users > 0 else 0
    
    # Identity Verification Stats
    verified_sellers = IdentityVerification.objects.filter(status='approved').count()
    pending_verifications = IdentityVerification.objects.filter(status='pending').count()
    total_sellers = User.objects.filter(is_seller=True).count()
    verified_percentage = round((verified_sellers / total_sellers * 100), 1) if total_sellers > 0 else 0
    
    # Fraud Detection Stats
    high_risk_cases = FraudDetection.objects.filter(risk_score__gte=80, is_resolved=False).count()
    medium_risk_cases = FraudDetection.objects.filter(risk_score__gte=50, risk_score__lt=80, is_resolved=False).count()
    low_risk_cases = FraudDetection.objects.filter(risk_score__lt=50, is_resolved=False).count()
    active_fraud_cases = high_risk_cases + medium_risk_cases + low_risk_cases
    
    # Watermark Stats
    watermarks_enabled = Watermark.objects.filter(is_enabled=True).count()
    total_documents = User.objects.count()  # Simplified - you might want to count actual documents
    watermark_percentage = round((watermarks_enabled / total_documents * 100), 1) if total_documents > 0 else 0
    
    context = {
        'users_with_2fa': users_with_2fa,
        'total_users': total_users,
        'twofa_percentage': twofa_percentage,
        'verified_sellers': verified_sellers,
        'pending_verifications': pending_verifications,
        'total_sellers': total_sellers,
        'verified_percentage': verified_percentage,
        'high_risk_cases': high_risk_cases,
        'medium_risk_cases': medium_risk_cases,
        'low_risk_cases': low_risk_cases,
        'active_fraud_cases': active_fraud_cases,
        'watermarks_enabled': watermarks_enabled,
        'total_documents': total_documents,
        'watermark_percentage': watermark_percentage,
    }
    
    return render(request, 'security/trust_security.html', context)

@user_passes_test(is_admin)
def fraud_cases_review(request):
    """Review and manage fraud detection cases"""
    
    # Get statistics
    from django.db.models import Count, Q
    from datetime import timedelta
    from django.utils import timezone
    
    high_risk_cases = FraudDetection.objects.filter(risk_score__gte=80, is_resolved=False).count()
    medium_risk_cases = FraudDetection.objects.filter(risk_score__gte=50, risk_score__lt=80, is_resolved=False).count()
    low_risk_cases = FraudDetection.objects.filter(risk_score__lt=50, is_resolved=False).count()
    total_cases = FraudDetection.objects.count()
    
    # Get all fraud cases
    fraud_cases = FraudDetection.objects.select_related('user').order_by('-created_at')
    
    context = {
        'high_risk_cases': high_risk_cases,
        'medium_risk_cases': medium_risk_cases,
        'low_risk_cases': low_risk_cases,
        'total_cases': total_cases,
        'fraud_cases': fraud_cases,
    }
    
    return render(request, 'security/fraud_cases_review.html', context)

def detect_fraud_activity(user, event_type, details=None, risk_score=0):
    """AI-powered fraud detection"""
    # Check for suspicious patterns
    fraud_alert = FraudDetection.objects.create(
        user=user,
        pattern_type=event_type,
        risk_score=risk_score,
        is_resolved=False,
        details=details or {}
    )
    
    # Auto-action based on risk score
    if risk_score >= 80:
        fraud_alert.auto_action_taken = 'suspended'
        user.is_active = False
        user.save()
    elif risk_score >= 60:
        fraud_alert.auto_action_taken = 'limited'
        # Implement rate limiting or other restrictions
    
    fraud_alert.save()
    
    # Create admin notification for fraud detection
    try:
        if risk_score >= 40:
            AdminNotification.create_suspicious_activity_notification(
                user=user,
                activity_type=event_type,
                details=f"Risk score: {risk_score}. {details or ''}"
            )
    except Exception:
        logger.exception("Failed to create fraud admin notification")
    
    return fraud_alert

def analyze_login_pattern(user, ip_address):
    """Analyze login patterns for fraud detection"""
    recent_logs = SecurityLog.objects.filter(
        user=user,
        event_type='login_success',
        created_at__gte=timezone.now() - timezone.timedelta(hours=24)
    )
    
    # Check for multiple IPs
    unique_ips = set(log.ip_address for log in recent_logs)
    if len(unique_ips) > 3:
        return detect_fraud_activity(
            user, 
            'multiple_accounts',
            {'unique_ips': len(unique_ips), 'ips': list(unique_ips)},
            risk_score=70
        )
    
    # Check for unusual time patterns
    login_times = [log.created_at for log in recent_logs]
    if len(login_times) > 5:
        # Detect if logins are happening at unusual intervals
        return detect_fraud_activity(
            user,
            'unusual_activity',
            {'login_count': len(login_times)},
            risk_score=50
        )
    
    return None
