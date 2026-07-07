import logging

from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import Sale
from .utils import create_or_get_wallet

logger = logging.getLogger(__name__)


@receiver(post_save, sender=Sale)
def credit_wallet_on_sale_create(sender, instance: Sale, created: bool, **kwargs):
    if not created:
        return

    try:
        wallet = create_or_get_wallet(instance.seller)
        wallet.add_pending_earnings(instance.net_amount, instance.commission_amount)
    except Exception:
        logger.exception("Failed to credit wallet for sale %s", instance.id)
