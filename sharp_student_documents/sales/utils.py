from decimal import Decimal
from django.db import transaction
from django.conf import settings
from .models import Wallet, Sale, Transaction
from django.utils import timezone
from datetime import timedelta

def create_or_get_wallet(user):
    """Create wallet for user if it doesn't exist"""
    wallet, created = Wallet.objects.get_or_create(user=user)
    return wallet

def update_seller_wallet(seller, net_amount, commission_amount, sale):
    """Update seller wallet when a sale is made"""
    wallet = create_or_get_wallet(seller)
    wallet.add_pending_earnings(net_amount, commission_amount)


def release_held_earnings_for_seller(seller, hold_days=14, now=None):
    """
    Release held earnings (sales older than hold_days) into the seller's available wallet balance.
    """
    now = now or timezone.now()
    cutoff = now - timedelta(days=hold_days)

    with transaction.atomic():
        wallet = create_or_get_wallet(seller)

        held_sales = list(
            Sale.objects.select_for_update()
            .filter(
                seller=seller,
                wallet_released_at__isnull=True,
                created_at__lte=cutoff,
                # Do not release earnings for refunded orders.
                order__status="paid",
            )
            .order_by("created_at")
        )

        if not held_sales:
            return wallet

        total_net = sum((sale.net_amount for sale in held_sales), Decimal("0.00"))

        wallet.pending_balance = max(Decimal("0.00"), wallet.pending_balance - total_net)

        repay = min(Decimal(total_net), Decimal(getattr(wallet, "debt_balance", Decimal("0.00")) or Decimal("0.00")))
        remaining = Decimal(total_net) - repay
        if repay > 0:
            wallet.debt_balance = max(Decimal("0.00"), Decimal(wallet.debt_balance) - repay)
        if remaining > 0:
            wallet.balance += remaining

        wallet.total_earned += total_net
        wallet.save(update_fields=["pending_balance", "balance", "total_earned", "debt_balance"])

        release_time = now
        for sale in held_sales:
            sale.wallet_released_at = release_time
            sale.save(update_fields=["wallet_released_at"])
            Transaction.objects.create(
                wallet=wallet,
                amount=sale.net_amount,
                transaction_type="sale",
                description=f"Sale earnings released (40% platform commission: ${sale.commission_amount})",
                commission_amount=sale.commission_amount,
                gross_amount=sale.gross_amount,
                sale=sale,
            )

        if repay > 0:
            Transaction.objects.create(
                wallet=wallet,
                amount=-repay,
                transaction_type="fee",
                description="Offset applied to repay refund debt",
                commission_amount=Decimal("0.00"),
                transaction_fee=Decimal("0.00"),
                net_amount=-repay,
            )

        return wallet

def create_sale_record(order):
    """Create sale record when order is paid"""
    with transaction.atomic():
        commission_rate = getattr(settings, "PLATFORM_COMMISSION_RATE", Decimal("0.40"))
        sale, _created = Sale.objects.get_or_create(
            order=order,
            defaults={
                "seller": order.document.seller,
                "buyer": order.buyer,
                "document": order.document,
                "gross_amount": order.amount_paid,
                "commission_rate": commission_rate,
            },
        )
        return sale

def get_seller_stats(seller):
    """Get comprehensive seller statistics"""
    wallet = create_or_get_wallet(seller)
    
    from django.db.models import Sum, Count, Avg
    from documents.models import Order
    
    sales_data = Sale.objects.filter(seller=seller).aggregate(
        total_sales=Sum('gross_amount'),
        total_earnings=Sum('net_amount'),
        total_commission=Sum('commission_amount'),
        sales_count=Count('id'),
        avg_sale_price=Avg('gross_amount')
    )
    
    orders_data = Order.objects.filter(
        document__seller=seller, 
        status='paid'
    ).aggregate(
        total_orders=Count('id'),
        total_revenue=Sum('amount_paid')
    )
    
    return {
        'wallet_balance': wallet.balance,
        'total_earned': wallet.total_earned,
        'total_commission_paid': wallet.total_commission_paid,
        'total_withdrawn': wallet.total_withdrawn,
        'sales_count': sales_data['sales_count'] or 0,
        'total_sales': sales_data['total_sales'] or Decimal('0.00'),
        'total_earnings': sales_data['total_earnings'] or Decimal('0.00'),
        'avg_sale_price': sales_data['avg_sale_price'] or Decimal('0.00'),
        'commission_rate': '40%',
        'pending_withdrawals': wallet.withdrawal_requests.filter(status='pending').count()
    }
