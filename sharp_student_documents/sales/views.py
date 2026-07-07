from django.contrib.auth.decorators import login_required
from django.contrib.admin.views.decorators import staff_member_required
from django.shortcuts import render, redirect
from django.contrib import messages
from django.views.decorators.http import require_http_methods
from django.db.models import Sum, Count
from django.db.models.functions import TruncMonth
from django.core.paginator import Paginator
from django.http import HttpResponse
import csv

from .models import Sale, Wallet, Transaction
from .utils import create_or_get_wallet

@login_required
def seller_dashboard(request):
    """
    Legacy seller dashboard (sales app).

    The project uses the unified dashboards under the `documents` app and the unified
    withdrawal system under the `withdrawals` app.
    """
    return redirect("documents:seller_dashboard")


@login_required
def sales_history(request):
    sales = Sale.objects.filter(seller=request.user).select_related("buyer", "document")

    total_sales = sales.count()
    total_earnings = sales.aggregate(total=Sum("net_amount"))["total"] or 0
    total_commission = sales.aggregate(total=Sum("commission_amount"))["total"] or 0

    # Group sales by month
    monthly_sales = (
        sales.annotate(month=TruncMonth("created_at"))
        .values("month")
        .annotate(
            sales_count=Count("id"),
            earnings=Sum("net_amount"),
            commission=Sum("commission_amount"),
            gross_sales=Sum("gross_amount")
        )
        .order_by("month")
    )

    return render(request, "sales/sales_history.html", {
        "sales": sales,
        "total_sales": total_sales,
        "total_earnings": total_earnings,
        "total_commission": total_commission,
        "commission_rate": "40%",
        "monthly_sales": monthly_sales,
    })


@login_required
def export_sales_csv(request):
    sales = Sale.objects.filter(seller=request.user).select_related("buyer", "document")

    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = 'attachment; filename="sales_report.csv"'

    writer = csv.writer(response)
    writer.writerow([
        "Date", "Document", "Buyer", "Gross Amount", 
        "Platform Commission (40%)", "Seller Earnings (60%)"
    ])

    for sale in sales:
        writer.writerow([
            sale.created_at.strftime("%Y-%m-%d %H:%M"),
            sale.document.title,
            sale.buyer.username,
            f"{sale.gross_amount:.2f}",
            f"{sale.commission_amount:.2f}",
            f"{sale.net_amount:.2f}"
        ])

    return response


@login_required
@require_http_methods(["GET", "POST"])
def request_withdrawal(request):
    """Legacy withdrawal endpoint (sales app). Redirect to unified withdrawals app."""
    return redirect("withdrawals:request")


@login_required
def transaction_history(request):
    """View transaction history"""
    wallet = create_or_get_wallet(request.user)
    
    transactions = Transaction.objects.filter(
        wallet=wallet
    ).order_by('-created_at')
    
    # Pagination
    paginator = Paginator(transactions, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    return render(request, 'sales/transaction_history.html', {
        'transactions': page_obj,
        'wallet': wallet,
    })


# Admin views for managing withdrawals
@staff_member_required
def manage_withdrawals(request):
    """Legacy admin withdrawal manager (sales app). Redirect to unified admin view."""
    return redirect("documents:admin_manage_withdrawals")


@staff_member_required
def approve_withdrawal(request, request_id):
    """Legacy sales withdrawal approval. Redirect to unified admin view."""
    messages.info(request, "This withdrawal system is deprecated. Use the unified withdrawals manager.")
    return redirect("documents:admin_manage_withdrawals")
