# Security signals for automated fraud detection and security monitoring

import logging
from django.db.models.signals import post_save
from django.contrib.auth.signals import user_logged_in, user_login_failed
from django.dispatch import receiver
from django.utils import timezone
from django.contrib.auth import get_user_model

from .models import SecurityLog, FraudDetection
from .views import analyze_login_pattern

User = get_user_model()
logger = logging.getLogger(__name__)

@receiver(user_logged_in)
def log_successful_login(sender, request, user, **kwargs):
    """Log successful login attempts"""
    try:
        SecurityLog.objects.create(
            user=user,
            event_type='login_success',
            ip_address=request.META.get('REMOTE_ADDR', '127.0.0.1'),
            user_agent=request.META.get('HTTP_USER_AGENT', ''),
            details={
                'login_method': getattr(request, 'login_method', 'password'),
                'timestamp': timezone.now().isoformat()
            }
        )
        
        # Analyze for suspicious patterns
        try:
            analyze_login_pattern(user, request.META.get('REMOTE_ADDR'))
        except Exception as fraud_error:
            # Log fraud detection error but don't break login
            logger.exception("Fraud detection error during login")
             
    except Exception as e:
        # Log security log error but don't break login
        logger.exception("Security log error during login")

@receiver(user_login_failed)
def log_failed_login(sender, request, credentials, **kwargs):
    """Log failed login attempts"""
    username = credentials.get('username', '')
    
    try:
        user = User.objects.get(username=username)
    except User.DoesNotExist:
        user = None
    
    # Only create security log if user exists (user field is required)
    if user:
        SecurityLog.objects.create(
            user=user,
            event_type='login_failed',
            ip_address=request.META.get('REMOTE_ADDR', '127.0.0.1'),
            user_agent=request.META.get('HTTP_USER_AGENT', ''),
            details={
                'username': username,
                'timestamp': timezone.now().isoformat(),
                'failure_reason': 'invalid_credentials'
            }
        )
    
    # Check for brute force patterns (only if we have an IP address)
    ip_address = request.META.get('REMOTE_ADDR')
    if ip_address:
        recent_failures = SecurityLog.objects.filter(
            event_type='login_failed',
            ip_address=ip_address,
            created_at__gte=timezone.now() - timezone.timedelta(minutes=15)
        ).count()
        
        if recent_failures >= 5:
            # Potential brute force attack - only create if user exists
            if user:
                try:
                    FraudDetection.objects.create(
                        user=user,
                        pattern_type='unusual_activity',
                        risk_score=85,
                        details={
                            'type': 'brute_force_attempt',
                            'failure_count': recent_failures,
                            'time_window': '15 minutes'
                        }
                    )
                except Exception as e:
                    # Log the error but don't break the login process
                    logger.exception("Error creating FraudDetection record")

@receiver(post_save, sender=User)
def monitor_user_creation(sender, instance, created, **kwargs):
    """Monitor new user registrations for fraud"""
    if created:
        # Check for suspicious patterns
        ip_address = getattr(instance, '_registration_ip', None)
        
        if ip_address:
            # Check for multiple accounts from same IP
            recent_accounts = User.objects.filter(
                date_joined__gte=timezone.now() - timezone.timedelta(hours=24)
            ).count()
            
            if recent_accounts > 5:
                try:
                    FraudDetection.objects.create(
                        user=instance,
                        pattern_type='multiple_accounts',
                        risk_score=75,
                        details={
                            'type': 'multiple_registrations',
                            'account_count': recent_accounts,
                            'time_window': '24 hours'
                        }
                    )
                except Exception as e:
                    # Log the error but don't break the registration process
                    logger.exception("Error creating FraudDetection record for user creation")
