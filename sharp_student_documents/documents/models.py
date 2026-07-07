from django.db import models
from django.conf import settings
from django.utils.text import slugify
from cloudinary.models import CloudinaryField


class Category(models.Model):
    CATEGORY_TYPES = [
        ('course', 'Course Materials'),
        ('subject', 'Subject Specific'),
        ('notes', 'Class Notes'),
        ('revision', 'Revision Papers'),
        ('exam', 'Exam Papers'),
        ('guide', 'Study Guides'),
        ('reference', 'Reference Materials'),
        ('lab', 'Lab Reports'),
        ('project', 'Project Reports'),
        ('thesis', 'Thesis & Dissertations'),
        ('case_study', 'Case Studies'),
        ('tutorial', 'Tutorials'),
        ('syllabus', 'Syllabus'),
        ('textbook', 'Textbooks'),
        ('assignment', 'Assignments'),
        ('research', 'Research Papers'),
        ('presentation', 'Presentations'),
        ('worksheet', 'Worksheets'),
        ('cheat_sheet', 'Cheat Sheets'),
        ('other', 'Other'),
    ]
    
    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(unique=True, blank=True)
    category_type = models.CharField(
        max_length=20,
        choices=CATEGORY_TYPES,
        default='other',
        help_text='Type of category for better organization'
    )
    description = models.TextField(
        blank=True,
        null=True,
        help_text='Detailed description of what this category contains'
    )
    icon = models.CharField(
        max_length=50,
        blank=True,
        help_text='Icon class for category display (e.g., bi-book, bi-file-text, etc.)'
    )
    is_active = models.BooleanField(
        default=True,
        help_text='Whether this category is available for new uploads'
    )
    sort_order = models.PositiveIntegerField(
        default=0,
        help_text='Order for displaying categories'
    )
    
    class Meta:
        verbose_name_plural = "Categories"
        ordering = ["sort_order", "category_type", "name"]
        indexes = [
            models.Index(fields=['category_type', 'name']),
            models.Index(fields=['is_active', 'sort_order']),
        ]

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


class Document(models.Model):
    # Document types for better categorization
    DOCUMENT_TYPES = [
        ('notes', 'Class Notes'),
        ('revision', 'Revision Papers'),
        ('exam', 'Exam Papers'),
        ('guide', 'Study Guide'),
        ('textbook', 'Textbook Chapter'),
        ('assignment', 'Assignment Solution'),
        ('research', 'Research Paper'),
        ('presentation', 'Presentation'),
        ('lab', 'Lab Report'),
        ('project', 'Project Report'),
        ('thesis', 'Thesis'),
        ('case_study', 'Case Study'),
        ('tutorial', 'Tutorial'),
        ('syllabus', 'Syllabus'),
        ('worksheet', 'Worksheet'),
        ('cheat_sheet', 'Cheat Sheet'),
        ('other', 'Other'),
    ]
    
    # Academic levels
    ACADEMIC_LEVELS = [
        ('high_school', 'High School'),
        ('undergraduate', 'Undergraduate'),
        ('graduate', 'Graduate'),
        ('professional', 'Professional'),
        ('other', 'Other'),
    ]

    LICENSE_CHOICES = [
        ("all_rights_reserved", "All rights reserved"),
        ("personal_use_only", "Personal use only (no redistribution)"),
        ("cc_by", "Creative Commons - Attribution (CC BY)"),
        ("cc_by_nc", "Creative Commons - Attribution-NonCommercial (CC BY-NC)"),
    ]
    
    seller = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="documents",
        db_index=True  # Performance index
    )
    category = models.ForeignKey(
        Category,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="documents",
        db_index=True  # Performance index
    )
    title = models.CharField(max_length=255)
    slug = models.SlugField(unique=True, blank=True)
    description = models.TextField()
    preview_text = models.TextField(blank=True, null=True)  # first few paragraphs
    file = models.FileField(upload_to='documents/', max_length=500)  # stored locally
    price = models.DecimalField(max_digits=8, decimal_places=2)
    pages = models.PositiveIntegerField(blank=True, null=True)  # number of pages
    
    # Enhanced categorization fields
    document_type = models.CharField(
        max_length=20,
        choices=DOCUMENT_TYPES,
        default='other',
        help_text='Type of document for better searchability'
    )
    academic_level = models.CharField(
        max_length=20,
        choices=ACADEMIC_LEVELS,
        default='other',
        help_text='Academic level this document is suitable for'
    )
    subject = models.CharField(
        max_length=100,
        blank=True,
        help_text='Subject area (e.g., Mathematics, Biology, History)'
    )
    course_code = models.CharField(
        max_length=20,
        blank=True,
        help_text='Course code (e.g., MATH101, BIO202)'
    )
    isbn = models.CharField(
        max_length=20,
        blank=True,
        help_text='ISBN for textbooks or reference materials'
    )
    author = models.CharField(
        max_length=100,
        blank=True,
        help_text='Author or professor name'
    )
    university = models.CharField(
        max_length=100,
        blank=True,
        help_text='University or institution'
    )
    year = models.PositiveIntegerField(
        blank=True,
        null=True,
        help_text='Academic year or publication year'
    )
    tags = models.TextField(
        blank=True,
        help_text='Comma-separated tags for better searchability'
    )

    license_type = models.CharField(
        max_length=40,
        choices=LICENSE_CHOICES,
        default="all_rights_reserved",
        help_text="Usage rights for buyers (shown on the listing and download areas).",
    )
    license_note = models.TextField(
        blank=True,
        help_text="Optional extra terms (e.g., 'One-device only', 'No sharing', 'For personal study').",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        indexes = [
            models.Index(fields=['seller', 'created_at']),
            models.Index(fields=['category', 'created_at']),
            models.Index(fields=['price']),
            models.Index(fields=['document_type', 'academic_level']),
            models.Index(fields=['subject', 'course_code']),
            models.Index(fields=['tags']),
            models.Index(fields=['title']),
        ]

    def save(self, *args, **kwargs):
        if not self.slug:
            base_slug = slugify(self.title) or "document"
            slug = base_slug
            suffix = 2
            while Document.objects.filter(slug=slug).exclude(pk=self.pk).exists():
                slug = f"{base_slug}-{suffix}"
                suffix += 1
            self.slug = slug
        super().save(*args, **kwargs)

    def __str__(self):
        return self.title

    @property
    def license_summary(self):
        """
        A short, buyer-friendly summary for display in templates.
        """
        if self.license_note:
            return self.license_note

        if self.license_type == "cc_by":
            return "You may share/adapt with attribution to the author."
        if self.license_type == "cc_by_nc":
            return "You may share/adapt with attribution for non-commercial use only."
        if self.license_type == "personal_use_only":
            return "For personal use only. No redistribution or resale."
        return "All rights reserved. For personal use only. No redistribution or resale."


class Order(models.Model):
    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("paid", "Paid"),
        ("cancelled", "Cancelled"),
        ("refunded", "Refunded"),
    ]

    PAYMENT_METHODS = [
        ("stripe", "Stripe (Card)"),
        ("paypal", "PayPal"),
        ("bank", "Direct Bank Transfer"),
    ]

    CURRENCY_CHOICES = [
        ("usd", "USD ($)"),
        ("eur", "EUR (€)"),
        ("gbp", "GBP (£)"),
    ]

    buyer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="orders",
        db_index=True  # Performance index
    )
    document = models.ForeignKey(
        Document,
        on_delete=models.CASCADE,
        related_name="orders",
        db_index=True  # Performance index
    )
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending", db_index=True)
    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHODS, default="stripe")
    currency = models.CharField(max_length=10, choices=CURRENCY_CHOICES, default="usd")

    # Payment tracking
    stripe_payment_intent = models.CharField(max_length=255, blank=True, null=True)
    paypal_payment_id = models.CharField(max_length=255, blank=True, null=True)

    amount_paid = models.DecimalField(max_digits=8, decimal_places=2, default=0.00)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Order #{self.id} - {self.document.title} ({self.status})"

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=['buyer', 'status']),
            models.Index(fields=['document', 'status']),
            models.Index(fields=['created_at']),
            models.Index(fields=['status', 'created_at']),
        ]


class RefundRequest(models.Model):
    STATUS_CHOICES = [
        ("open", "Open"),
        ("admin_review", "Admin Review"),
        ("approved", "Approved"),
        ("rejected", "Rejected"),
        ("refunded", "Refunded"),
    ]

    REASON_CHOICES = [
        ("not_as_described", "Not as described"),
        ("wrong_level", "Wrong academic level"),
        ("corrupt_file", "File is corrupt / won't open"),
        ("duplicate", "Duplicate / already owned"),
        ("other", "Other"),
    ]

    order = models.OneToOneField(
        Order,
        on_delete=models.CASCADE,
        related_name="refund_request",
        db_index=True,
    )
    buyer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="refund_requests",
        db_index=True,
    )

    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="open", db_index=True)
    reason = models.CharField(max_length=30, choices=REASON_CHOICES)
    details = models.TextField(blank=True)

    # Manual PayPal refund reconciliation (entered by admin once refunded).
    paypal_refund_id = models.CharField(max_length=255, blank=True, null=True)
    admin_notes = models.TextField(blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)
    resolved_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["status", "created_at"]),
            models.Index(fields=["buyer", "created_at"]),
        ]

    def __str__(self):
        return f"RefundRequest #{self.id} - Order #{self.order_id} ({self.status})"
