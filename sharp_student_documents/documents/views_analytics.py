from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.admin.views.decorators import staff_member_required
from django.http import JsonResponse
from django.db.models import Count, Sum, Avg
from django.utils import timezone
from datetime import timedelta, datetime
import json

from .models import Document
from .analytics import get_seller_analytics, get_marketplace_stats, get_popular_categories, get_trending_subjects
from reviews.models import Review
from sales.models import Sale
from sharp_student_documents.models import DownloadLog

@login_required
def seller_analytics(request):
    """
    Comprehensive seller analytics dashboard
    """
    if not request.user.is_seller:
        return redirect('home')
    
    period = request.GET.get("period", 30)
    try:
        period = int(period)
    except (TypeError, ValueError):
        period = 30

    period_options = [7, 30, 90, 365]
    if period not in period_options:
        period = 30

    # Get analytics data
    analytics = get_seller_analytics(request.user, days=period)

    monthly_sales_list = []
    for item in analytics["monthly_sales"]:
        month_value = item.get("month")
        month_label = month_value.strftime("%b %Y") if month_value else ""
        monthly_sales_list.append(
            {
                "month": month_label,
                "sales_count": int(item.get("sales_count") or 0),
                "revenue": float(item.get("revenue") or 0),
                "avg_price": float(item.get("avg_price") or 0),
            }
        )
    
    # Get wallet info
    from sales.models import Wallet
    wallet, created = Wallet.objects.get_or_create(user=request.user)
    lifetime_net_earned = wallet.balance + wallet.pending_balance + wallet.reserved_balance + wallet.total_withdrawn
    
    context = {
        'analytics': analytics,
        'sales_chart_data': json.dumps(monthly_sales_list),
        'wallet_balance': wallet.balance,
        'total_earned': lifetime_net_earned,
        'total_withdrawn': wallet.total_withdrawn,
        'period_options': period_options,
        'current_period': period,
    }
    
    return render(request, 'documents/seller_analytics.html', context)

@staff_member_required
def marketplace_analytics(request):
    """
    Admin marketplace analytics dashboard
    """
    marketplace_stats = get_marketplace_stats()
    popular_categories = get_popular_categories()
    trending_subjects = get_trending_subjects()
    
    # Get growth data
    growth_data = []
    for days in [7, 30, 90, 365]:
        stats = get_marketplace_stats(days=days)
        growth_data.append({
            'period': f'{days} days',
            'new_users': stats['new_users'],
            'total_users': stats['total_users'],
            'active_sellers': stats['active_sellers'],
            'total_sales': stats['total_sales'],
            'total_revenue': stats['total_revenue'],
        })
    
    context = {
        'marketplace_stats': marketplace_stats,
        'popular_categories': popular_categories,
        'trending_subjects': trending_subjects,
        'growth_data': growth_data,
    }
    
    return render(request, 'documents/marketplace_analytics.html', context)

@login_required
def document_performance(request, document_id):
    """
    Individual document performance metrics
    """
    document = get_object_or_404(Document, id=document_id, seller=request.user)
    
    # Performance data
    end_date = timezone.now()
    start_date = end_date - timedelta(days=30)
    
    downloads = DownloadLog.objects.filter(
        document=document,
        created_at__gte=start_date
    ).select_related('user').order_by('-created_at')
    
    # Sales data
    sales = Sale.objects.filter(document=document).select_related('buyer')
    reviews = Review.objects.filter(document=document).select_related('reviewer')
    
    # Conversion funnel
    views_count = DownloadLog.objects.filter(document=document).count()
    downloads_count = downloads.count()
    sales_count = sales.count()
    conversion_rate = (sales_count / views_count * 100) if views_count > 0 else 0
    
    context = {
        'document': document,
        'views_count': views_count,
        'downloads_count': downloads_count,
        'sales_count': sales_count,
        'conversion_rate': round(conversion_rate, 2),
        'revenue': sales.aggregate(total=Sum('net_amount'))['total'] or 0,
        'avg_rating': reviews.aggregate(avg_rating=Avg('rating'))['avg_rating'] or 0,
        'recent_downloads': downloads[:10],
        'recent_sales': sales[:10],
        'reviews': reviews[:10],
    }
    
    return render(request, 'documents/document_performance.html', context)

@login_required
def analytics_api(request):
    """
    API endpoint for real-time analytics data
    """
    period = request.GET.get('period', 30)
    try:
        period = int(period)
    except ValueError:
        period = 30
    
    if request.user.is_seller:
        analytics = get_seller_analytics(request.user, days=period)

        monthly_sales_list = []
        for item in analytics["monthly_sales"]:
            month_value = item.get("month")
            month_label = month_value.strftime("%Y-%m") if month_value else ""
            monthly_sales_list.append(
                {
                    "month": month_label,
                    "sales_count": int(item.get("sales_count") or 0),
                    "revenue": float(item.get("revenue") or 0),
                    "avg_price": float(item.get("avg_price") or 0),
                }
            )

        return JsonResponse({
            'status': 'success',
            'data': {
                'total_revenue': float(analytics['total_revenue']),
                'total_sales': analytics['total_sales'],
                'total_downloads': analytics['total_downloads'],
                'conversion_rate': analytics['conversion_rate'],
                'monthly_sales': monthly_sales_list,
                'top_documents': [
                    {
                        'title': doc.title,
                        'downloads': doc.downloads_count,
                        'revenue': float(doc.revenue or 0),
                        'sales_count': int(doc.sales_count or 0),
                    }
                    for doc in analytics['top_documents']
                ]
            }
        })
    else:
        return JsonResponse({'status': 'error', 'message': 'Unauthorized'}, status=401)

@staff_member_required
def marketplace_analytics_api(request):
    """
    API endpoint for marketplace analytics
    """
    marketplace_stats = get_marketplace_stats()
    
    return JsonResponse({
        'status': 'success',
        'data': {
            'total_documents': marketplace_stats['total_documents'],
            'total_users': marketplace_stats['total_users'],
            'active_sellers': marketplace_stats['active_sellers'],
            'total_sales': marketplace_stats['total_sales'],
            'total_revenue': float(marketplace_stats['total_revenue']),
            'avg_rating': float(marketplace_stats['avg_rating']),
            'popular_categories': list(get_popular_categories()),
            'trending_subjects': list(get_trending_subjects()),
        }
    })
