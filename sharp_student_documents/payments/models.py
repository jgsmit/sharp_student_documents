# payments/models.py
from django.db import models
from django.core.exceptions import ValidationError
from documents.models import Order


class Payment(models.Model):
    PAYMENT_METHODS = [
        ("stripe", "Stripe"),
        ("paypal", "PayPal"),
        ("bank", "Direct Bank Transfer"),
    ]

    STATUSES = [
        ("pending", "Pending"),
        ("success", "Success"),
        ("failed", "Failed"),
    ]

    order = models.OneToOneField(
        Order,
        on_delete=models.CASCADE,
        related_name="payment",
        db_index=True
    )
    payment_method = models.CharField(
        max_length=20,
        choices=PAYMENT_METHODS,
        db_index=True
    )
    transaction_id = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        help_text="Gateway transaction ID (Stripe PI, PayPal ID, etc.)",
        db_index=True
    )
    amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        help_text="Final amount paid"
    )
    currency = models.CharField(
        max_length=10,
        default="USD",
        help_text="Currency of the transaction"
    )
    status = models.CharField(
        max_length=20,
        choices=STATUSES,
        default="pending",
        db_index=True
    )
    failure_reason = models.TextField(
        blank=True,
        null=True,
        help_text="Reason for payment failure"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)  # ✅ keep track of changes

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=['status', 'created_at']),
            models.Index(fields=['payment_method', 'status']),
            models.Index(fields=['transaction_id']),
        ]
    
    def clean(self):
        """Validate payment data"""
        if self.amount <= 0:
            raise ValidationError("Payment amount must be greater than zero.")
        
        if self.status == 'success' and not self.transaction_id:
            raise ValidationError("Successful payments must have a transaction ID.")

    def __str__(self):
        return f"{self.payment_method} - {self.status} (${self.amount})"
    
    def mark_success(self, transaction_id):
        """Mark payment as successful"""
        self.status = 'success'
        self.transaction_id = transaction_id
        self.save()
        
        # Update order status
        if self.order:
            self.order.status = 'paid'
            if not getattr(self.order, "amount_paid", None) or self.order.amount_paid == 0:
                self.order.amount_paid = self.amount
            self.order.save()
    
    def mark_failed(self, reason):
        """Mark payment as failed"""
        self.status = 'failed'
        self.failure_reason = reason
        self.save()
        
        # Update order status
        if self.order:
            self.order.status = 'cancelled'
            self.order.save()
