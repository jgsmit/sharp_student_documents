import time
from django.shortcuts import render, get_object_or_404
from django.db.models import Count, Avg
from django.conf import settings
from django.core.cache import cache
from django.http import HttpResponse, Http404
from django.contrib.sites.requests import RequestSite
from django.views.decorators.http import require_GET
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from cloudinary.utils import cloudinary_url

from documents.models import Category, Document, Order
from documents.views import generate_preview  # helper for text preview


def bad_request(request, exception):
    return render(request, "400.html", status=400)


def permission_denied(request, exception):
    return render(request, "403.html", status=403)


def csrf_failure(request, reason="", template_name=None):
    return render(request, "403.html", status=403)


def page_not_found(request, exception):
    return render(request, "404.html", status=404)


def server_error(request):
    return render(request, "500.html", status=500)


def _site_url(request):
    configured_site_url = getattr(settings, "SITE_URL", "").strip()
    if configured_site_url and "127.0.0.1:8000" not in configured_site_url:
        return configured_site_url.rstrip("/")
    return request.build_absolute_uri("/").rstrip("/")


def robots_txt(request):
    return render(
        request,
        "robots.txt",
        {"site_url": _site_url(request)},
        content_type="text/plain",
    )


def sitemap_xml(request, sitemaps):
    site = RequestSite(request)
    sitemap_data = []

    for sitemap_obj in sitemaps.values():
        sitemap_instance = sitemap_obj() if isinstance(sitemap_obj, type) else sitemap_obj
        sitemap_data.extend(sitemap_instance.get_urls(site=site, protocol=request.scheme))

    return render(request, "sitemap.xml", {"sitemap_data": sitemap_data}, content_type="application/xml")


def home(request):
    # Annotate documents with average ratings and review counts
    documents = Document.objects.select_related(
        'seller', 'category'
    ).annotate(
        average_rating=Avg("reviews__rating"),
        reviews_count=Count("reviews"),
    )

    # Top 5 sellers by total number of paid sales (include first name + username)
    top_sellers = (
        Order.objects.filter(status="paid")
        .select_related('document__seller')
        .values(
            "document__seller__id",
            "document__seller__first_name",
            "document__seller__username",
        )
        .annotate(sales_count=Count("id"))
        .order_by("-sales_count")[:5]
    )

    # Purchases for logged-in user
    purchased_ids = set()
    purchases = []

    if request.user.is_authenticated:
        orders = (
            Order.objects.filter(buyer=request.user, status="paid")
            .select_related("document__seller")
            .prefetch_related("document__reviews")
        )
        for order in orders:
            doc = order.document

            # ✅ Use local file URLs instead of Cloudinary
            download_url = getattr(doc.file, 'url', '')

            purchases.append({
                "order": order,
                "document": doc,
                "download_url": download_url,
            })
            purchased_ids.add(doc.id)

    # Add preview and access info for each document
    for doc in documents:
        # Flag if the logged-in user purchased it
        doc.can_access_full = doc.id in purchased_ids
        
        # Find the order for this document if user purchased it
        doc.user_order = None
        if doc.can_access_full and request.user.is_authenticated:
            try:
                doc.user_order = Order.objects.filter(document=doc, buyer=request.user, status="paid").first()
            except:
                doc.user_order = None

        # Generate preview text if missing
        if not doc.preview_text:
            try:
                uploaded_file = getattr(doc.file, "file", None)
                doc.preview_text = generate_preview(uploaded_file, doc.description)
                doc.save(update_fields=["preview_text"])
            except Exception:
                doc.preview_text = doc.description[:300] + "..."

    context = {
        "documents": documents,
        "top_sellers": top_sellers,
        "purchases": purchases,
        "categories": Category.objects.filter(is_active=True).order_by("sort_order", "name")[:12],
    }
    return render(request, "home.html", context)


@login_required
@require_GET
def download_document(request, document_id):
    """Secure document download with rate limiting"""
    # Rate limiting: max 5 downloads per minute per user
    cache_key = f"download_rate_{request.user.id}"
    download_count = cache.get(cache_key, 0)
    
    if download_count >= 5:
        raise PermissionDenied("Too many download attempts. Please try again later.")
    
    # Increment rate limit counter
    cache.set(cache_key, download_count + 1, 60)  # 1 minute expiry
    
    # Get document and verify purchase
    document = get_object_or_404(
        Document.objects.select_related('seller'),
        id=document_id
    )
    
    # Check if user purchased the document or is the seller
    has_access = (
        document.seller == request.user or
        Order.objects.filter(
            buyer=request.user,
            document=document,
            status='paid'
        ).exists()
    )
    
    if not has_access:
        raise PermissionDenied("You don't have access to this document.")
    
    try:
        # Generate secure download URL
        public_id = getattr(document.file, "public_id", None)
        if not public_id:
            raise Http404("Document file not found.")
            
        download_url, _ = cloudinary_url(
            public_id,
            resource_type="raw",
            sign_url=True,
            expires_at=int(time.time()) + 300,  # 5 minutes expiry
        )
        
        # Log the download for analytics
        from .models import DownloadLog
        DownloadLog.objects.create(
            user=request.user,
            document=document,
            ip_address=request.META.get('REMOTE_ADDR')
        )
        
        return HttpResponse(f"Download link: {download_url}")
        
    except Exception as e:
        raise Http404(f"Error generating download link: {str(e)}")
