from django.db import models
from django.contrib.auth import get_user_model
from django.utils import timezone
from decimal import Decimal
from datetime import timedelta

User = get_user_model()


class FraudDetection(models.Model):
    """Fraud detection system for monitoring suspicious activities"""
    
    ALERT_TYPES = [
        ('rapid_withdrawals', 'Rapid Withdrawals'),
        ('large_amount', 'Large Amount'),
        ('unusual_pattern', 'Unusual Pattern'),
        ('multiple_accounts', 'Multiple Accounts'),
        ('suspicious_location', 'Suspicious Location'),
        ('failed_attempts', 'Failed Attempts'),
    ]
    
    SEVERITY_LEVELS = [
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
        ('critical', 'Critical'),
    ]
    
    alert_type = models.CharField(
        max_length=20,
        choices=ALERT_TYPES,
        default='rapid_withdrawals'
    )
    severity = models.CharField(
        max_length=10,
        choices=SEVERITY_LEVELS,
        default='medium'
    )
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='withdrawal_fraud_alerts'
    )
    description = models.TextField()
    
    # Related objects
    withdrawal_request = models.ForeignKey(
        'withdrawals.WithdrawalRequest',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='fraud_alerts'
    )
    
    # Metadata
    is_resolved = models.BooleanField(default=False)
    is_blocked = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    resolved_at = models.DateTimeField(null=True, blank=True)
    resolved_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='resolved_fraud_alerts'
    )
    
    # Additional data
    data = models.JSONField(default=dict, blank=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['alert_type', 'is_resolved']),
            models.Index(fields=['severity', 'created_at']),
            models.Index(fields=['user', 'created_at']),
        ]
    
    def __str__(self):
        return f"{self.get_alert_type_display()}: {self.user.username}"
    
    def resolve(self, resolved_by, note=""):
        """Resolve fraud alert"""
        self.is_resolved = True
        self.resolved_at = timezone.now()
        self.resolved_by = resolved_by
        self.data['resolution_note'] = note
        self.save()
    
    @classmethod
    def check_rapid_withdrawals(cls, user, time_window_minutes=30, max_withdrawals=3):
        """Check for rapid withdrawals within time window"""
        from withdrawals.models import WithdrawalRequest
        
        time_threshold = timezone.now() - timedelta(minutes=time_window_minutes)
        recent_withdrawals = WithdrawalRequest.objects.filter(
            user=user,
            requested_at__gte=time_threshold
        ).count()
        
        if recent_withdrawals >= max_withdrawals:
            severity = 'high' if recent_withdrawals >= 5 else 'medium'
            
            return cls.objects.create(
                alert_type='rapid_withdrawals',
                severity=severity,
                user=user,
                description=f'User has made {recent_withdrawals} withdrawals in the last {time_window_minutes} minutes',
                data={
                    'withdrawal_count': recent_withdrawals,
                    'time_window': time_window_minutes,
                    'threshold': max_withdrawals,
                }
            )
        return None
    
    @classmethod
    def check_large_amount(cls, user, amount, threshold=Decimal('1000')):
        """Check for unusually large withdrawal amounts"""
        from withdrawals.models import WithdrawalRequest
        
        # Get user's average withdrawal amount
        user_withdrawals = WithdrawalRequest.objects.filter(user=user)
        if user_withdrawals.count() < 3:
            return None  # Not enough history
        
        avg_amount = user_withdrawals.aggregate(
            avg=models.Avg('amount')
        )['avg'] or Decimal('0')
        
        # Check if current amount is significantly higher than average
        if amount > threshold or amount > (avg_amount * 5):
            severity = 'critical' if amount > Decimal('5000') else 'high'
            
            return cls.objects.create(
                alert_type='large_amount',
                severity=severity,
                user=user,
                description=f'Unusually large withdrawal: ${amount} (avg: ${avg_amount:.2f})',
                withdrawal_request=user_withdrawals.order_by('-requested_at').first(),
                data={
                    'amount': str(amount),
                    'average_amount': str(avg_amount),
                    'threshold': str(threshold),
                    'ratio': float(amount / avg_amount) if avg_amount > 0 else 0,
                }
            )
        return None
    
    @classmethod
    def check_failed_attempts(cls, user, max_attempts=5, time_window_hours=24):
        """Check for multiple failed withdrawal attempts"""
        from withdrawals.models import WithdrawalRequest
        
        time_threshold = timezone.now() - timedelta(hours=time_window_hours)
        failed_withdrawals = WithdrawalRequest.objects.filter(
            user=user,
            status='failed',
            requested_at__gte=time_threshold
        ).count()
        
        if failed_withdrawals >= max_attempts:
            severity = 'critical' if failed_withdrawals >= 10 else 'high'
            
            return cls.objects.create(
                alert_type='failed_attempts',
                severity=severity,
                user=user,
                description=f'User has {failed_withdrawals} failed withdrawals in the last {time_window_hours} hours',
                data={
                    'failed_count': failed_withdrawals,
                    'time_window': time_window_hours,
                    'threshold': max_attempts,
                }
            )
        return None
    
    @classmethod
    def check_unusual_pattern(cls, user):
        """Check for unusual withdrawal patterns"""
        from withdrawals.models import WithdrawalRequest
        
        # Get withdrawal history
        withdrawals = WithdrawalRequest.objects.filter(user=user).order_by('-requested_at')[:20]
        if withdrawals.count() < 10:
            return None  # Not enough history
        
        # Check for pattern anomalies
        amounts = [w.amount for w in withdrawals]
        times = [w.requested_at for w in withdrawals]
        
        # Check for round numbers (potential testing)
        round_numbers = sum(1 for amount in amounts if amount % 100 == 0)
        if round_numbers > len(amounts) * 0.7:  # More than 70% are round numbers
            return cls.objects.create(
                alert_type='unusual_pattern',
                severity='medium',
                user=user,
                description=f'Unusual pattern: {round_numbers}/{len(amounts)} withdrawals are round numbers',
                data={
                    'round_number_count': round_numbers,
                    'total_withdrawals': len(amounts),
                    'pattern_type': 'round_numbers',
                }
            )
        
        return None
    
    @classmethod
    def run_fraud_check(cls, user, withdrawal_request=None):
        """Run comprehensive fraud check on user"""
        alerts = []
        
        # Check rapid withdrawals
        if withdrawal_request:
            rapid_alert = cls.check_rapid_withdrawals(user)
            if rapid_alert:
                alerts.append(rapid_alert)
            
            # Check large amount
            large_alert = cls.check_large_amount(user, withdrawal_request.amount)
            if large_alert:
                alerts.append(large_alert)
        
        # Check failed attempts
        failed_alert = cls.check_failed_attempts(user)
        if failed_alert:
            alerts.append(failed_alert)
        
        # Check unusual patterns
        pattern_alert = cls.check_unusual_pattern(user)
        if pattern_alert:
            alerts.append(pattern_alert)
        
        return alerts
    
    @classmethod
    def get_user_risk_score(cls, user):
        """Calculate user's risk score based on fraud alerts"""
        alerts = cls.objects.filter(user=user, is_resolved=False)
        
        # Base score
        score = 0
        
        # Add points for each alert based on severity
        severity_scores = {
            'low': 1,
            'medium': 3,
            'high': 7,
            'critical': 15,
        }
        
        for alert in alerts:
            score += severity_scores.get(alert.severity, 0)
        
        # Cap at 100
        return min(score, 100)
    
    @classmethod
    def should_block_withdrawal(cls, user, amount):
        """Determine if withdrawal should be blocked based on fraud risk"""
        risk_score = cls.get_user_risk_score(user)
        
        # Block if risk score is high
        if risk_score >= 50:
            return True, f"High risk score: {risk_score}"
        
        # Block if user has critical alerts
        critical_alerts = cls.objects.filter(
            user=user,
            severity='critical',
            is_resolved=False
        )
        
        if critical_alerts.exists():
            return True, "Critical fraud alerts detected"
        
        # Block if amount is extremely high
        if amount > Decimal('10000'):
            return True, "Amount exceeds safety threshold"
        
        return False, None


class FraudRule(models.Model):
    """Configurable fraud detection rules"""
    
    RULE_TYPES = [
        ('amount_threshold', 'Amount Threshold'),
        ('frequency_limit', 'Frequency Limit'),
        ('time_window', 'Time Window'),
        ('pattern_detection', 'Pattern Detection'),
    ]
    
    rule_type = models.CharField(max_length=20, choices=RULE_TYPES)
    name = models.CharField(max_length=100)
    description = models.TextField()
    
    # Rule parameters (JSON)
    parameters = models.JSONField(default=dict)
    
    # Status
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['rule_type', 'name']
    
    def __str__(self):
        return f"{self.get_rule_type_display()}: {self.name}"
    
    def evaluate(self, user, withdrawal_request=None):
        """Evaluate the rule against user data"""
        if self.rule_type == 'amount_threshold':
            return self._evaluate_amount_threshold(user, withdrawal_request)
        elif self.rule_type == 'frequency_limit':
            return self._evaluate_frequency_limit(user)
        elif self.rule_type == 'pattern_detection':
            return self._evaluate_pattern_detection(user)
        
        return False, "Rule type not implemented"
    
    def _evaluate_amount_threshold(self, user, withdrawal_request):
        """Evaluate amount threshold rule"""
        if not withdrawal_request:
            return False, "No withdrawal request provided"
        
        threshold = Decimal(str(self.parameters.get('threshold', '1000')))
        if withdrawal_request.amount > threshold:
            return True, f"Amount ${withdrawal_request.amount} exceeds threshold ${threshold}"
        
        return False, None
    
    def _evaluate_frequency_limit(self, user):
        """Evaluate frequency limit rule"""
        from withdrawals.models import WithdrawalRequest
        
        max_count = self.parameters.get('max_count', 3)
        time_window = self.parameters.get('time_window_minutes', 30)
        
        time_threshold = timezone.now() - timedelta(minutes=time_window)
        count = WithdrawalRequest.objects.filter(
            user=user,
            requested_at__gte=time_threshold
        ).count()
        
        if count > max_count:
            return True, f"Too many withdrawals: {count} in {time_window} minutes (max: {max_count})"
        
        return False, None
    
    def _evaluate_pattern_detection(self, user):
        """Evaluate pattern detection rule"""
        pattern_type = self.parameters.get('pattern_type', 'round_numbers')
        
        if pattern_type == 'round_numbers':
            from withdrawals.models import WithdrawalRequest
            
            withdrawals = WithdrawalRequest.objects.filter(user=user).order_by('-requested_at')[:20]
            if withdrawals.count() < 10:
                return False, "Insufficient history"
            
            round_numbers = sum(1 for w in withdrawals if w.amount % 100 == 0)
            threshold = self.parameters.get('threshold_percentage', 70)
            
            if (round_numbers / len(withdrawals) * 100) > threshold:
                return True, f"Unusual pattern: {round_numbers}/{len(withdrawals)} are round numbers"
        
        return False, None
