from django.db import models
from django.conf import settings
from django.core.validators import MinValueValidator
from decimal import Decimal
from documents.models import Document, Order


class Sale(models.Model):
    order = models.OneToOneField(Order, on_delete=models.CASCADE, related_name="sale")
    seller = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="sales")
    buyer = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="purchases")
    document = models.ForeignKey(Document, on_delete=models.CASCADE, related_name="sales")
    
    # Financial details
    gross_amount = models.DecimalField(
        max_digits=10, 
        decimal_places=2,
        default=Decimal('0.00'),
        help_text="Total amount paid by buyer"
    )
    commission_rate = models.DecimalField(
        max_digits=5, 
        decimal_places=4, 
        default=Decimal('0.4000'),
        help_text="Commission rate (40% = 0.4000)"
    )
    commission_amount = models.DecimalField(
        max_digits=10, 
        decimal_places=2,
        default=Decimal('0.00'),
        help_text="Amount deducted for site maintenance"
    )
    net_amount = models.DecimalField(
        max_digits=10, 
        decimal_places=2,
        default=Decimal('0.00'),
        help_text="Amount credited to seller after commission"
    )

    # Earnings hold/release (used to enforce a holding period before funds become withdrawable)
    wallet_released_at = models.DateTimeField(null=True, blank=True)
     
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=['seller', 'created_at']),
            models.Index(fields=['created_at']),
        ]

    def __str__(self):
        return f"{self.document.title} sold to {self.buyer.username} for ${self.gross_amount}"
    
    def save(self, *args, **kwargs):
        gross = Decimal(str(self.gross_amount)) if not isinstance(self.gross_amount, Decimal) else self.gross_amount
        rate = Decimal(str(self.commission_rate)) if not isinstance(self.commission_rate, Decimal) else self.commission_rate

        self.commission_amount = (gross * rate).quantize(Decimal("0.01"))
        self.net_amount = (gross - self.commission_amount).quantize(Decimal("0.01"))
        super().save(*args, **kwargs)


class Wallet(models.Model):
    """Seller wallet for managing earnings and withdrawals"""
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="wallet"
    )
    balance = models.DecimalField(
        max_digits=12, 
        decimal_places=2, 
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00'))],
        help_text="Available balance for withdrawal"
    )
    pending_balance = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00'))],
        help_text="Earnings on hold (not yet withdrawable)"
    )
    reserved_balance = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00'))],
        help_text="Amount reserved for pending withdrawals"
    )
    debt_balance = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal("0.00"),
        validators=[MinValueValidator(Decimal("0.00"))],
        help_text="Outstanding amount owed to platform due to refunds after payout (deducted from future earnings).",
    )
    total_earned = models.DecimalField(
        max_digits=12, 
        decimal_places=2, 
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00'))],
        help_text="Total earnings after commission"
    )
    total_commission_paid = models.DecimalField(
        max_digits=12, 
        decimal_places=2, 
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00'))],
        help_text="Total commission paid to platform"
    )
    total_withdrawn = models.DecimalField(
        max_digits=12, 
        decimal_places=2, 
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00'))],
        help_text="Total amount withdrawn"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        indexes = [
            models.Index(fields=['user']),
            models.Index(fields=['created_at']),
        ]
    
    def __str__(self):
        return f"{self.user.username}'s Wallet - ${self.balance}"
    
    def add_earnings(self, amount, commission_amount, sale=None):
        """Add earnings after commission deduction"""
        repay = min(Decimal(amount), Decimal(self.debt_balance or 0))
        remaining = Decimal(amount) - repay
        if repay > 0:
            self.debt_balance = max(Decimal("0.00"), Decimal(self.debt_balance) - repay)
        if remaining > 0:
            self.balance += remaining

        self.total_earned += amount
        self.total_commission_paid += commission_amount
        self.save(update_fields=["balance", "debt_balance", "total_earned", "total_commission_paid", "updated_at"])
        
        # Create transaction record
        Transaction.objects.create(
            wallet=self,
            amount=amount,
            transaction_type='sale',
            description=f'Sale earnings (40% platform commission: ${commission_amount})',
            commission_amount=commission_amount,
            gross_amount=amount + commission_amount,
            sale=sale
        )

        if repay > 0:
            Transaction.objects.create(
                wallet=self,
                amount=-repay,
                transaction_type="fee",
                description="Offset applied to repay refund debt",
                commission_amount=Decimal("0.00"),
                transaction_fee=Decimal("0.00"),
                net_amount=-repay,
            )
        
        return amount, commission_amount

    def add_pending_earnings(self, amount, commission_amount):
        """Add earnings to pending balance (held funds)."""
        self.pending_balance += amount
        self.total_commission_paid += commission_amount
        self.save(update_fields=["pending_balance", "total_commission_paid"])

    def release_pending_earnings(self, amount, commission_amount, sale=None):
        """Move held earnings into available balance."""
        self.pending_balance = max(Decimal("0.00"), self.pending_balance - amount)

        repay = min(Decimal(amount), Decimal(self.debt_balance or 0))
        remaining = Decimal(amount) - repay
        if repay > 0:
            self.debt_balance = max(Decimal("0.00"), Decimal(self.debt_balance) - repay)

        if remaining > 0:
            self.balance += remaining

        self.total_earned += amount
        self.save(update_fields=["pending_balance", "balance", "total_earned", "debt_balance"])

        Transaction.objects.create(
            wallet=self,
            amount=amount,
            transaction_type='sale',
            description=f'Sale earnings released (40% platform commission: ${commission_amount})',
            commission_amount=commission_amount,
            gross_amount=amount + commission_amount,
            sale=sale
        )

        if repay > 0:
            Transaction.objects.create(
                wallet=self,
                amount=-repay,
                transaction_type="fee",
                description="Offset applied to repay refund debt",
                commission_amount=Decimal("0.00"),
                transaction_fee=Decimal("0.00"),
                net_amount=-repay,
            )

        return amount, commission_amount

    def refund_withdrawal(self, amount, reason="Withdrawal refunded"):
        """Refund a previously debited withdrawal back into the wallet."""
        self.balance += amount
        self.total_withdrawn = max(Decimal("0.00"), self.total_withdrawn - amount)
        self.save(update_fields=["balance", "total_withdrawn"])

        Transaction.objects.create(
            wallet=self,
            amount=amount,
            transaction_type='refund',
            description=reason,
            commission_amount=Decimal('0.00'),
            transaction_fee=Decimal('0.00'),
            net_amount=amount,
        )

    def reserve_withdrawal(self, amount, reason="Withdrawal reserved"):
        """Reserve funds for a withdrawal without marking it as withdrawn yet."""
        if Decimal(str(getattr(self, "debt_balance", 0) or 0)) > 0:
            raise ValueError("Withdrawals are disabled until refund debt is repaid")
        if amount > self.balance:
            raise ValueError("Insufficient balance")

        self.balance -= amount
        self.reserved_balance += amount
        self.save(update_fields=["balance", "reserved_balance"])

        Transaction.objects.create(
            wallet=self,
            amount=-amount,
            transaction_type="withdrawal",
            description=reason,
            commission_amount=Decimal("0.00"),
            transaction_fee=Decimal("0.00"),
            net_amount=-amount,
        )

    def finalize_reserved_withdrawal(self, amount):
        """Mark a reserved withdrawal as completed (moves reserved -> withdrawn)."""
        self.reserved_balance = max(Decimal("0.00"), self.reserved_balance - amount)
        self.total_withdrawn += amount
        self.save(update_fields=["reserved_balance", "total_withdrawn"])

    def release_reserved_withdrawal(self, amount, reason="Withdrawal released"):
        """Release reserved funds back to available balance."""
        self.reserved_balance = max(Decimal("0.00"), self.reserved_balance - amount)
        self.balance += amount
        self.save(update_fields=["reserved_balance", "balance"])

        Transaction.objects.create(
            wallet=self,
            amount=amount,
            transaction_type="refund",
            description=reason,
            commission_amount=Decimal("0.00"),
            transaction_fee=Decimal("0.00"),
            net_amount=amount,
        )
    
    def withdraw(self, amount, reason='Withdrawal', transaction_fee=Decimal('0.00')):
        """Process withdrawal with validation"""
        if Decimal(str(getattr(self, "debt_balance", 0) or 0)) > 0:
            raise ValueError("Withdrawals are disabled until refund debt is repaid")
        if amount > self.balance:
            raise ValueError("Insufficient balance")
        
        # No commission on withdrawals - commission already taken from sales
        # Only charge transaction fee
        net_amount = amount - transaction_fee
        description = reason if transaction_fee == Decimal("0.00") else f'{reason} (Transaction fee: ${transaction_fee})'
        
        self.balance -= amount
        self.total_withdrawn += amount
        self.save()
        
        # Create transaction record
        Transaction.objects.create(
            wallet=self,
            amount=-amount,
            transaction_type='withdrawal',
            description=description,
            commission_amount=Decimal('0.00'),  # No commission on withdrawals
            transaction_fee=transaction_fee,
            net_amount=net_amount
        )
        
        return net_amount, Decimal('0.00'), transaction_fee


class Transaction(models.Model):
    """Transaction history for wallet operations"""
    TRANSACTION_TYPES = [
        ('sale', 'Sale Earnings'),
        ('withdrawal', 'Withdrawal'),
        ('refund', 'Refund'),
        ('bonus', 'Bonus'),
        ('fee', 'Transaction Fee'),
    ]
    
    wallet = models.ForeignKey(
        Wallet,
        on_delete=models.CASCADE,
        related_name="transactions"
    )
    amount = models.DecimalField(
        max_digits=12, 
        decimal_places=2,
        help_text="Gross amount (positive for credits, negative for debits)"
    )
    net_amount = models.DecimalField(
        max_digits=12, 
        decimal_places=2, 
        null=True, 
        blank=True,
        help_text="Net amount after commission and fees"
    )
    commission_amount = models.DecimalField(
        max_digits=12, 
        decimal_places=2, 
        default=Decimal('0.00'),
        help_text="Commission/fee amount"
    )
    transaction_fee = models.DecimalField(
        max_digits=12, 
        decimal_places=2, 
        default=Decimal('0.00'),
        help_text="Transaction processing fee"
    )
    gross_amount = models.DecimalField(
        max_digits=12, 
        decimal_places=2, 
        null=True, 
        blank=True,
        help_text="Gross sale amount before commission"
    )
    transaction_type = models.CharField(
        max_length=20, 
        choices=TRANSACTION_TYPES
    )
    description = models.TextField()
    sale = models.ForeignKey(
        'Sale',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="transactions"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=['wallet', 'created_at']),
            models.Index(fields=['transaction_type', 'created_at']),
        ]
    
    def __str__(self):
        return f"{self.wallet.user.username} - {self.transaction_type} - ${abs(self.amount)}"


