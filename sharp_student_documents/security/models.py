from django.db import models
from django.conf import settings
from django.utils import timezone
from django.utils.crypto import constant_time_compare, salted_hmac
import pyotp
import qrcode
from io import BytesIO
import base64
from PIL import Image
import hashlib
import ast
import json
import secrets
import logging

logger = logging.getLogger(__name__)

class TwoFactorAuth(models.Model):
    """
    Two-factor authentication for enhanced security
    """
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="two_factor"
    )
    secret_key = models.CharField(max_length=32, unique=True, default=pyotp.random_base32)
    backup_codes = models.TextField(blank=True)  # JSON list of hashed backup codes (legacy values may exist)
    is_enabled = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    last_used = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        indexes = [
            models.Index(fields=['user', 'is_enabled']),
        ]
    
    def __str__(self):
        return f"{self.user.username} - 2FA {'Enabled' if self.is_enabled else 'Disabled'}"
    
    def generate_secret(self):
        """Generate a new secret key"""
        self.secret_key = pyotp.random_base32()
        self.save()
        return self.secret_key

    def _hash_backup_code(self, code: str) -> str:
        return salted_hmac(
            "two_factor_backup_code",
            code,
            secret=self.secret_key or settings.SECRET_KEY,
            algorithm="sha256",
        ).hexdigest()

    def _parse_backup_codes(self):
        """
        Returns a list of stored codes.

        New format: JSON list of sha256 hex digests.
        Legacy format: stringified Python list of plain codes (handled via ast.literal_eval).
        """
        if not self.backup_codes:
            return []

        raw = self.backup_codes.strip()
        if not raw:
            return []

        try:
            data = json.loads(raw)
            if isinstance(data, list):
                return data
        except Exception:
            pass

        try:
            data = ast.literal_eval(raw)
            if isinstance(data, list):
                return [str(x) for x in data]
        except Exception:
            return []

        return []

    def backup_codes_count(self) -> int:
        return len(self._parse_backup_codes())
    
    def generate_qr_code(self):
        """Generate QR code for 2FA setup"""
        if not self.secret_key:
            self.generate_secret()
        
        totp_uri = pyotp.totp.TOTP(self.secret_key).provisioning_uri(
            name=self.user.email,
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
        return qr_image
    
    def verify_token(self, token):
        """Verify TOTP token"""
        if not self.secret_key or not self.is_enabled:
            return False
        
        totp = pyotp.TOTP(self.secret_key)
        return totp.verify(token)
    
    def generate_backup_codes(self):
        """Generate 10 backup codes"""
        # 8-digit numeric codes for user entry; store only hashes in DB.
        codes = [f"{secrets.randbelow(10**8):08d}" for _ in range(10)]
        hashed_codes = [self._hash_backup_code(code) for code in codes]
        self.backup_codes = json.dumps(hashed_codes)
        self.save()
        return codes
    
    def verify_backup_code(self, code):
        """Verify a backup code and remove it if valid"""
        stored = self._parse_backup_codes()
        if not stored:
            return False

        def _is_sha256_hex(value: str) -> bool:
            return (
                isinstance(value, str)
                and len(value) == 64
                and all(ch in "0123456789abcdef" for ch in value.lower())
            )

        # Legacy: stored plain codes. If present, consume and migrate to hashed storage.
        if not all(_is_sha256_hex(x) for x in stored):
            if code in stored:
                stored.remove(code)
                self.backup_codes = json.dumps([self._hash_backup_code(c) for c in stored])
                self.save(update_fields=["backup_codes"])
                return True
            return False

        hashed_input = self._hash_backup_code(code)
        for idx, stored_hash in enumerate(list(stored)):
            if isinstance(stored_hash, str) and constant_time_compare(stored_hash, hashed_input):
                del stored[idx]
                self.backup_codes = json.dumps(stored)
                self.save(update_fields=["backup_codes"])
                return True

        return False

class IdentityVerification(models.Model):
    """
    Identity verification for sellers to build trust
    """
    VERIFICATION_TYPES = [
        ('government_id', 'Government ID'),
        ('student_id', 'Student ID'),
        ('university_email', 'University Email'),
        ('phone', 'Phone Number'),
        ('social', 'Social Media'),
    ]
    
    VERIFICATION_STATUS = [
        ('pending', 'Pending Review'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('expired', 'Expired'),
    ]
    
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="verifications"
    )
    verification_type = models.CharField(max_length=20, choices=VERIFICATION_TYPES)
    status = models.CharField(max_length=20, choices=VERIFICATION_STATUS, default='pending')
    verification_data = models.JSONField(default=dict)  # Store verification details
    documents = models.JSONField(default=list)  # Store uploaded documents
    verified_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="verified_users",
        limit_choices_to={'is_staff': True}
    )
    verified_at = models.DateTimeField(null=True, blank=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    rejection_reason = models.TextField(blank=True)
    revocation_reason = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', 'status']),
            models.Index(fields=['status', 'created_at']),
        ]
    
    def __str__(self):
        return f"{self.user.username} - {self.get_verification_type_display()} ({self.status})"
    
    def is_valid(self):
        """Check if verification is still valid"""
        if self.status == 'approved' and self.expires_at:
            return timezone.now() < self.expires_at
        return self.status == 'approved'
    
    def approve(self, verified_by, expiry_months=12):
        """Approve verification"""
        self.status = 'approved'
        self.verified_by = verified_by
        self.verified_at = timezone.now()
        self.expires_at = timezone.now() + timezone.timedelta(days=expiry_months)  # Valid for specified period
        self.save()
    
    def reject(self, verified_by, reason):
        """Reject verification"""
        self.status = 'rejected'
        self.verified_by = verified_by
        self.rejection_reason = reason
        self.save()

class SecurityLog(models.Model):
    """
    Log security events for fraud detection
    """
    EVENT_TYPES = [
        ('login', 'Login Attempt'),
        ('login_success', 'Successful Login'),
        ('login_failed', 'Failed Login'),
        ('password_change', 'Password Change'),
        ('2fa_enabled', '2FA Enabled'),
        ('2fa_disabled', '2FA Disabled'),
        ('verification_submitted', 'Identity Verification Submitted'),
        ('suspicious_activity', 'Suspicious Activity'),
        ('account_locked', 'Account Locked'),
    ]
    
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="security_logs"
    )
    event_type = models.CharField(max_length=30, choices=EVENT_TYPES)
    ip_address = models.GenericIPAddressField()
    user_agent = models.TextField(blank=True)
    details = models.JSONField(default=dict)
    severity = models.CharField(
        max_length=10,
        choices=[
            ('low', 'Low'),
            ('medium', 'Medium'),
            ('high', 'High'),
            ('critical', 'Critical'),
        ],
        default='low'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', 'created_at']),
            models.Index(fields=['event_type', 'created_at']),
            models.Index(fields=['severity', 'created_at']),
        ]
    
    def __str__(self):
        return f"{self.user.username} - {self.get_event_type_display()}"

class FraudDetection(models.Model):
    """
    AI-powered fraud detection patterns
    """
    PATTERN_TYPES = [
        ('multiple_accounts', 'Multiple Accounts from Same IP'),
        ('unusual_activity', 'Unusual Activity Pattern'),
        ('suspicious_uploads', 'Suspicious Upload Behavior'),
        ('fake_reviews', 'Fake Review Patterns'),
        ('payment_fraud', 'Payment Fraud Indicators'),
        ('account_takeover', 'Account Takeover Indicators'),
    ]
    
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="fraud_alerts"
    )
    pattern_type = models.CharField(max_length=30, choices=PATTERN_TYPES)
    risk_score = models.IntegerField(default=0)  # 0-100 risk score
    details = models.JSONField(default=dict)
    is_confirmed = models.BooleanField(default=False)
    is_resolved = models.BooleanField(default=False)
    resolved_at = models.DateTimeField(null=True, blank=True)
    resolved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="resolved_fraud_cases",
        limit_choices_to={'is_staff': True}
    )
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="reviewed_fraud_cases",
        limit_choices_to={'is_staff': True}
    )
    auto_action_taken = models.CharField(
        max_length=50,
        choices=[
            ('none', 'None'),
            ('flagged', 'Flagged for Review'),
            ('limited', 'Account Limited'),
            ('suspended', 'Account Suspended'),
        ],
        default='flagged'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    reviewed_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        ordering = ['-risk_score', '-created_at']
        indexes = [
            models.Index(fields=['user', 'risk_score']),
            models.Index(fields=['pattern_type', 'created_at']),
            models.Index(fields=['is_confirmed', 'created_at']),
        ]
    
    def __str__(self):
        return f"{self.user.username} - {self.get_pattern_type_display()} (Risk: {self.risk_score})"

class Watermark(models.Model):
    """
    Watermark settings for document preview protection
    """
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="watermark_settings"
    )
    is_enabled = models.BooleanField(default=True)
    watermark_text = models.CharField(max_length=100, blank=True)
    watermark_opacity = models.IntegerField(default=30)  # 0-100%
    watermark_position = models.CharField(
        max_length=20,
        choices=[
            ('center', 'Center'),
            ('top_left', 'Top Left'),
            ('top_right', 'Top Right'),
            ('bottom_left', 'Bottom Left'),
            ('bottom_right', 'Bottom Right'),
        ],
        default='center'
    )
    include_user_info = models.BooleanField(default=True)
    include_timestamp = models.BooleanField(default=True)
    auto_watermark = models.BooleanField(default=True)  # Automatically watermark new uploads
    watermark_size = models.IntegerField(default=20)  # Font size
    watermark_color = models.CharField(max_length=7, default='#CCCCCC')  # Hex color
    watermark_rotation = models.IntegerField(default=45)  # Rotation angle
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        indexes = [
            models.Index(fields=['user', 'is_enabled']),
            models.Index(fields=['auto_watermark']),
        ]
    
    def __str__(self):
        return f"{self.user.username} - Watermark {'Enabled' if self.is_enabled else 'Disabled'}"
    
    def generate_watermark_text(self, document_title=None):
        """Generate dynamic watermark text"""
        text_parts = []
        
        if self.watermark_text:
            text_parts.append(self.watermark_text)
        elif document_title:
            text_parts.append(f"Preview: {document_title}")
        else:
            text_parts.append("SharpDocs Preview")
        
        if self.include_user_info:
            text_parts.append(f"User: {self.user.username}")
        
        if self.include_timestamp:
            text_parts.append(f"Generated: {timezone.now().strftime('%Y-%m-%d %H:%M')}")
        
        return " | ".join(text_parts)
    
    def apply_watermark(self, image_path, document_title=None):
        """Apply watermark to an image with enhanced features"""
        if not self.is_enabled:
            return image_path
        
        try:
            from PIL import Image, ImageDraw, ImageFont
            import os
            
            # Open the image
            image = Image.open(image_path)
            
            # Make a copy to avoid modifying original
            watermarked = image.copy()
            
            # Create drawing context
            draw = ImageDraw.Draw(watermarked)
            
            # Generate watermark text
            watermark_text = self.generate_watermark_text(document_title)
            
            # Try to load a font, fallback to default
            try:
                font = ImageFont.truetype("arial.ttf", self.watermark_size)
            except:
                font = ImageFont.load_default()
            
            # Calculate text size
            bbox = draw.textbbox((0, 0), watermark_text, font=font)
            text_width = bbox[2] - bbox[0]
            text_height = bbox[3] - bbox[1]
            
            # Calculate position
            img_width, img_height = watermarked.size
            margin = 20
            
            positions = {
                'center': ((img_width - text_width) // 2, (img_height - text_height) // 2),
                'top_left': (margin, margin),
                'top_right': (img_width - text_width - margin, margin),
                'bottom_left': (margin, img_height - text_height - margin),
                'bottom_right': (img_width - text_width - margin, img_height - text_height - margin),
            }
            
            x, y = positions.get(self.watermark_position, positions['center'])
            
            # Apply rotation if needed
            if self.watermark_rotation != 0:
                # Create a rotated text image
                text_img = Image.new('RGBA', (text_width + 20, text_height + 20), (0, 0, 0, 0))
                text_draw = ImageDraw.Draw(text_img)
                text_draw.text((10, 10), watermark_text, font=font, fill=self.watermark_color + '80')
                rotated_text = text_img.rotate(self.watermark_rotation, expand=1)
                
                # Paste rotated text
                watermarked.paste(rotated_text, (x, y), rotated_text)
            else:
                # Draw text directly
                opacity_hex = hex(int(self.watermark_opacity * 2.55)).lstrip('0x').zfill(2)
                color_with_opacity = self.watermark_color + opacity_hex
                draw.text((x, y), watermark_text, font=font, fill=color_with_opacity)
            
            # Save watermarked image
            watermarked_path = image_path.replace('.', '_watermarked.')
            watermarked.save(watermarked_path)
            
            return watermarked_path
            
        except Exception as e:
            logger.exception("Error applying watermark")
            return image_path
