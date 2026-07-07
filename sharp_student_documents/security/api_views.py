from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.contrib.auth.decorators import login_required, user_passes_test
from django.utils import timezone
import json
from django.contrib.auth import get_user_model

from .models import TwoFactorAuth, IdentityVerification, SecurityLog, FraudDetection
from .views import is_admin
import pyotp

User = get_user_model()

@login_required
@user_passes_test(lambda u: u.is_staff)
@require_http_methods(["GET"])
def verification_details(request, verification_id):
    """Get verification details via AJAX"""
    try:
        verification = IdentityVerification.objects.get(id=verification_id)
        
        data = {
            'id': verification.id,
            'username': verification.user.username,
            'email': verification.user.email,
            'verification_type': verification.verification_type,
            'verification_type_display': verification.get_verification_type_display(),
            'status': verification.status,
            'status_display': verification.get_status_display(),
            'created_at': verification.created_at.strftime('%Y-%m-%d %H:%M') if verification.created_at else None,
            'reviewed_at': verification.verified_at.strftime('%Y-%m-%d %H:%M') if verification.verified_at else None,
            'reviewed_by': verification.verified_by.username if verification.verified_by else None,
            'expires_at': verification.expires_at.strftime('%Y-%m-%d %H:%M') if verification.expires_at else None,
            'rejection_reason': verification.rejection_reason or '',
            'revocation_reason': verification.revocation_reason or '',
            'documents': verification.documents or [],
        }
        
        return JsonResponse({'success': True, 'data': data})
        
    except IdentityVerification.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Verification not found'})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})

@login_required
@user_passes_test(lambda u: u.is_staff)
@require_http_methods(["POST"])
def process_verification_action(request):
    """Process verification actions (approve, reject, revoke)"""
    try:
        verification_id = request.POST.get('verification_id')
        action_type = request.POST.get('action_type')
        
        verification = IdentityVerification.objects.get(id=verification_id)
        
        if action_type == 'approve':
            expiry_months = int(request.POST.get('expiry_months', 12))
            verification.approve(request.user, expiry_months)
            message = f'Verification approved for {verification.user.username}'
            
        elif action_type == 'reject':
            rejection_reason = request.POST.get('rejection_reason')
            verification.reject(request.user, rejection_reason)
            message = f'Verification rejected for {verification.user.username}'
            
        elif action_type == 'revoke':
            revocation_reason = request.POST.get('revocation_reason')
            # Revoke by setting status to expired
            verification.status = 'expired'
            verification.revocation_reason = revocation_reason
            verification.verified_by = request.user
            verification.verified_at = timezone.now()
            verification.save()
            message = f'Verification revoked for {verification.user.username}'
            
        else:
            return JsonResponse({'success': False, 'error': 'Invalid action type'})
        
        # Log security event
        SecurityLog.objects.create(
            user=request.user,
            event_type=f'verification_{action_type}',
            ip_address=request.META.get('REMOTE_ADDR', '127.0.0.1'),
            user_agent=request.META.get('HTTP_USER_AGENT', ''),
            details={
                'target_user': verification.user.username,
                'verification_id': verification.id,
                'action_type': action_type
            }
        )
        
        return JsonResponse({'success': True, 'message': message})
        
    except IdentityVerification.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Verification not found'})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})

@login_required
@user_passes_test(lambda u: u.is_staff)
@require_http_methods(["POST"])
def resubmit_verification(request, verification_id):
    """Allow user to resubmit verification"""
    try:
        verification = IdentityVerification.objects.get(id=verification_id)
        
        # Reset to pending status
        verification.status = 'pending'
        verification.rejection_reason = ''
        verification.revocation_reason = ''
        verification.verified_by = None
        verification.verified_at = None
        verification.save()
        
        # Log security event
        SecurityLog.objects.create(
            user=request.user,
            event_type='verification_resubmitted',
            ip_address=request.META.get('REMOTE_ADDR', '127.0.0.1'),
            user_agent=request.META.get('HTTP_USER_AGENT', ''),
            details={
                'target_user': verification.user.username,
                'verification_id': verification.id
            }
        )
        
        return JsonResponse({'success': True, 'message': f'Verification resubmitted for {verification.user.username}'})
        
    except IdentityVerification.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Verification not found'})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})

@login_required
@user_passes_test(lambda u: u.is_staff)
@require_http_methods(["GET"])
def user_2fa_details(request, user_id):
    """Get user 2FA details via AJAX"""
    try:
        user = User.objects.get(id=user_id)
        user_2fa = TwoFactorAuth.objects.filter(user=user).first()
        
        data = {
            'username': user.username,
            'email': user.email,
            'is_enabled': user_2fa.is_enabled if user_2fa else False,
            'last_used': user_2fa.last_used.strftime('%Y-%m-%d %H:%M') if user_2fa and user_2fa.last_used else None,
            'created_at': user_2fa.created_at.strftime('%Y-%m-%d %H:%M') if user_2fa else None,
            'backup_codes_count': user_2fa.backup_codes_count() if user_2fa else 0,
        }
        
        return JsonResponse({'success': True, 'data': data})
        
    except User.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'User not found'})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})

@login_required
@user_passes_test(lambda u: u.is_staff)
@require_http_methods(["POST"])
def enable_user_2fa(request, user_id):
    """Enable 2FA for a user"""
    try:
        user = User.objects.get(id=user_id)
        user_2fa, created = TwoFactorAuth.objects.get_or_create(user=user)
        
        # Generate new secret if not exists
        if not user_2fa.secret_key:
            user_2fa.secret_key = pyotp.random_base32()
        
        user_2fa.is_enabled = True
        user_2fa.save()
        
        # Generate backup codes if not exists
        if not user_2fa.backup_codes:
            user_2fa.generate_backup_codes()
        
        # Log security event
        SecurityLog.objects.create(
            user=request.user,
            event_type='2fa_enabled',
            ip_address=request.META.get('REMOTE_ADDR', '127.0.0.1'),
            user_agent=request.META.get('HTTP_USER_AGENT', ''),
            details={
                'target_user': user.username,
                'method': 'admin_action'
            }
        )
        
        return JsonResponse({'success': True, 'message': f'2FA enabled for {user.username}'})
        
    except User.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'User not found'})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})

@login_required
@user_passes_test(lambda u: u.is_staff)
@require_http_methods(["POST"])
def disable_user_2fa(request, user_id):
    """Disable 2FA for a user"""
    try:
        user = User.objects.get(id=user_id)
        user_2fa = TwoFactorAuth.objects.filter(user=user).first()
        
        if user_2fa:
            user_2fa.is_enabled = False
            user_2fa.save()
        
        # Log security event
        SecurityLog.objects.create(
            user=request.user,
            event_type='2fa_disabled',
            ip_address=request.META.get('REMOTE_ADDR', '127.0.0.1'),
            user_agent=request.META.get('HTTP_USER_AGENT', ''),
            details={
                'target_user': user.username,
                'method': 'admin_action'
            }
        )
        
        return JsonResponse({'success': True, 'message': f'2FA disabled for {user.username}'})
        
    except User.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'User not found'})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})

@login_required
@user_passes_test(lambda u: u.is_staff)
@require_http_methods(["POST"])
def reset_user_2fa(request, user_id):
    """Reset 2FA for a user (generate new secret and backup codes)"""
    try:
        user = User.objects.get(id=user_id)
        user_2fa, created = TwoFactorAuth.objects.get_or_create(user=user)
        
        # Generate new secret key
        user_2fa.secret_key = pyotp.random_base32()
        
        # Generate new backup codes
        user_2fa.generate_backup_codes()
        
        # Keep current enabled status
        user_2fa.save()
        
        # Log security event
        SecurityLog.objects.create(
            user=request.user,
            event_type='2fa_reset',
            ip_address=request.META.get('REMOTE_ADDR', '127.0.0.1'),
            user_agent=request.META.get('HTTP_USER_AGENT', ''),
            details={
                'target_user': user.username,
                'method': 'admin_action'
            }
        )
        
        return JsonResponse({'success': True, 'message': f'2FA reset for {user.username}'})
        
    except User.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'User not found'})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})

@require_http_methods(["GET"])
@login_required
@user_passes_test(is_admin)
def fraud_case_details(request, case_id):
    """Get fraud case details"""
    try:
        case = get_object_or_404(FraudDetection, id=case_id)
        
        data = {
            'success': True,
            'data': {
                'id': str(case.id),
                'username': case.user.username,
                'email': case.user.email,
                'risk_score': case.risk_score,
                'pattern_type': case.pattern_type,
                'pattern_type_display': case.get_pattern_type_display(),
                'created_at': case.created_at.strftime('%Y-%m-%d %H:%M:%S'),
                'status': 'Resolved' if case.is_resolved else 'Active',
                'resolved_at': case.resolved_at.strftime('%Y-%m-%d %H:%M:%S') if case.resolved_at else None,
                'details': case.details
            }
        }
        return JsonResponse(data)
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=400)

@require_http_methods(["POST"])
@login_required
@user_passes_test(is_admin)
def resolve_fraud_case(request, case_id):
    """Resolve a fraud case"""
    try:
        case = get_object_or_404(FraudDetection, id=case_id)
        
        case.is_resolved = True
        case.resolved_at = timezone.now()
        case.resolved_by = request.user
        case.save()
        
        # Log the action
        SecurityLog.objects.create(
            user=request.user,
            event_type='fraud_case_resolved',
            ip_address=request.META.get('REMOTE_ADDR', '127.0.0.1'),
            user_agent=request.META.get('HTTP_USER_AGENT', ''),
            details={
                'case_id': str(case.id),
                'target_user': case.user.username,
                'risk_score': case.risk_score
            }
        )
        
        return JsonResponse({
            'success': True,
            'message': 'Fraud case resolved successfully'
        })
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=400)

@require_http_methods(["POST"])
@login_required
@user_passes_test(is_admin)
def escalate_fraud_case(request, case_id):
    """Escalate a fraud case"""
    try:
        case = get_object_or_404(FraudDetection, id=case_id)
        
        # Increase risk score for escalation
        case.risk_score = min(100, case.risk_score + 20)
        case.save()
        
        # Log the escalation
        SecurityLog.objects.create(
            user=request.user,
            event_type='fraud_case_escalated',
            ip_address=request.META.get('REMOTE_ADDR', '127.0.0.1'),
            user_agent=request.META.get('HTTP_USER_AGENT', ''),
            details={
                'case_id': str(case.id),
                'target_user': case.user.username,
                'new_risk_score': case.risk_score
            }
        )
        
        return JsonResponse({
            'success': True,
            'message': 'Fraud case escalated successfully'
        })
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=400)

@require_http_methods(["POST"])
@login_required
@user_passes_test(is_admin)
def disable_user_account(request, user_id):
    """Disable a user account due to fraud"""
    try:
        user = get_object_or_404(User, id=user_id)
        
        # Check if user is trying to disable themselves
        if user == request.user:
            return JsonResponse({
                'success': False,
                'error': 'Cannot disable your own account'
            }, status=400)
        
        # Check if user is superuser
        if user.is_superuser:
            return JsonResponse({
                'success': False,
                'error': 'Cannot disable superuser account'
            }, status=400)
        
        # Parse request data
        data = json.loads(request.body)
        case_id = data.get('case_id')
        reason = data.get('reason', 'Fraud detection - suspicious activity')
        
        # Disable the account
        user.is_active = False
        user.save()
        
        # Log the action
        SecurityLog.objects.create(
            user=request.user,
            event_type='account_disabled',
            ip_address=request.META.get('REMOTE_ADDR', '127.0.0.1'),
            user_agent=request.META.get('HTTP_USER_AGENT', ''),
            details={
                'target_user': user.username,
                'target_user_id': user.id,
                'case_id': case_id,
                'reason': reason
            }
        )
        
        # If case_id provided, update the fraud case
        if case_id:
            try:
                fraud_case = FraudDetection.objects.get(id=case_id)
                fraud_case.auto_action_taken = 'suspended'
                fraud_case.save()
            except FraudDetection.DoesNotExist:
                pass
        
        return JsonResponse({
            'success': True,
            'message': f'Account for {user.username} has been disabled'
        })
        
    except User.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'User not found'}, status=404)
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=400)

@require_http_methods(["POST"])
@login_required
@user_passes_test(is_admin)
def enable_user_account(request, user_id):
    """Re-enable a user account after review"""
    try:
        user = get_object_or_404(User, id=user_id)
        
        # Parse request data
        data = json.loads(request.body)
        case_id = data.get('case_id')
        reason = data.get('reason', 'Account re-enabled after review')
        
        # Enable the account
        user.is_active = True
        user.save()
        
        # Log the action
        SecurityLog.objects.create(
            user=request.user,
            event_type='account_enabled',
            ip_address=request.META.get('REMOTE_ADDR', '127.0.0.1'),
            user_agent=request.META.get('HTTP_USER_AGENT', ''),
            details={
                'target_user': user.username,
                'target_user_id': user.id,
                'case_id': case_id,
                'reason': reason
            }
        )
        
        return JsonResponse({
            'success': True,
            'message': f'Account for {user.username} has been re-enabled'
        })
        
    except User.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'User not found'}, status=404)
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=400)
