from django.db import models
from django.conf import settings
from django.utils import timezone


class UserNotification(models.Model):
    NOTIFICATION_TYPES = [
        ('purchase_confirmed', 'Purchase Confirmed'),
        ('sale_made', 'Sale Made'),
        ('withdrawal_approved', 'Withdrawal Approved'),
        ('withdrawal_rejected', 'Withdrawal Rejected'),
        ('withdrawal_completed', 'Withdrawal Completed'),
        ('withdrawal_failed', 'Withdrawal Failed'),
        ('refund_requested', 'Refund Requested on Your Document'),
        ('refund_processed', 'Refund Processed'),
        ('review_received', 'Review Received'),
        ('identity_verified', 'Identity Verified'),
        ('identity_rejected', 'Identity Rejected'),
        ('verification_submitted', 'Verification Submitted'),
        ('wallet_credited', 'Wallet Credited'),
        ('wallet_debited', 'Wallet Debited'),
        ('system_message', 'System Message'),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='notifications'
    )
    notification_type = models.CharField(
        max_length=30,
        choices=NOTIFICATION_TYPES
    )
    title = models.CharField(max_length=200)
    message = models.TextField()
    link = models.CharField(max_length=500, blank=True, default='')
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    read_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', 'is_read']),
            models.Index(fields=['user', '-created_at']),
        ]

    def __str__(self):
        return f"{self.user.username}: {self.title}"

    def mark_as_read(self):
        if not self.is_read:
            self.is_read = True
            self.read_at = timezone.now()
            self.save(update_fields=['is_read', 'read_at'])

    @classmethod
    def create_notification(cls, user, notification_type, title, message, link=''):
        return cls.objects.create(
            user=user,
            notification_type=notification_type,
            title=title,
            message=message,
            link=link,
        )
