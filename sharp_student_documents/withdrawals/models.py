from django.db import models
from django.contrib.auth import get_user_model
from django.utils import timezone
import uuid
from decimal import Decimal

User = get_user_model()

# Import TwoFactorAuth from security app
try:
    from security.models import TwoFactorAuth
except ImportError:
    TwoFactorAuth = None

class WithdrawalMethod(models.Model):
    """User's withdrawal methods (Stripe, PayPal, etc.)"""
    WITHDRAWAL_TYPES = [
        ('stripe', 'Stripe Connect'),
        ('paypal', 'PayPal'),
        ('bank', 'Direct Bank Transfer'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='withdrawal_methods')
    method_type = models.CharField(max_length=20, choices=WITHDRAWAL_TYPES)
    is_active = models.BooleanField(default=True)
    is_verified = models.BooleanField(default=False)
    
    # Stripe Connect fields
    stripe_account_id = models.CharField(max_length=255, blank=True, null=True)
    stripe_refresh_token = models.CharField(max_length=500, blank=True, null=True)
    
    # PayPal fields
    paypal_email = models.EmailField(blank=True, null=True)
    paypal_verified = models.BooleanField(default=False)
    
    # Bank fields (for future implementation)
    bank_name = models.CharField(max_length=100, blank=True, null=True)
    bank_account_number = models.CharField(max_length=50, blank=True, null=True)
    bank_routing_number = models.CharField(max_length=50, blank=True, null=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'withdrawal_methods'
        indexes = [
            models.Index(fields=['user', 'is_active']),
            models.Index(fields=['method_type', 'is_verified']),
        ]
    
    def __str__(self):
        return f"{self.user.username} - {self.get_method_type_display()}"

class WithdrawalRequest(models.Model):
    """User withdrawal requests"""
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('processing', 'Processing'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
        ('cancelled', 'Cancelled'),
        ('2fa_required', '2FA Required'),
    ]
    
    PAYOUT_TYPE_CHOICES = [
        ('weekly', 'Twice Monthly (14th & 28th)'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='withdrawal_requests')
    withdrawal_method = models.ForeignKey(WithdrawalMethod, on_delete=models.CASCADE, null=True, blank=True)
    
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    fee = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    net_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    
    payout_type = models.CharField(max_length=20, choices=PAYOUT_TYPE_CHOICES, default='weekly')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    
    # Processing details
    stripe_transfer_id = models.CharField(max_length=255, blank=True, null=True)
    paypal_payout_id = models.CharField(max_length=255, blank=True, null=True)
    
    # 2FA verification
    two_fa_verified = models.BooleanField(default=False)
    two_fa_token = models.CharField(max_length=10, blank=True, null=True)
    
    # Timestamps
    requested_at = models.DateTimeField(auto_now_add=True)
    processed_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    # Scheduling / bookkeeping
    scheduled_for = models.DateField(null=True, blank=True)
    wallet_debited = models.BooleanField(default=False)
    
    # Notes
    admin_notes = models.TextField(blank=True, null=True)
    failure_reason = models.TextField(blank=True, null=True)
    
    class Meta:
        db_table = 'withdrawal_requests'
        indexes = [
            models.Index(fields=['user', 'status']),
            models.Index(fields=['status', 'requested_at']),
            models.Index(fields=['payout_type', 'requested_at']),
            models.Index(fields=['withdrawal_method', 'status']),
        ]
        ordering = ['-requested_at']
    
    def __str__(self):
        return f"{self.user.username} - ${self.amount} ({self.get_status_display()})"
    
    def calculate_fee(self):
        """No withdrawal fees; seller receives full requested amount."""
        amount = Decimal(str(self.amount)) if not isinstance(self.amount, Decimal) else self.amount
        self.fee = Decimal("0.00")
        self.net_amount = amount
        self.save(update_fields=["fee", "net_amount"])
        return self.fee
    
    def requires_two_factor_auth(self):
        """Check if withdrawal requires 2FA verification"""
        from django.conf import settings
        if not bool(getattr(settings, "WITHDRAWALS_REQUIRE_2FA_FOR_WITHDRAWALS", False)):
            return False
        if not TwoFactorAuth:
            return False
        try:
            two_fa = self.user.two_factor
            # Require 2FA for all withdrawals for security
            return two_fa.is_enabled
        except TwoFactorAuth.DoesNotExist:
            return False

    # Backwards-compatible alias (older code/tests used this name).
    def requires_2fa(self):
        return self.requires_two_factor_auth()
    
    def can_process_instant(self):
        """Instant withdrawals are disabled (fraud risk)."""
        return False

class WithdrawalSchedule(models.Model):
    """Automated weekly withdrawal processing schedule"""
    DAY_CHOICES = [
        (0, 'Monday'),
        (1, 'Tuesday'),
        (2, 'Wednesday'),
        (3, 'Thursday'),
        (4, 'Friday'),
        (5, 'Saturday'),
        (6, 'Sunday'),
    ]
    
    day_of_week = models.IntegerField(choices=DAY_CHOICES, default=2)  # Wednesday
    processing_time = models.TimeField(default='12:00')  # 12:00 PM UTC
    is_active = models.BooleanField(default=True)
    
    last_processed = models.DateTimeField(null=True, blank=True)
    next_processing = models.DateTimeField(null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'withdrawal_schedule'
    
    def __str__(self):
        return f"Weekly Processing: {self.get_day_of_week_display()} at {self.processing_time}"
    
    def get_next_processing_time(self):
        """Calculate next processing time"""
        from datetime import datetime, timedelta
        
        now = timezone.now()
        current_weekday = now.weekday()
        target_weekday = self.day_of_week
        
        # Calculate days until next processing day
        days_until = (target_weekday - current_weekday) % 7
        if days_until == 0 and now.time() > self.processing_time:
            days_until = 7  # Next week if time has passed
        
        next_date = now + timedelta(days=days_until)
        return timezone.make_aware(
            datetime.combine(next_date.date(), self.processing_time),
            timezone.get_current_timezone()
        )

class WithdrawalTransaction(models.Model):
    """Individual withdrawal transactions for batch processing"""
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('processing', 'Processing'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
    ]
    
    withdrawal_request = models.ForeignKey(WithdrawalRequest, on_delete=models.CASCADE, related_name='transactions')
    transaction_id = models.CharField(max_length=255, unique=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    
    # External IDs
    stripe_transfer_id = models.CharField(max_length=255, blank=True, null=True)
    paypal_payout_item_id = models.CharField(max_length=255, blank=True, null=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    processed_at = models.DateTimeField(null=True, blank=True)
    
    # Response data
    response_data = models.JSONField(default=dict, blank=True)
    error_message = models.TextField(blank=True, null=True)
    
    class Meta:
        db_table = 'withdrawal_transactions'
        indexes = [
            models.Index(fields=['withdrawal_request', 'status']),
            models.Index(fields=['status', 'created_at']),
            models.Index(fields=['transaction_id']),
        ]
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Transaction {self.transaction_id} - {self.get_status_display()}"


class AdminNotification(models.Model):
    """Admin notifications for system events"""
    
    NOTIFICATION_TYPES = [
        ('withdrawal_request', 'Withdrawal Request'),
        ('large_withdrawal', 'Large Withdrawal'),
        ('failed_withdrawal', 'Failed Withdrawal'),
        ('suspicious_activity', 'Suspicious Activity'),
        ('system_alert', 'System Alert'),
        ('daily_summary', 'Daily Summary'),
        ('weekly_summary', 'Weekly Summary'),
    ]
    
    PRIORITY_LEVELS = [
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
        ('urgent', 'Urgent'),
    ]
    
    notification_type = models.CharField(
        max_length=20,
        choices=NOTIFICATION_TYPES,
        default='withdrawal_request'
    )
    priority = models.CharField(
        max_length=10,
        choices=PRIORITY_LEVELS,
        default='medium'
    )
    title = models.CharField(max_length=200)
    message = models.TextField()
    
    # Related objects
    user = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='admin_notifications'
    )
    withdrawal_request = models.ForeignKey(
        'WithdrawalRequest',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='admin_notifications'
    )
    
    # Metadata
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    read_at = models.DateTimeField(null=True, blank=True)

    # Email tracking
    requires_email = models.BooleanField(default=False)
    email_sent = models.BooleanField(default=False)
    
    # Additional data (JSON field for flexible data storage)
    data = models.JSONField(default=dict, blank=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['notification_type', 'is_read']),
            models.Index(fields=['priority', 'created_at']),
            models.Index(fields=['created_at']),
        ]
    
    def __str__(self):
        return f"{self.get_notification_type_display()}: {self.title}"
    
    def mark_as_read(self):
        """Mark notification as read"""
        if not self.is_read:
            self.is_read = True
            self.read_at = timezone.now()
            self.save()
    
    @classmethod
    def create_withdrawal_notification(cls, withdrawal_request):
        """Create notification for withdrawal request"""
        # Determine priority based on amount
        if withdrawal_request.amount >= Decimal('1000'):
            priority = 'high'
        elif withdrawal_request.amount >= Decimal('500'):
            priority = 'medium'
        else:
            priority = 'low'
        
        # Determine notification type
        if withdrawal_request.amount >= Decimal('1000'):
            notification_type = 'large_withdrawal'
        else:
            notification_type = 'withdrawal_request'
        
        return cls.objects.create(
            notification_type=notification_type,
            priority=priority,
            title=f'Withdrawal Request: ${withdrawal_request.amount}',
            message=f'{withdrawal_request.user.username} requested a {withdrawal_request.payout_type} withdrawal of ${withdrawal_request.amount} via {withdrawal_request.withdrawal_method.method_type}.',
            user=withdrawal_request.user,
            withdrawal_request=withdrawal_request,
            data={
                'withdrawal_id': str(withdrawal_request.id),
                'amount': str(withdrawal_request.amount),
                'user': withdrawal_request.user.username,
                'method': withdrawal_request.withdrawal_method.method_type,
                'type': withdrawal_request.payout_type,
            }
        )
    
    @classmethod
    def create_failed_withdrawal_notification(cls, withdrawal_request):
        """Create notification for failed withdrawal"""
        return cls.objects.create(
            notification_type='failed_withdrawal',
            priority='high',
            title=f'Failed Withdrawal: ${withdrawal_request.amount}',
            message=f'Withdrawal for {withdrawal_request.user.username} failed: {withdrawal_request.failure_reason}',
            user=withdrawal_request.user,
            withdrawal_request=withdrawal_request,
            data={
                'withdrawal_id': str(withdrawal_request.id),
                'amount': str(withdrawal_request.amount),
                'user': withdrawal_request.user.username,
                'failure_reason': withdrawal_request.failure_reason,
            }
        )
    
    @classmethod
    def get_unread_count(cls, notification_type=None):
        """Get count of unread notifications"""
        queryset = cls.objects.filter(is_read=False)
        if notification_type:
            queryset = queryset.filter(notification_type=notification_type)
        return queryset.count()
    
    @classmethod
    def get_recent_notifications(cls, hours=24, notification_type=None):
        """Get recent notifications"""
        from django.utils import timezone
        since = timezone.now() - timezone.timedelta(hours=hours)
        queryset = cls.objects.filter(created_at__gte=since)
        if notification_type:
            queryset = queryset.filter(notification_type=notification_type)
        return queryset.order_by('-created_at')
    
    @classmethod
    def create_suspicious_activity_notification(cls, user, activity_type, details):
        """Create notification for suspicious activity"""
        return cls.objects.create(
            notification_type='suspicious_activity',
            priority='urgent',
            title=f'Suspicious Activity: {activity_type}',
            message=f'Suspicious activity detected for user {user.username}: {details}',
            user=user,
            data={
                'activity_type': activity_type,
                'details': details,
                'user': user.username,
            }
        )
