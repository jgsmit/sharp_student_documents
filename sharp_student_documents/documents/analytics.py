from django.db import models
from django.db.models import Count, Sum, Avg, F, Q, Case, When
from django.db.models.functions import TruncMonth
from django.db.models import FloatField
from django.utils import timezone
from datetime import timedelta
from documents.models import Document, Order, Category
from sales.models import Sale, Wallet
from reviews.models import Review
import calendar

def get_seller_analytics(seller, days=30):
    """
    Get comprehensive analytics for a seller
    """
    end_date = timezone.now()
    start_date = end_date - timedelta(days=days)
    
    # Sales data
    sales = Sale.objects.filter(
        seller=seller,
        created_at__gte=start_date,
        created_at__lte=end_date
    ).select_related('document', 'buyer').prefetch_related('document__reviews')
    
    # Document performance
    documents = Document.objects.filter(seller=seller).annotate(
        views_count=Count('download_logs', filter=Q(download_logs__download_time__gte=start_date)),
        downloads_count=Count('download_logs', filter=Q(download_logs__download_time__gte=start_date)),
        avg_rating=Avg('reviews__rating'),
        reviews_count=Count('reviews'),
        sales_count=Count('sales', filter=Q(sales__created_at__gte=start_date, sales__created_at__lte=end_date)),
        revenue=Sum('sales__net_amount', filter=Q(sales__created_at__gte=start_date, sales__created_at__lte=end_date)),
    ).prefetch_related('reviews')
    
    # Revenue data
    total_revenue = sales.aggregate(
        total=Sum('net_amount')
    )['total'] or 0
    
    # Monthly trends
    monthly_sales = sales.annotate(
        month=TruncMonth('created_at')
    ).values('month').annotate(
        sales_count=Count('id'),
        revenue=Sum('net_amount'),
        avg_price=Avg('net_amount')
    ).order_by('month')
    
    # Top performing documents
    top_documents = documents.order_by('-downloads_count')[:10]
    
    # Popular subjects
    subject_performance = documents.values('subject').annotate(
        doc_count=Count('id'),
        total_downloads=Count('download_logs', filter=Q(download_logs__download_time__gte=start_date)),
        avg_rating=Avg('reviews__rating'),
        total_revenue=Sum('sales__net_amount', filter=Q(sales__created_at__gte=start_date, sales__created_at__lte=end_date)),
    ).filter(subject__isnull=False).order_by('-total_downloads')[:10]
    
    # Calculate total downloads for percentage calculation
    total_subject_downloads = subject_performance.aggregate(total=Sum('total_downloads'))['total'] or 0
    
    # Convert QuerySet to list for iteration
    subject_performance_list = list(subject_performance)
    
    # Add percentage to each subject - calculate in view to avoid template issues
    for i, subject in enumerate(subject_performance_list):
        if total_subject_downloads > 0:
            percentage = (subject['total_downloads'] / total_subject_downloads) * 100
        else:
            percentage = 0
        subject_performance_list[i] = {
            'subject': subject['subject'],
            'doc_count': subject['doc_count'],
            'total_downloads': subject['total_downloads'],
            'avg_rating': subject['avg_rating'],
            'total_revenue': subject['total_revenue'],
            'download_percentage': round(percentage, 1)
        }
    
    downloads_total = documents.aggregate(
        total=Count("download_logs", filter=Q(download_logs__download_time__gte=start_date))
    )["total"] or 0

    return {
        'period_days': days,
        'total_revenue': total_revenue,
        'total_sales': sales.count(),
        'total_documents': documents.count(),
        'avg_document_price': documents.aggregate(avg_price=Avg('price'))['avg_price'] or 0,
        'total_downloads': downloads_total,
        'avg_rating': documents.aggregate(avg_rating=Avg('reviews__rating'))['avg_rating'] or 0,
        'monthly_sales': monthly_sales,
        'top_documents': top_documents,
        'subject_performance': subject_performance_list,
        'recent_sales': sales.select_related('document', 'buyer')[:10],
        'conversion_rate': (sales.count() / downloads_total) * 100 if downloads_total else 0,
    }

def get_marketplace_stats(days=30):
    """
    Get overall marketplace statistics
    """
    end_date = timezone.now()
    start_date = end_date - timedelta(days=days)
    
    # Document stats
    document_stats = Document.objects.filter(
        created_at__gte=start_date
    ).aggregate(
        total_docs=Count('id'),
        total_views=Sum('download_logs__id', filter=Q(download_logs__download_time__gte=start_date)),
        total_downloads=Sum('download_logs__id', filter=Q(download_logs__download_time__gte=start_date)),
        avg_price=Avg('price')
    )
    
    # User stats
    from accounts.models import CustomUser
    total_users = CustomUser.objects.count()
    user_stats = CustomUser.objects.filter(
        date_joined__gte=start_date
    ).aggregate(
        new_users=Count('id'),
        active_sellers=Count('id', filter=Q(is_seller=True)),
        total_buyers=Count('id', filter=Q(is_seller=False))
    )
    
    # Get total active sellers and buyers (all time)
    total_sellers = CustomUser.objects.filter(is_seller=True).count()
    total_buyers_all = CustomUser.objects.filter(is_seller=False).count()
    
    # Sales stats
    sales_stats = Sale.objects.filter(
        created_at__gte=start_date
    ).aggregate(
        total_sales=Count('id'),
        total_revenue=Sum('net_amount'),
        avg_sale_value=Avg('net_amount')
    )
    
    # Review stats
    review_stats = Review.objects.filter(
        created_at__gte=start_date
    ).aggregate(
        total_reviews=Count('id'),
        avg_rating=Avg('rating')
    )
    
    return {
        'period_days': days,
        'total_documents': document_stats['total_docs'] or 0,
        'total_views': document_stats['total_views'] or 0,
        'total_downloads': document_stats['total_downloads'] or 0,
        'avg_price': document_stats['avg_price'] or 0,
        'new_users': user_stats['new_users'] or 0,
        'total_users': total_users,
        'active_sellers': total_sellers,
        'total_buyers': total_buyers_all,
        'total_sales': sales_stats['total_sales'] or 0,
        'total_revenue': sales_stats['total_revenue'] or 0,
        'avg_sale_value': sales_stats['avg_sale_value'] or 0,
        'total_reviews': review_stats['total_reviews'] or 0,
        'avg_rating': review_stats['avg_rating'] or 0,
    }

def get_popular_categories(limit=10):
    """
    Get most popular categories based on sales
    """
    categories = Category.objects.annotate(
        document_count=Count('documents'),
        total_sales=Count('documents__sales'),
        total_revenue=Sum('documents__sales__net_amount')
    ).filter(document_count__gt=0).order_by('-total_sales')[:limit]
    
    # Convert to list of dicts for JSON serialization
    return [
        {
            'name': cat.name,
            'document_count': cat.document_count,
            'total_sales': cat.total_sales,
            'total_revenue': float(cat.total_revenue) if cat.total_revenue else 0
        }
        for cat in categories
    ]

def get_trending_subjects(limit=15):
    """
    Get trending subjects based on recent activity
    """
    end_date = timezone.now()
    start_date = end_date - timedelta(days=30)
    
    subjects = Document.objects.filter(
        created_at__gte=start_date,
        subject__isnull=False
    ).exclude(subject='').values('subject').annotate(
        doc_count=Count('id'),
        recent_views=Count('download_logs', filter=Q(download_logs__download_time__gte=start_date)),
        recent_sales=Count('sales', filter=Q(sales__created_at__gte=start_date))
    ).filter(doc_count__gt=0).order_by('-recent_views')[:limit]
    
    # Convert to list of dicts for JSON serialization
    return [
        {
            'subject': subject['subject'],
            'doc_count': subject['doc_count'],
            'recent_views': subject['recent_views'],
            'recent_sales': subject['recent_sales']
        }
        for subject in subjects
    ]

def get_user_behavior_analytics(days=30):
    """
    Track user behavior patterns
    """
    end_date = timezone.now()
    start_date = end_date - timedelta(days=days)
    
    from sharp_student_documents.models import DownloadLog
    
    # Search patterns
    search_data = DownloadLog.objects.filter(
        created_at__gte=start_date
    ).values('document__subject', 'document__document_type', 'document__academic_level')
    
    return {
        'search_patterns': {
            'popular_subjects': search_data.values('document__subject').annotate(count=Count('id')).order_by('-count')[:10],
            'popular_document_types': search_data.values('document__document_type').annotate(count=Count('id')).order_by('-count')[:10],
            'popular_academic_levels': search_data.values('document__academic_level').annotate(count=Count('id')).order_by('-count')[:10],
        },
        'peak_hours': DownloadLog.objects.filter(
            created_at__gte=start_date
        ).extra({
            'hour': 'EXTRACT(hour FROM created_at)'
        }).values('hour').annotate(count=Count('id')).order_by('-count')[:5],
    }
