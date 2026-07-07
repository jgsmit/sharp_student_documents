# payments/signals.py
import logging
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.db import transaction
from decimal import Decimal
from .models import Payment
from documents.models import Order
from sales.models import Sale

logger = logging.getLogger(__name__)

@receiver(post_save, sender=Payment)
def create_sale_on_payment_success(sender, instance, created, **kwargs):
    """
    Automatically create a Sale record when a payment is marked as successful
    to ensure financial data consistency across all apps.
    """
    if instance.status == 'success' and instance.order:
        # Check if Sale already exists for this order
        if not hasattr(instance.order, 'sale'):
            try:
                with transaction.atomic():
                    # Create Sale record
                    Sale.objects.create(
                        order=instance.order,
                        seller=instance.order.document.seller,
                        buyer=instance.order.buyer,
                        document=instance.order.document,
                        gross_amount=instance.amount,
                        commission_rate=Decimal('0.4000'),  # 40% platform commission
                    )
                    logger.info("Created Sale record for Order %s", instance.order.id)
            except Exception:
                logger.exception("Error creating Sale record for Order %s", instance.order.id)


@receiver(post_save, sender=Payment)
def update_order_on_payment_change(sender, instance, **kwargs):
    """
    Update order status based on payment status to maintain consistency
    """
    if instance.order:
        if instance.status == 'success':
            instance.order.status = 'paid'
            # Ensure amount_paid is set so seller dashboards can compute revenue correctly.
            if not getattr(instance.order, "amount_paid", None) or instance.order.amount_paid == 0:
                instance.order.amount_paid = instance.amount
            instance.order.save()
            logger.info("Updated Order %s status to paid", instance.order.id)
        elif instance.status == 'failed':
            instance.order.status = 'cancelled'
            instance.order.save()
            logger.info("Updated Order %s status to cancelled", instance.order.id)
