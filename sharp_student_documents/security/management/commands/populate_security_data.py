from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.utils import timezone
from decimal import Decimal
import random

User = get_user_model()

class Command(BaseCommand):
    help = 'Populate security models with test data for dashboard testing'

    def handle(self, *args, **options):
        self.stdout.write('Populating security data for dashboard testing...')
        
        # Get or create test users
        users = User.objects.all()[:5]  # Get first 5 users
        if not users:
            self.stdout.write('No users found. Creating test users first...')
            # Create test users
            for i in range(3):
                user = User.objects.create_user(
                    username=f'testuser{i}',
                    email=f'test{i}@example.com',
                    password='testpass123',
                    is_seller=True
                )
                users.append(user)
        
        # Create Security Logs
        self.create_security_logs(users)
        
        # Create TwoFactorAuth records
        self.create_2fa_records(users)
        
        # Create Identity Verifications
        self.create_identity_verifications(users)
        
        # Create Fraud Detection records
        self.create_fraud_detections(users)
        
        self.stdout.write(self.style.SUCCESS('Security data populated successfully!'))

    def create_security_logs(self, users):
        """Create sample security logs"""
        event_types = ['login_success', 'login_failed', 'password_change', '2fa_enabled', '2fa_disabled']
        severities = ['low', 'medium', 'high', 'critical']
        
        from security.models import SecurityLog
        
        for user in users:
            for _ in range(random.randint(3, 8)):
                SecurityLog.objects.create(
                    user=user,
                    event_type=random.choice(event_types),
                    severity=random.choice(severities),
                    ip_address=f'192.168.1.{random.randint(1, 255)}',
                    user_agent='Mozilla/5.0 (Test Browser)',
                    details={'test': 'sample data'},
                    created_at=timezone.now() - timezone.timedelta(days=random.randint(0, 30))
                )
        
        self.stdout.write(f'Created {SecurityLog.objects.count()} security logs')

    def create_2fa_records(self, users):
        """Create sample 2FA records"""
        from security.models import TwoFactorAuth
        
        for user in users[:3]:  # Enable 2FA for first 3 users
            TwoFactorAuth.objects.get_or_create(
                user=user,
                defaults={
                    'secret_key': 'test_secret_key_' + str(random.randint(1000, 9999)),
                    'is_enabled': True,
                    'backup_codes': ['123456', '789012', '345678', '901234'],
                    'last_used': timezone.now() - timezone.timedelta(hours=random.randint(1, 24))
                }
            )
        
        self.stdout.write(f'Created {TwoFactorAuth.objects.filter(is_enabled=True).count()} active 2FA records')

    def create_identity_verifications(self, users):
        """Create sample identity verifications"""
        from security.models import IdentityVerification
        
        verification_types = ['government_id', 'student_id', 'university_email', 'phone', 'social_media']
        statuses = ['pending', 'approved', 'rejected', 'expired']
        
        for user in users:
            for _ in range(random.randint(1, 3)):
                IdentityVerification.objects.create(
                    user=user,
                    verification_type=random.choice(verification_types),
                    status=random.choice(statuses),
                    verification_data={
                        'document_type': 'test_document',
                        'document_number': f'TEST{random.randint(100000, 999999)}'
                    },
                    created_at=timezone.now() - timezone.timedelta(days=random.randint(1, 60))
                )
        
        self.stdout.write(f'Created {IdentityVerification.objects.count()} identity verifications')

    def create_fraud_detections(self, users):
        """Create sample fraud detection records"""
        from security.models import FraudDetection
        
        pattern_types = ['multiple_accounts', 'unusual_activity', 'suspicious_uploads', 'fake_reviews', 'payment_fraud']
        
        for user in users[:2]:  # Create fraud cases for first 2 users
            for _ in range(random.randint(1, 2)):
                FraudDetection.objects.create(
                    user=user,
                    pattern_type=random.choice(pattern_types),
                    risk_score=random.randint(20, 95),
                    is_resolved=False,
                    details={
                        'reason': 'Test fraud detection',
                        'evidence': 'Sample evidence data'
                    },
                    is_confirmed=random.choice([True, False]),
                    auto_action_taken=random.choice(['flagged', 'limited', 'suspended']),
                    created_at=timezone.now() - timezone.timedelta(days=random.randint(1, 30))
                )
        
        self.stdout.write(f'Created {FraudDetection.objects.count()} fraud detection records')
