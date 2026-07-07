# documents/financial_utils.py
"""
Unified financial reporting utilities for consistency across all dashboards
"""
from django.db.models import Sum, Count, F, Q
from django.db.models.functions import Coalesce
from decimal import Decimal
from documents.models import Order, Document
from sales.models import Wallet, Sale
from withdrawals.models import WithdrawalRequest as WithdrawalsAppWithdrawal
from payments.models import Payment
from django.conf import settings


def get_unified_financial_data(user=None, is_admin=False):
    """
    Get standardized financial data for both seller and admin dashboards
    
    Args:
        user: User object (for seller dashboard) or None (for admin dashboard)
        is_admin: Boolean flag for admin dashboard calculations
    
    Returns:
        dict: Standardized financial data
    """
    
    if is_admin:
        # Admin dashboard - system-wide financial data
        paid_orders = Order.objects.filter(status='paid')
        pending_orders = Order.objects.filter(status='pending')
        
        # Revenue calculations using amount_paid for consistency
        total_revenue = paid_orders.aggregate(
            total=Sum('amount_paid')
        )['total'] or 0
        
        pending_revenue = pending_orders.aggregate(
            total=Sum('amount_paid')
        )['total'] or 0
        
        # Order statistics
        total_orders = Order.objects.count()
        completed_orders = paid_orders.count()
        pending_orders_count = pending_orders.count()
        
        # Withdrawal data (single source of truth: withdrawals app)
        total_withdrawn = WithdrawalsAppWithdrawal.objects.filter(status='completed').aggregate(
            total=Sum('amount')
        )['total'] or 0
        
        # Payment statistics - use Order data if no Payment records exist
        payment_count = Payment.objects.count()
        if payment_count > 0:
            successful_payments = Payment.objects.filter(status='success').aggregate(
                total=Sum('amount')
            )['total'] or 0
        else:
            # Fallback to Order data if no Payment records
            successful_payments = total_revenue
        
        return {
            'total_revenue': total_revenue,
            'pending_revenue': pending_revenue,
            'total_orders': total_orders,
            'completed_orders': completed_orders,
            'pending_orders': pending_orders_count,
            'total_withdrawn': total_withdrawn,
            'net_profit': total_revenue - total_withdrawn,
            'successful_payments': successful_payments,
            'order_completion_rate': (completed_orders / total_orders * 100) if total_orders > 0 else 0,
            'platform_commission_rate': getattr(settings, "PLATFORM_COMMISSION_RATE", Decimal("0.40")),
            'seller_share': getattr(settings, "SELLER_SHARE", Decimal("0.60")),
            'total_commission': Sale.objects.aggregate(total=Sum('commission_amount'))['total'] or 0,
            'total_earnings': Sale.objects.aggregate(total=Sum('net_amount'))['total'] or 0,
        }
    
    else:
        # Seller dashboard - user-specific financial data
        if not user:
            return {}
        
        paid_orders = Order.objects.filter(document__seller=user, status='paid')
        pending_orders = Order.objects.filter(document__seller=user, status='pending')

        total_gross_sales = paid_orders.aggregate(total=Sum("amount_paid"))["total"] or 0
        
        # Earnings should reflect seller share (net), not gross buyer payments.
        total_earnings = Sale.objects.filter(seller=user).aggregate(
            earnings=Sum('net_amount')
        )['earnings'] or 0
        
        pending_earnings = pending_orders.aggregate(pending=Sum('amount_paid'))['pending'] or 0
        
        # Sales statistics
        total_sales = paid_orders.count()
        pending_sales = pending_orders.count()
        
        # Wallet data from sales app - use actual wallet values for consistency
        wallet_data = {}
        try:
            from sales.utils import create_or_get_wallet
            wallet = create_or_get_wallet(user)
             
            lifetime_net_earned = (
                wallet.balance
                + wallet.pending_balance
                + wallet.reserved_balance
                + wallet.total_withdrawn
            )
            unrequested_balance = wallet.balance + wallet.pending_balance

            wallet_data = {
                'balance': wallet.balance,  # Use actual wallet balance
                # Lifetime net earnings (includes held + withdrawn).
                'total_earned': lifetime_net_earned,
                # Released net earnings only (excludes held funds).
                'released_earned': wallet.total_earned,
                'pending_balance': wallet.pending_balance,
                'reserved_balance': wallet.reserved_balance,
                # Money not yet requested for withdrawal (available + held).
                'unrequested_balance': unrequested_balance,
                'total_commission_paid': wallet.total_commission_paid,  # Use actual wallet commission
                'total_withdrawn': wallet.total_withdrawn,  # Use actual wallet withdrawals
            }
                 
        except Exception as e:
            print(f"Error getting wallet for {user.username}: {e}")
            # Fallback to calculated values if wallet fails
            commission_rate = getattr(settings, "PLATFORM_COMMISSION_RATE", Decimal("0.40"))
            order_based_commission = total_earnings * commission_rate
            wallet_data = {
                'balance': total_earnings - order_based_commission,
                'total_earned': total_earnings,
                'released_earned': total_earnings,
                'pending_balance': Decimal("0.00"),
                'reserved_balance': Decimal("0.00"),
                'unrequested_balance': total_earnings,
                'total_commission_paid': order_based_commission,
                'total_withdrawn': 0,
            }
        
        # Recent sales data - use Order data for consistency with admin dashboard
        recent_sales = []
        total_sales_amount = 0
        total_commission_amount = 0
        
        try:
            # Get recent orders for this seller and convert to sale-like format
            recent_orders = Order.objects.filter(
                document__seller=user, 
                status='paid'
            ).order_by("-created_at")[:10]
            
            for order in recent_orders:
                commission_rate = getattr(settings, "PLATFORM_COMMISSION_RATE", Decimal("0.40"))
                commission = order.amount_paid * commission_rate
                net_amount = order.amount_paid - commission
                
                recent_sales.append({
                    'document': order.document,
                    'buyer': order.buyer,
                    'gross_amount': order.amount_paid,
                    'commission_amount': commission,
                    'net_amount': net_amount,
                    'created_at': order.created_at,
                    'order': order
                })
                
                total_sales_amount += net_amount
                total_commission_amount += commission
                
        except Exception as e:
            print(f"Error calculating recent sales for {user.username}: {e}")
            recent_sales = []
            total_sales_amount = 0
            total_commission_amount = 0
        
        # Withdrawal requests (single source of truth: withdrawals app)
        try:
            withdrawal_requests = list(
                WithdrawalsAppWithdrawal.objects.filter(user=user).order_by("-requested_at")
            )
        except Exception as e:
            print(f"Error fetching withdrawals for {user.username}: {e}")
            withdrawal_requests = []
        
        pending_withdrawals = [
            w for w in withdrawal_requests if getattr(w, 'status', None) in ['pending', 'processing']
        ]
        failed_withdrawals = [
            w
            for w in withdrawal_requests
            if getattr(w, "status", None) in ["failed", "rejected", "cancelled"]
        ]
         
        return {
            'total_gross_sales': total_gross_sales,
            'total_earnings': total_earnings,
            'pending_earnings': pending_earnings,
            'total_sales': total_sales,
            'pending_sales': pending_sales,
            'wallet': wallet_data,
            'recent_sales': recent_sales,
            'total_sales_amount': total_sales_amount,
            'total_commission_amount': total_commission_amount,
            'withdrawal_requests': withdrawal_requests,
            'pending_withdrawals': pending_withdrawals,
            'failed_withdrawals': failed_withdrawals,
        }


def debug_financial_data():
    """
    Debug function to identify financial discrepancies between dashboards
    """
    print("DEBUGGING FINANCIAL DATA DISCREPANCIES")
    print("=" * 50)
    
    # Admin dashboard totals
    admin_paid_orders = Order.objects.filter(status='paid')
    admin_total_revenue = admin_paid_orders.aggregate(
        total=Sum('amount_paid')
    )['total'] or 0
    
    print(f"Admin Dashboard Data:")
    print(f"   Total Revenue (Orders): ${admin_total_revenue:,.2f}")
    print(f"   Paid Orders Count: {admin_paid_orders.count()}")
    
    # Seller dashboard totals (sum of all sellers)
    try:
        from accounts.models import CustomUser
        all_sellers = CustomUser.objects.filter(is_seller=True)
    except:
        all_sellers = []
    
    seller_total_earnings = 0
    
    for seller in all_sellers:
        seller_earnings = Order.objects.filter(
            document__seller=seller, status='paid'
        ).aggregate(earnings=Sum('amount_paid'))['earnings'] or 0
        seller_total_earnings += seller_earnings
    
    print(f"\nSeller Dashboard Data:")
    print(f"   Total Seller Earnings: ${seller_total_earnings:,.2f}")
    
    # Check for discrepancy
    discrepancy = abs(admin_total_revenue - seller_total_earnings)
    if discrepancy > 0.01:  # Allow for small rounding differences
        print(f"\nDISCREPANCY DETECTED: ${discrepancy:,.2f}")
        print(f"   Admin shows: ${admin_total_revenue:,.2f}")
        print(f"   Sellers show: ${seller_total_earnings:,.2f}")
    else:
        print(f"\nFINANCIAL DATA MATCHES!")
    
    print("=" * 50)
    return {
        'admin_revenue': admin_total_revenue,
        'seller_earnings': seller_total_earnings,
        'discrepancy': discrepancy
    }


def synchronize_financial_data():
    """
    Synchronize financial data across all apps to ensure consistency
    This function can be called periodically or as needed
    """
    print("Starting financial data synchronization...")
    
    # Create missing Sale records for successful payments
    successful_payments = Payment.objects.filter(status='success').select_related('order')
    for payment in successful_payments:
        if payment.order and not hasattr(payment.order, 'sale'):
            try:
                Sale.objects.get_or_create(
                    order=payment.order,
                    defaults={
                        'seller': payment.order.document.seller,
                        'buyer': payment.order.buyer,
                        'document': payment.order.document,
                        'gross_amount': payment.amount,
                        'commission_rate': Decimal('0.4000'),  # 40% platform commission
                    }
                )
                print(f"Created missing Sale for Order {payment.order.id}")
            except Exception as e:
                print(f"Error creating Sale for Order {payment.order.id}: {e}")
    
    print("Financial data synchronization completed")
    return True
