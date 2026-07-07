import logging
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.contrib import messages
from withdrawals.models import WithdrawalRequest
from withdrawals.services import WithdrawalService
from sales.models import Wallet

logger = logging.getLogger(__name__)

@login_required
@require_POST
def approve_withdrawal(request, withdrawal_id):
    """Approve a withdrawal request"""
    if not request.user.is_superuser:
        return JsonResponse({'success': False, 'error': 'Permission denied'})
    
    withdrawal = get_object_or_404(WithdrawalRequest, id=withdrawal_id)
    
    if withdrawal.status != 'pending':
        return JsonResponse({'success': False, 'error': 'Withdrawal is not pending'})
    
    try:
        # Instant withdrawals are disabled; approving means scheduling for the next payout day.
        withdrawal.processed_at = timezone.now()
        withdrawal.save(update_fields=["processed_at"])

        WithdrawalService._schedule_weekly_withdrawal(withdrawal)
        
        # TODO: Add notification system when available
        # For now, just log the action
        logger.info(
            "Admin %s approved withdrawal %s for user %s",
            request.user.username,
            withdrawal.id,
            withdrawal.user.username,
        )
        
        # Refresh the withdrawal object to get the latest status
        withdrawal.refresh_from_db()
        
        return JsonResponse({
            'success': True,
            'message': 'Withdrawal approved successfully',
            'new_status': withdrawal.status
        })
        
    except Exception as e:
        withdrawal.status = 'failed'
        withdrawal.failure_reason = f"Processing error: {str(e)}"
        withdrawal.save(update_fields=["status", "failure_reason"])

        if withdrawal.wallet_debited:
            try:
                wallet = Wallet.objects.get(user=withdrawal.user)
                wallet.release_reserved_withdrawal(withdrawal.amount, reason=f"Withdrawal failed: {withdrawal.failure_reason}")
                withdrawal.wallet_debited = False
                withdrawal.save(update_fields=["wallet_debited"])
            except Exception:
                logger.exception("Failed to release reserved funds for withdrawal %s", withdrawal.id)
        return JsonResponse({'success': False, 'error': str(e)})


@login_required
@require_POST
def reject_withdrawal(request, withdrawal_id):
    """Reject a withdrawal request"""
    if not request.user.is_superuser:
        return JsonResponse({'success': False, 'error': 'Permission denied'})
    
    withdrawal = get_object_or_404(WithdrawalRequest, id=withdrawal_id)
    
    if withdrawal.status not in ['pending', 'processing']:
        return JsonResponse({'success': False, 'error': 'Cannot reject withdrawal in current status'})
    
    try:
        reason = request.POST.get('reason', 'Withdrawal rejected by admin')
        
        # Update status to failed
        withdrawal.status = 'failed'
        withdrawal.failure_reason = reason
        withdrawal.processed_at = timezone.now()
        withdrawal.save()

        if withdrawal.wallet_debited:
            try:
                wallet = Wallet.objects.get(user=withdrawal.user)
                wallet.release_reserved_withdrawal(withdrawal.amount, reason=f"Withdrawal rejected: {reason}")
                withdrawal.wallet_debited = False
                withdrawal.save(update_fields=["wallet_debited"])
            except Exception:
                logger.exception("Failed to release reserved funds for withdrawal %s", withdrawal.id)
        
        # TODO: Add notification system when available
        # For now, just log the action
        logger.info(
            "Admin %s rejected withdrawal %s for user %s",
            request.user.username,
            withdrawal.id,
            withdrawal.user.username,
        )
        
        return JsonResponse({
            'success': True,
            'message': 'Withdrawal rejected successfully',
            'new_status': withdrawal.status
        })
        
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})


@login_required
def get_withdrawal_details(request, withdrawal_id):
    """Get detailed information about a withdrawal request"""
    logger.debug("get_withdrawal_details withdrawal_id=%s", withdrawal_id)
    
    if not request.user.is_superuser:
        logger.warning("Permission denied: user is not superuser")
        return JsonResponse({'success': False, 'error': 'Permission denied'})
    
    try:
        withdrawal = get_object_or_404(WithdrawalRequest, id=withdrawal_id)
        logger.debug("Withdrawal found: %s", withdrawal)
    except Exception as e:
        logger.exception("Error getting withdrawal")
        return JsonResponse({'success': False, 'error': str(e)})
    
    if not withdrawal:
        logger.warning("Withdrawal not found")
        return JsonResponse({'success': False, 'error': 'Withdrawal not found'})
    
    details = {
        'id': str(withdrawal.id),
        'user': {
            'username': withdrawal.user.username,
            'email': withdrawal.user.email
        },
        'amount': str(withdrawal.amount),
        'fee': str(withdrawal.fee),
        'net_amount': str(withdrawal.net_amount),
        'payout_type': withdrawal.get_payout_type_display(),
        'status': withdrawal.status,
        'requested_at': withdrawal.requested_at.isoformat(),
        'can_approve': withdrawal.status == 'pending',
        'can_reject': withdrawal.status in ['pending', 'processing']
    }
    
    # Add method-specific details
    if not withdrawal.withdrawal_method:
        details["withdrawal_method"] = {
            "type": "legacy",
            "details": {},
        }
    elif withdrawal.withdrawal_method.method_type == 'paypal':
        details['withdrawal_method'] = {
            'type': withdrawal.withdrawal_method.method_type,
            'details': {
                'email': withdrawal.withdrawal_method.paypal_email,
                'verified': withdrawal.withdrawal_method.is_verified
            }
        }
    
    elif withdrawal.withdrawal_method.method_type == 'stripe':
        details['withdrawal_method'] = {
            'type': withdrawal.withdrawal_method.method_type,
            'details': {
                'account_id': withdrawal.withdrawal_method.stripe_account_id,
                'verified': withdrawal.withdrawal_method.is_verified
            }
        }
    else:
        details['withdrawal_method'] = {
            'type': withdrawal.withdrawal_method.method_type,
            'details': {}
        }
    
    response_data = {'success': True, 'details': details}
    return JsonResponse(response_data)
