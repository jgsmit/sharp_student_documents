from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth import get_user_model
from django.contrib import messages
from django.db import transaction
from django.db.models import Sum, Avg, Count, F, Q, DecimalField, OuterRef, Subquery, IntegerField, Value
from django.db.models.functions import Coalesce
from django.utils import timezone
from datetime import timedelta
from decimal import Decimal
from django.conf import settings
from django.urls import reverse
from django.http import HttpResponse, JsonResponse, StreamingHttpResponse, FileResponse
from django.core.paginator import Paginator
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings
import os
import mimetypes

from .models import Document, Order, Category
from .forms import DocumentUploadForm, DocumentSearchForm
from reviews.models import Review
from .models import RefundRequest
from .forms import RefundRequestForm
from sharp_student_documents.models import DownloadLog
from accounts.permissions import seller_required, can_upload_documents, can_manage_analytics
from accounts.models import CustomUser
from withdrawals.models import WithdrawalRequest
from payments.models import Payment
from security.models import SecurityLog, TwoFactorAuth, IdentityVerification, FraudDetection
from notifications.utils import send_new_document_notification, send_new_purchase_notification

# Import education models if available
try:
    from education.models import StudySession
except ImportError:
    StudySession = None

# Import notification models if available  
try:
    from security.models import Notification
except ImportError:
    Notification = None

import PyPDF2
from docx import Document as DocxDocument
import requests
from django.http import StreamingHttpResponse
import os
import time
import logging

logger = logging.getLogger(__name__)

# -------------------------
# Helper: Generate document preview and page count
# -------------------------
def generate_preview(uploaded_file, description=""):
    """
    Returns both preview text and page count for PDFs, DOCX, TXT.
    """
    preview_text = ""
    pages = None

    if uploaded_file:
        name = uploaded_file.name.lower()
        try:
            if name.endswith(".pdf"):
                reader = PyPDF2.PdfReader(uploaded_file)
                text_pages = []
                for page in reader.pages[:3]:  # first 3 pages
                    text = page.extract_text()
                    if text:
                        text_pages.append(text)
                preview_text = "\n\n".join(text_pages)[:2000]
                pages = len(reader.pages)

            elif name.endswith(".txt"):
                content = uploaded_file.read().decode("utf-8", errors="ignore")
                paras = [p.strip() for p in content.split("\n\n") if p.strip()]
                preview_text = "\n\n".join(paras[:10])
                pages = max(1, len(paras) // 10)

            elif name.endswith(".docx"):
                docx_file = DocxDocument(uploaded_file)
                paras = [p.text for p in docx_file.paragraphs if p.text.strip()]
                preview_text = "\n\n".join(paras[:10])
                pages = max(1, len(paras) // 10)

        except Exception as e:
            logger.exception("Preview extraction error")
        finally:
            try:
                uploaded_file.seek(0)
            except Exception:
                pass

    if not preview_text and description:
        paragraphs = [p.strip() for p in description.split("\n\n") if p.strip()]
        preview_text = "\n\n".join(paragraphs[:3]) if paragraphs else description[:500]
        pages = max(1, len(paragraphs) // 3)

    return preview_text, pages

# ---------------------------
# Document Detail View
# ---------------------------



# ---------------------------
# Document List View
# ---------------------------
def document_list(request):
    """
    Enhanced document listing with advanced search functionality
    Shows all documents by default, with optional advanced search
    """
    search_form = DocumentSearchForm(request.GET or None)
    documents = Document.objects.all()
    
    # Always apply filters from GET parameters (both with and without search query)
    # Basic search query (handle both 'q' from template and 'query' from form)
    query = request.GET.get('q') or request.GET.get('query')
    search_type = request.GET.get('search_type', 'all')
    
    if query:
        if search_type == 'title':
            documents = documents.filter(title__icontains=query)
        elif search_type == 'content':
            documents = documents.filter(description__icontains=query)
        elif search_type == 'author':
            documents = documents.filter(author__icontains=query)
        elif search_type == 'tags':
            documents = documents.filter(tags__icontains=query)
        elif search_type == 'isbn':
            documents = documents.filter(isbn__icontains=query)
        else:  # all fields
            documents = documents.filter(
                Q(title__icontains=query) |
                Q(description__icontains=query) |
                Q(tags__icontains=query) |
                Q(author__icontains=query) |
                Q(subject__icontains=query) |
                Q(course_code__icontains=query) |
                Q(isbn__icontains=query)
            )
    
    # Document type filter
    document_type = request.GET.get('document_type')
    if document_type:
        documents = documents.filter(document_type=document_type)
    
    # Academic level filter
    academic_level = request.GET.get('academic_level')
    if academic_level:
        documents = documents.filter(academic_level=academic_level)
    
    # Subject filter
    subject = request.GET.get('subject')
    if subject:
        documents = documents.filter(subject__icontains=subject)
    
    # Course code filter
    course_code = request.GET.get('course_code')
    if course_code:
        documents = documents.filter(course_code__icontains=course_code)
    
    # Author filter
    author = request.GET.get('author')
    if author:
        documents = documents.filter(author__icontains=author)
    
    # ISBN filter
    isbn = request.GET.get('isbn')
    if isbn:
        documents = documents.filter(isbn__icontains=isbn)
    
    # University filter
    university = request.GET.get('university')
    if university:
        documents = documents.filter(university__icontains=university)
    
    # Year range filter
    year_min = request.GET.get('year_min')
    year_max = request.GET.get('year_max')
    if year_min:
        try:
            documents = documents.filter(year__gte=int(year_min))
        except ValueError:
            pass
    if year_max:
        try:
            documents = documents.filter(year__lte=int(year_max))
        except ValueError:
            pass
    
    # Price range filter
    min_price = request.GET.get('min_price')
    max_price = request.GET.get('max_price')
    if min_price:
        try:
            documents = documents.filter(price__gte=float(min_price))
        except ValueError:
            pass
    if max_price:
        try:
            documents = documents.filter(price__lte=float(max_price))
        except ValueError:
            pass
    
    # Tags filter
    tags = request.GET.get('tags')
    if tags:
        tag_list = [tag.strip() for tag in tags.split(',') if tag.strip()]
        for tag in tag_list:
            documents = documents.filter(tags__icontains=tag)
    
    # Category filter
    category = request.GET.get('category')
    if category:
        try:
            documents = documents.filter(category_id=int(category))
        except ValueError:
            pass
    
    # Sorting
    sort_by = request.GET.get('sort_by', '-created_at')
    # Validate sort_by to prevent SQL injection
    valid_sort_fields = [
        'created_at', '-created_at', 'price', '-price', 
        'title', '-title', 'rating', '-rating'
    ]
    if sort_by in valid_sort_fields:
        if sort_by in ['rating', '-rating']:
            # Handle rating sorting with annotation
            documents = documents.annotate(
                avg_rating=Avg('reviews__rating')
            ).order_by(sort_by)
        else:
            documents = documents.order_by(sort_by)
    else:
        documents = documents.order_by('-created_at')
    
    # Annotate with ratings and review count
    documents = documents.annotate(
        average_rating=Avg('reviews__rating'),
        reviews_count=Count('reviews')
    ).select_related('seller', 'category').prefetch_related('reviews')
    
    # Add pagination
    from django.core.paginator import Paginator
    paginator = Paginator(documents, 12)  # 12 documents per page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    result_count = paginator.count
    current_page = page_obj.number
    index_start = page_obj.start_index() if result_count else 0
    index_end = page_obj.end_index() if result_count else 0

    active_filters = []
    if query:
        active_filters.append(query)
    if subject:
        active_filters.append(subject)
    if academic_level:
        active_filters.append(academic_level.replace("_", " ").title())
    if document_type:
        active_filters.append(document_type.replace("_", " ").title())
    if university:
        active_filters.append(university)
    if author:
        active_filters.append(author)

    filter_label = ", ".join(active_filters[:4]) if active_filters else "student documents"
    search_heading = "Browse Documents"
    search_intro = "Explore student documents, notes, study guides, and past papers on SharpDocs."
    seo_title = "Browse Student Documents, Study Guides & Notes | SharpDocs"
    seo_description = (
        "Browse student documents, study guides, notes, and past papers on SharpDocs. "
        "Find academic resources by subject, university, author, and course."
    )

    if query:
        search_heading = f"Search Results for {query}"
        search_intro = (
            f"Browse SharpDocs search results for {query}. Discover matching notes, study guides, "
            "past papers, and other academic resources."
        )
        seo_title = f"{query} Documents & Study Notes | SharpDocs Search"
        seo_description = (
            f"Search SharpDocs for {query} documents, notes, study guides, and past papers. "
            f"Explore {result_count} results with filters for subject, level, and price."
        )
    elif active_filters:
        search_heading = f"{filter_label} on SharpDocs"
        search_intro = (
            f"Browse {filter_label} on SharpDocs. Compare student documents, notes, study guides, "
            "and past papers from verified sellers."
        )
        seo_title = f"{filter_label} | SharpDocs Documents"
        seo_description = (
            f"Explore {filter_label} on SharpDocs. Browse {result_count} student documents, "
            "notes, study guides, and past papers from verified sellers."
        )

    context = {
        'documents': page_obj,
        'document_types': Document.DOCUMENT_TYPES,
        'academic_levels': Document.ACADEMIC_LEVELS,
        'categories': Category.objects.filter(is_active=True).order_by('sort_order', 'name'),
        'featured_subjects': [
            "Mathematics",
            "Computer Science",
            "Business",
            "Engineering",
            "Medicine",
            "Economics",
        ],
        'brand_aliases': [
            "SharpDocs",
            "SharpDoc",
            "Sharp Docs",
            "Sharp Students",
            "Sharp Student Docs",
            "SharpStudentDoc",
            "SharpStudentDocs",
            "sharp studen",
        ],
        'search_form': search_form,
        'is_paginated': page_obj.has_other_pages(),
        'page_obj': page_obj,
        'result_count': result_count,
        'index_start': index_start,
        'index_end': index_end,
        'search_heading': search_heading,
        'search_intro': search_intro,
        'seo_title': seo_title,
        'seo_description': seo_description,
        'seo_filter_label': filter_label,
        'search_query': query or "",
        'current_sort': sort_by,
        'current_page_number': current_page,
    }
    
    return render(request, 'documents/document_list.html', context)


def category_detail(request, slug):
    """
    Public, indexable landing page for a document category.
    """
    category = get_object_or_404(Category, slug=slug, is_active=True)

    documents = (
        Document.objects.filter(category=category)
        .annotate(
            average_rating=Avg("reviews__rating"),
            reviews_count=Count("reviews"),
        )
        .select_related("seller", "category")
        .prefetch_related("reviews")
        .order_by("-created_at")
    )

    paginator = Paginator(documents, 12)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    result_count = paginator.count
    index_start = page_obj.start_index() if result_count else 0
    index_end = page_obj.end_index() if result_count else 0

    category_name = category.name.strip()
    category_type = category.get_category_type_display() if hasattr(category, "get_category_type_display") else ""
    page_intro = category.description or (
        f"Browse {category_name.lower()} documents, study guides, notes, and past papers on SharpDocs."
    )

    context = {
        "documents": page_obj,
        "document_types": Document.DOCUMENT_TYPES,
        "academic_levels": Document.ACADEMIC_LEVELS,
        "categories": Category.objects.filter(is_active=True).order_by("sort_order", "name"),
        "featured_subjects": [
            "Mathematics",
            "Computer Science",
            "Business",
            "Engineering",
            "Medicine",
            "Economics",
        ],
        "search_form": DocumentSearchForm(),
        "is_paginated": page_obj.has_other_pages(),
        "page_obj": page_obj,
        "result_count": result_count,
        "index_start": index_start,
        "index_end": index_end,
        "search_heading": f"{category_name} Documents",
        "search_intro": page_intro,
        "seo_title": f"{category_name} Documents, Notes & Study Guides | SharpDocs",
        "seo_description": (
            f"Browse {result_count} {category_name.lower()} documents on SharpDocs, including notes, "
            f"study guides, and past papers."
        ),
        "seo_filter_label": category_name,
        "search_query": "",
        "current_sort": "-created_at",
        "current_page_number": page_obj.number,
        "category_page": category,
        "category_type_label": category_type,
    }

    return render(request, "documents/document_list.html", context)

# ---------------------------
# Advanced Search View
# ---------------------------
@login_required
def advanced_search(request):
    """
    Advanced search page with all search filters
    """
    search_form = DocumentSearchForm(request.GET or None)
    documents = Document.objects.all()
    
    # Apply search filters if provided
    if request.GET.get('q'):
        if search_form.is_valid():
            query = search_form.cleaned_data.get('query', '')
            search_type = search_form.cleaned_data.get('search_type', 'all')
            
            if query:
                if search_type == 'title':
                    documents = documents.filter(title__icontains=query)
                elif search_type == 'content':
                    documents = documents.filter(description__icontains=query)
                elif search_type == 'tags':
                    documents = documents.filter(tags__icontains=query)
                elif search_type == 'author':
                    documents = documents.filter(author__icontains=query)
                elif search_type == 'isbn':
                    documents = documents.filter(isbn__icontains=query)
                else:  # all fields
                    documents = documents.filter(
                        Q(title__icontains=query) |
                        Q(description__icontains=query) |
                        Q(tags__icontains=query) |
                        Q(author__icontains=query) |
                        Q(subject__icontains=query) |
                        Q(course_code__icontains=query) |
                        Q(isbn__icontains=query)
                    )
            
            # Category filter
            category = search_form.cleaned_data.get('category')
            if category:
                documents = documents.filter(category=category)
            
            # Document type filter
            document_type = search_form.cleaned_data.get('document_type')
            if document_type:
                documents = documents.filter(document_type=document_type)
            
            # Academic level filter
            academic_level = search_form.cleaned_data.get('academic_level')
            if academic_level:
                documents = documents.filter(academic_level=academic_level)
            
            # Subject filter
            subject = search_form.cleaned_data.get('subject')
            if subject:
                documents = documents.filter(subject__icontains=subject)
            
            # Course code filter
            course_code = search_form.cleaned_data.get('course_code')
            if course_code:
                documents = documents.filter(course_code__icontains=course_code)
            
            # Author filter
            author = search_form.cleaned_data.get('author')
            if author:
                documents = documents.filter(author__icontains=author)
            
            # ISBN filter
            isbn = search_form.cleaned_data.get('isbn')
            if isbn:
                documents = documents.filter(isbn__icontains=isbn)
            
            # University filter
            university = search_form.cleaned_data.get('university')
            if university:
                documents = documents.filter(university__icontains=university)
            
            # Year range filter
            year_min = search_form.cleaned_data.get('year_min')
            year_max = search_form.cleaned_data.get('year_max')
            if year_min:
                documents = documents.filter(year__gte=year_min)
            if year_max:
                documents = documents.filter(year__lte=year_max)
            
            # Price range filter
            price_min = search_form.cleaned_data.get('price_min')
            price_max = search_form.cleaned_data.get('price_max')
            if price_min:
                documents = documents.filter(price__gte=price_min)
            if price_max:
                documents = documents.filter(price__lte=price_max)
            
            # Tags filter
            tags = search_form.cleaned_data.get('tags')
            if tags:
                tag_list = [tag.strip() for tag in tags.split(',') if tag.strip()]
                for tag in tag_list:
                    documents = documents.filter(tags__icontains=tag)
            
            # Sorting
            sort_by = search_form.cleaned_data.get('sort_by', '-created_at')
            documents = documents.order_by(sort_by)
        
        # Annotate with ratings and review count
        documents = documents.annotate(
            average_rating=Avg('reviews__rating'),
            reviews_count=Count('reviews')
        ).select_related('seller', 'category').prefetch_related('reviews')
    
    context = {
        'documents': documents,
        'search_form': search_form,
        'is_advanced_search': True,
    }
    
    return render(request, 'documents/advanced_search.html', context)


def document_detail(request, slug):
    document = get_object_or_404(
        Document.objects.annotate(
            average_rating=Avg("reviews__rating"),
            reviews_count=Count("reviews"),
        ),
        slug=slug
    )

    # Related documents
    related_documents = Document.objects.filter(
        Q(category=document.category) | Q(seller=document.seller)
    ).exclude(id=document.id)[:4]

    # Reviews
    reviews = Review.objects.filter(document=document).select_related("reviewer")

    # Keep the listing public for search engines and visitors, while
    # still restricting download access to authenticated buyers.
    user_orders = Order.objects.none()
    can_download = False
    user_order = None

    if request.user.is_authenticated:
        user_orders = request.user.orders.filter(document=document, status="paid")
        can_download = user_orders.exists()
        user_order = user_orders.first() if can_download else None

    # Generate download URL only if purchased (using local media)
    download_url = None
    if can_download and document.file:
        download_url = document.file.url

    detail_labels = [
        document.subject,
        document.course_code,
        document.university,
        document.get_document_type_display() if hasattr(document, "get_document_type_display") else "",
        document.get_academic_level_display() if hasattr(document, "get_academic_level_display") else "",
    ]
    detail_labels = [label for label in detail_labels if label]

    seo_description = (
        f"Download {document.title} on SharpDocs."
        f" Access {document.get_academic_level_display().lower()} study materials"
        f"{f' for {document.subject}' if document.subject else ''}"
        f"{f' at {document.university}' if document.university else ''},"
        f" including notes, study guides, past papers, and academic resources."
    )

    if document.description:
        seo_description = f"{document.description[:220].strip()} | SharpDocs"

    seo_keywords = ", ".join(
        [
            keyword
            for keyword in [
                document.title,
                document.subject,
                document.course_code,
                document.university,
                document.author,
                document.tags,
                "SharpDocs",
                "student documents",
                "study guides",
                "notes",
                "past papers",
            ]
            if keyword
        ]
    )

    context = {
        "document": document,
        "related_documents": related_documents,
        "reviews": reviews,
        "can_download": can_download,
        "download_url": download_url,
        "user_order": user_order,
        "detail_labels": detail_labels,
        "seo_description": seo_description,
        "seo_keywords": seo_keywords,
    }

    return render(request, "documents/document_detail.html", context)


# -------------------------
# Seller Functions
# -------------------------
@login_required
def upload_document(request):
    """
    Upload a document to local storage and store its metadata in the database.
    Ensures preview, pages, and file path are correctly saved.
    """
    if not getattr(request.user, "is_seller", False):
        if request.user.is_superuser:
            messages.info(request, "Admin accounts do not use the seller upload page.")
            return redirect("documents:admin_dashboard")
        messages.error(request, "Only seller accounts can upload documents.")
        return redirect("documents:buyer_dashboard")

    if request.method == "POST":
        form = DocumentUploadForm(request.POST, request.FILES)
        if form.is_valid():
            try:
                doc = form.save(commit=False)
                doc.seller = request.user

                uploaded_file = request.FILES.get("file")
                if uploaded_file:
                    # Generate preview text and page count
                    preview_text, pages = generate_preview(uploaded_file, doc.description)
                    doc.preview_text = preview_text
                    doc.pages = pages

                # Save document to database
                doc.save()

                try:
                    send_new_document_notification(doc)
                except Exception:
                    logger.exception("Failed to send new document notification")

                messages.success(request, "✅ Document uploaded successfully with preview.")
                return redirect("documents:seller_dashboard")
                
            except Exception as e:
                # Handle file errors gracefully
                error_message = str(e)
                logger.exception("Document upload failed")
                if "maximum allowed" in error_message.lower() or "too large" in error_message.lower():
                    error_msg = "The upload was larger than this server currently accepts."
                elif "file type" in error_message.lower() or "extension" in error_message.lower():
                    error_msg = "The file could not be accepted by storage with its current name or format."
                else:
                    error_msg = "An error occurred while uploading your file. Please try again."

                if settings.DEBUG:
                    error_msg = f"{error_msg} ({error_message})"
                 
                messages.error(request, f"❌ {error_msg}")
                return render(request, "documents/upload_document.html", {"form": form})
        else:
            logger.warning("Upload form invalid: %s", form.errors)
            messages.error(request, "❌ Please fix the errors in the form and try again.")
    else:
        form = DocumentUploadForm()

    return render(request, "documents/upload_document.html", {"form": form})
@login_required
def edit_document(request, pk):
    """
    Edit an existing document. Updates preview, page count, and handles new file uploads.
    """
    document = get_object_or_404(Document, pk=pk, seller=request.user)

    if request.method == "POST":
        form = DocumentUploadForm(request.POST, request.FILES, instance=document)
        if form.is_valid():
            doc = form.save(commit=False)
            uploaded_file = request.FILES.get("file")

            if uploaded_file:
                # Generate preview and page count for new uploaded file
                preview_text, pages = generate_preview(uploaded_file, doc.description)
                doc.preview_text = preview_text
                doc.pages = pages

            doc.save()

            messages.success(request, "✅ Document updated successfully with new preview.")
            return redirect("documents:seller_dashboard")
    else:
        form = DocumentUploadForm(instance=document)

    return render(request, "documents/edit_document.html", {"form": form, "document": document})


@login_required
def delete_document(request, pk):
    """
    Delete a document. Ensures only the seller can delete their own documents.
    """
    document = get_object_or_404(Document, pk=pk, seller=request.user)

    if request.method == "POST":
        document.delete()
        messages.success(request, "✅ Document deleted successfully.")
        return redirect("documents:seller_dashboard")

    return render(request, "documents/delete_document.html", {"document": document})


@login_required
def seller_documents(request):
    """
    Display all documents for the current seller with enhanced filtering and management options
    """
    if not getattr(request.user, "is_seller", False):
        return redirect("home")
    
    # Get all seller's documents for statistics
    all_documents = Document.objects.filter(seller=request.user)
    
    # Order-based metrics must be isolated from other joins (reviews/download logs),
    # otherwise counts/sums can be over-inflated by join multiplication.
    paid_orders_by_doc = (
        Order.objects.filter(document=OuterRef("pk"), status="paid")
        .values("document")
    )
    sales_count_sq = Subquery(
        paid_orders_by_doc.annotate(c=Count("id")).values("c")[:1],
        output_field=IntegerField(),
    )
    total_revenue_sq = Subquery(
        paid_orders_by_doc.annotate(r=Sum("amount_paid")).values("r")[:1],
        output_field=DecimalField(max_digits=12, decimal_places=2),
    )

    # Get seller's documents with enhanced statistics for filtering
    documents = all_documents.annotate(
        sales_count=Coalesce(sales_count_sq, Value(0, output_field=IntegerField())),
        total_revenue=Coalesce(
            total_revenue_sq,
            Value(Decimal("0.00"), output_field=DecimalField(max_digits=12, decimal_places=2)),
        ),
        average_rating=Avg("reviews__rating"),
        reviews_count=Count("reviews", distinct=True),
        downloads_count=Count("download_logs", distinct=True),
    ).order_by("-created_at")
    
    # Apply filters from GET parameters
    search_form = DocumentSearchForm(request.GET or None)
    
    # Basic search query
    query = request.GET.get('q') or request.GET.get('query')
    if query:
        documents = documents.filter(
            Q(title__icontains=query) |
            Q(description__icontains=query) |
            Q(tags__icontains=query) |
            Q(author__icontains=query) |
            Q(subject__icontains=query) |
            Q(course_code__icontains=query) |
            Q(isbn__icontains=query)
        )
    
    # Document type filter
    document_type = request.GET.get('document_type')
    if document_type:
        documents = documents.filter(document_type=document_type)
    
    # Academic level filter
    academic_level = request.GET.get('academic_level')
    if academic_level:
        documents = documents.filter(academic_level=academic_level)
    
    # Subject filter
    subject = request.GET.get('subject')
    if subject:
        documents = documents.filter(subject__icontains=subject)
    
    # Category filter
    category = request.GET.get('category')
    if category:
        try:
            documents = documents.filter(category_id=int(category))
        except ValueError:
            pass
    
    # Sorting
    sort_by = request.GET.get('sort_by', '-created_at')
    valid_sort_fields = [
        'created_at', '-created_at', 'price', '-price', 
        'title', '-title', 'sales_count', '-sales_count',
        'average_rating', '-average_rating'
    ]
    if sort_by in valid_sort_fields:
        documents = documents.order_by(sort_by)
    else:
        documents = documents.order_by('-created_at')
    
    # Add pagination
    from django.core.paginator import Paginator
    paginator = Paginator(documents, 12)  # 12 documents per page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        "documents": page_obj,
        "search_form": search_form,
        "is_paginated": page_obj.has_other_pages(),
        "page_obj": page_obj,
        "total_documents": all_documents.count(),
        "total_revenue": all_documents.aggregate(total=Sum("orders__amount_paid", filter=Q(orders__status="paid")))["total"] or 0,
        "total_sales": all_documents.aggregate(total=Count("orders", filter=Q(orders__status="paid")))["total"] or 0,
        "document_types": Document.DOCUMENT_TYPES,
        "academic_levels": Document.ACADEMIC_LEVELS,
    }
    
    return render(request, "documents/seller_documents.html", context)

@login_required
def seller_dashboard(request):
    """
    Enhanced seller dashboard with access to all seller functionality across all apps
    """
    if not getattr(request.user, "is_seller", False):
        return redirect("home")

    # Import unified financial utilities
    from .financial_utils import get_unified_financial_data, synchronize_financial_data
    
    # Get standardized financial data for this seller
    financial_data = get_unified_financial_data(user=request.user, is_admin=False)
    
    # Synchronize financial data to ensure consistency
    synchronize_financial_data()

    # Withdrawal maturity messaging (14-day hold): if seller tries to withdraw too early, show days to maturity.
    withdrawal_hold_notice = None
    try:
        from django.conf import settings
        from django.utils import timezone
        from datetime import timedelta
        from sales.models import Sale
        from withdrawals.services import WithdrawalService

        hold_days = WithdrawalService.hold_days()
        min_amount = Decimal(str(getattr(settings, "WITHDRAWALS_MIN_WITHDRAWAL_AMOUNT", "10.00")))

        wallet_balance = Decimal(str(financial_data.get("wallet", {}).get("balance", 0) or 0))
        wallet_held = Decimal(str(financial_data.get("wallet", {}).get("pending_balance", 0) or 0))

        if wallet_balance < min_amount and wallet_held > 0:
            oldest_held = (
                Sale.objects.filter(seller=request.user, wallet_released_at__isnull=True)
                .order_by("created_at")
                .only("created_at")
                .first()
            )
            if oldest_held and oldest_held.created_at:
                maturity_date = (oldest_held.created_at + timedelta(days=hold_days)).date()
                days_until = (maturity_date - timezone.localdate()).days
                if days_until > 0:
                    withdrawal_hold_notice = (
                        f"Your earnings are still held for {hold_days} days. "
                        f"Next funds mature in {days_until} day(s) (on {maturity_date})."
                    )
                else:
                    withdrawal_hold_notice = (
                        "Your earnings should mature soon. Refresh the Withdrawal Dashboard to release matured funds."
                    )
    except Exception:
        withdrawal_hold_notice = None

    # Get seller's documents with accurate order-based metrics (avoid join multiplication)
    paid_orders_by_doc = (
        Order.objects.filter(document=OuterRef("pk"), status="paid")
        .values("document")
    )
    sales_count_sq = Subquery(
        paid_orders_by_doc.annotate(c=Count("id")).values("c")[:1],
        output_field=IntegerField(),
    )
    total_revenue_sq = Subquery(
        paid_orders_by_doc.annotate(r=Sum("amount_paid")).values("r")[:1],
        output_field=DecimalField(max_digits=12, decimal_places=2),
    )

    documents = Document.objects.filter(seller=request.user).annotate(
        sales_count=Coalesce(sales_count_sq, Value(0, output_field=IntegerField())),
        total_revenue=Coalesce(
            total_revenue_sq,
            Value(Decimal("0.00"), output_field=DecimalField(max_digits=12, decimal_places=2)),
        ),
        average_rating=Avg("reviews__rating"),
        reviews_count=Count("reviews", distinct=True),
    ).order_by("-created_at")
    
    # Reviews and feedback
    doc_reviews = {doc.id: Review.objects.filter(document=doc).select_related("reviewer") for doc in documents}
    all_reviews = Review.objects.filter(document__seller=request.user).select_related("reviewer", "document")
    
    # Security activities
    recent_activities = []
    try:
        recent_activities = list(SecurityLog.objects.filter(user=request.user).order_by("-timestamp")[:10])
    except:
        recent_activities = []
    
    # Education data (study tools for sellers)
    study_sessions = []
    if StudySession:
        study_sessions = list(StudySession.objects.filter(user=request.user).order_by("-created_at")[:5])
    
    # 2FA status for withdrawals (general security 2FA)
    two_fa_enabled = False
    try:
        from security.models import TwoFactorAuth
        two_fa = TwoFactorAuth.objects.get(user=request.user)
        two_fa_enabled = two_fa.is_enabled
    except:
        two_fa_enabled = False
    
    # Pagination setup
    from django.core.paginator import Paginator
    
    # Get recent orders for pagination
    recent_orders_queryset = Order.objects.filter(document__seller=request.user).order_by("-created_at")
    recent_orders_paginator = Paginator(recent_orders_queryset, 10)  # 10 orders per page
    recent_orders_page_number = request.GET.get('orders_page', 1)
    recent_orders = recent_orders_paginator.get_page(recent_orders_page_number)
    
    # Get recent reviews for pagination
    recent_reviews_queryset = Review.objects.filter(document__seller=request.user).order_by("-created_at")
    reviews_paginator = Paginator(recent_reviews_queryset, 10)  # 10 reviews per page
    reviews_page_number = request.GET.get('reviews_page', 1)
    recent_reviews = reviews_paginator.get_page(reviews_page_number)
    
    # Get top documents for pagination (create queryset before documents is paginated)
    top_documents_queryset = Document.objects.filter(seller=request.user).annotate(
        sales_count=Coalesce(sales_count_sq, Value(0, output_field=IntegerField())),
        total_revenue=Coalesce(
            total_revenue_sq,
            Value(Decimal("0.00"), output_field=DecimalField(max_digits=12, decimal_places=2)),
        ),
    ).order_by("-sales_count", "-total_revenue")[:20]
    top_docs_paginator = Paginator(top_documents_queryset, 8)  # 8 top documents per page
    top_docs_page_number = request.GET.get('top_docs_page', 1)
    top_documents = top_docs_paginator.get_page(top_docs_page_number)
    
    # Paginate documents (do this after creating top_documents_queryset)
    documents_paginator = Paginator(documents, 12)  # 12 documents per page
    documents_page_number = request.GET.get('docs_page', 1)
    documents = documents_paginator.get_page(documents_page_number)
    
    context = {
        "total_sales": financial_data["total_sales"],
        "pending_orders": financial_data["pending_sales"],
        "total_documents": Document.objects.filter(seller=request.user).count(),
        
        # Reviews Management
        "doc_reviews": doc_reviews,
        "all_reviews": all_reviews,
        "total_reviews": all_reviews.count(),
        "average_rating": all_reviews.aggregate(avg=Avg("rating"))["avg"] or 0,
        
        # Withdrawal Management - using unified financial data
        "withdrawal_requests": financial_data["withdrawal_requests"],
        "pending_withdrawals": financial_data["pending_withdrawals"],
        "failed_withdrawals": financial_data.get("failed_withdrawals", []),
        "total_withdrawn": financial_data["wallet"]["total_withdrawn"],
        
        # Financial Data - using unified financial data
        "total_gross_sales": financial_data.get("total_gross_sales", 0),
        "total_earnings": financial_data["total_earnings"],
        "pending_earnings": financial_data["pending_earnings"],
        "wallet": financial_data["wallet"],
        "withdrawal_hold_notice": withdrawal_hold_notice,
        "recent_sales": financial_data["recent_sales"],
        "total_sales_amount": financial_data["total_sales_amount"],
        "total_commission_amount": financial_data["total_commission_amount"],
        "two_fa_enabled": two_fa_enabled,
        
        # Education & Tools
        "study_sessions": study_sessions,
        "study_time_today": 0,  # Default if StudySession not available
        
        # Security & Activity
        "recent_activities": recent_activities,
        "last_login": recent_activities[0] if recent_activities else None,
        
        # Quick Stats
        "unread_notifications": 0,  # Default if Notification not available,
        
        # Paginated data
        "recent_orders": recent_orders,
        "documents": documents,
        "recent_reviews": recent_reviews,
        "top_documents": top_documents,
        
        # Pagination data for recent orders
        "orders_page_number": recent_orders_page_number,
        "orders_has_previous": recent_orders.has_previous(),
        "orders_has_next": recent_orders.has_next(),
        "orders_previous_page_number": recent_orders.previous_page_number() if recent_orders.has_previous() else None,
        "orders_next_page_number": recent_orders.next_page_number() if recent_orders.has_next() else None,
        "orders_num_pages": recent_orders_paginator.num_pages,
        "orders_total": recent_orders_paginator.count,
        
        # Pagination data for documents
        "docs_page_number": documents_page_number,
        "docs_has_previous": documents.has_previous(),
        "docs_has_next": documents.has_next(),
        "docs_num_pages": documents_paginator.num_pages,
        "docs_total": documents_paginator.count,
        
        # Pagination data for reviews
        "reviews_page_number": reviews_page_number,
        "reviews_has_previous": recent_reviews.has_previous(),
        "reviews_has_next": recent_reviews.has_next(),
        "reviews_previous_page_number": recent_reviews.previous_page_number() if recent_reviews.has_previous() else None,
        "reviews_next_page_number": recent_reviews.next_page_number() if recent_reviews.has_next() else None,
        "reviews_num_pages": reviews_paginator.num_pages,
        "reviews_total": reviews_paginator.count,
        
        # Pagination data for top documents
        "top_docs_page_number": top_docs_page_number,
        "top_docs_has_previous": top_documents.has_previous(),
        "top_docs_has_next": top_documents.has_next(),
        "top_docs_previous_page_number": top_documents.previous_page_number() if top_documents.has_previous() else None,
        "top_docs_next_page_number": top_documents.next_page_number() if top_documents.has_next() else None,
        "top_docs_num_pages": top_docs_paginator.num_pages,
        "top_docs_total": top_docs_paginator.count,
    }
    
    return render(request, "documents/seller_dashboard.html", context)


# -------------------------
# Purchases & Downloads
# -------------------------

# -------------------------
# Unified Dashboard System
# -------------------------

@login_required
def dashboard(request):
    """
    Unified dashboard that routes users to appropriate role-based dashboard
    """
    user = request.user
    
    # Check if user is admin
    if user.is_superuser:
        return redirect("documents:admin_dashboard")
    
    # Check if user is seller
    elif getattr(user, "is_seller", False):
        return redirect("documents:seller_dashboard")
    
    # Regular buyer
    else:
        return redirect("documents:buyer_dashboard")


# -------------------------
# Purchases & Downloads
# -------------------------

# -------------------------
# Unified Dashboard System
# -------------------------

@login_required
def dashboard(request):
    """
    Unified dashboard that routes users to appropriate role-based dashboard
    """
    user = request.user
    
    # Check if user is admin
    if user.is_superuser:
        return redirect("documents:admin_dashboard")
    
    # Check if user is seller
    elif getattr(user, "is_seller", False):
        return redirect("documents:seller_dashboard")
    
    # Regular buyer
    else:
        return redirect("documents:buyer_dashboard")


@login_required
def admin_dashboard(request):
    """
    Admin dashboard with access to all system functionality
    """
    if not request.user.is_superuser:
        return redirect("home")
    
    # Import unified financial utilities
    from .financial_utils import get_unified_financial_data, synchronize_financial_data, debug_financial_data
    
    # Get standardized financial data
    financial_data = get_unified_financial_data(is_admin=True)
    
    # Debug financial discrepancies
    debug_info = debug_financial_data()
    
    # Synchronize financial data to ensure consistency
    synchronize_financial_data()
    
    # Get system-wide statistics
    context = {
        # User Statistics
        "total_users": CustomUser.objects.count() if CustomUser else 0,
        "total_sellers": CustomUser.objects.filter(is_seller=True).count() if CustomUser else 0,
        "total_buyers": CustomUser.objects.filter(is_seller=False).count() if CustomUser else 0,
        "total_staff": CustomUser.objects.filter(is_staff=True).count() if CustomUser else 0,
        "security_staff": CustomUser.objects.filter(is_staff=True).order_by('username') if CustomUser else [],
        
        # Document Statistics
        "total_documents": Document.objects.count(),
        "pending_documents": 0,  # Document model doesn't have status field
        "approved_documents": Document.objects.count(),  # All documents are considered approved
        
        # Use unified financial data
        "total_orders": financial_data["total_orders"],
        "pending_orders": financial_data["pending_orders"],
        "completed_orders": financial_data["completed_orders"],
        "total_revenue": financial_data["total_revenue"],
        "order_completion_rate": financial_data["order_completion_rate"],
        "total_commission": financial_data.get("total_commission", 0),
        "seller_earnings": financial_data.get("total_earnings", 0),
        "pending_order_value": financial_data["pending_revenue"],
        
        # Review Statistics
        "total_reviews": Review.objects.count(),
        "pending_reviews": 0,  # Default if Review has status field
        # Review.objects.filter(status="pending").count(),
        "average_rating": Review.objects.aggregate(
            avg=Avg("rating")
        )["avg"] or 0,
        
        # Withdrawal Statistics - using unified data
        "total_withdrawn": financial_data["total_withdrawn"],
        "net_profit": financial_data["net_profit"],
        
        # Security Statistics
        "recent_logins": SecurityLog.objects.filter(
            event_type='login_success'
        ).order_by("-created_at")[:10] if SecurityLog else [],
        "security_events": SecurityLog.objects.filter(
            severity__in=['medium', 'high', 'critical']
        ).order_by("-created_at")[:10] if SecurityLog else [],
        "total_security_events": SecurityLog.objects.count() if SecurityLog else 0,
        "critical_events": SecurityLog.objects.filter(severity='critical').count() if SecurityLog else 0,
        
        # Login Statistics for Admin Dashboard
        "total_logins": SecurityLog.objects.filter(event_type='login_success').count() if SecurityLog else 0,
        "today_logins": SecurityLog.objects.filter(
            event_type='login_success',
            created_at__date=timezone.now().date()
        ).count() if SecurityLog else 0,
        "failed_logins": SecurityLog.objects.filter(event_type='login_failed').count() if SecurityLog else 0,
        "login_success_rate": 0,  # Will be calculated below
    }
    
    # Calculate login success rate
    total_logins = context["total_logins"]
    failed_logins = context["failed_logins"]
    if total_logins > 0:
        context["login_success_rate"] = round(((total_logins - failed_logins) / total_logins) * 100, 1)
    else:
        context["login_success_rate"] = 0.0
    
    # Add additional admin data
    total_users = context["total_users"]
    context["active_users"] = total_users  # Placeholder - would be calculated from recent logins
    context["failed_orders"] = 0  # Placeholder - would be calculated from failed orders
    
    # Withdrawal data (single source of truth: withdrawals app)
    try:
        from withdrawals.models import WithdrawalRequest as WithdrawalsAppWithdrawal

        withdrawal_requests = list(WithdrawalsAppWithdrawal.objects.all().order_by("-requested_at")[:10])
        pending_withdrawals = [w for w in withdrawal_requests if getattr(w, 'status', None) in ['pending', 'processing']]
        completed_withdrawals = [w for w in withdrawal_requests if getattr(w, 'status', None) == 'completed']
        failed_withdrawals = [w for w in withdrawal_requests if getattr(w, 'status', None) == 'failed']
        
    except Exception as e:
        print(f"Withdrawal data error: {e}")
        withdrawal_requests = []
        pending_withdrawals = []
        completed_withdrawals = []
        failed_withdrawals = []
    
    # Get Payment Management data - limited for display, totals from unified data
    payments = []
    pending_payments = []
    completed_payments = []
    failed_payments = []
    
    try:
        payments = list(Payment.objects.all().order_by("-created_at")[:10])
        pending_payments = [p for p in payments if p.status == "pending"]
        completed_payments = [p for p in payments if p.status == "success"]
        failed_payments = [p for p in payments if p.status == "failed"]
    except Exception as e:
        print(f"Payment data error: {e}")
        payments = []
        pending_payments = []
        completed_payments = []
        failed_payments = []
    
    # Get Account Management data
    all_users = []
    active_users = []
    inactive_users = []
    new_users_count = 0
    
    try:
        all_users = list(CustomUser.objects.all().order_by("-date_joined")[:10])
        active_users = [u for u in all_users if u.is_active]
        inactive_users = [u for u in all_users if not u.is_active]
        new_users_count = CustomUser.objects.filter(date_joined__gte=timezone.now() - timedelta(days=7)).count()
    except Exception as e:
        print(f"User data error: {e}")
        all_users = []
        active_users = []
        inactive_users = []
        new_users_count = 0
    
    context.update({
        # Withdrawal Management - use unified data
        "withdrawal_requests": withdrawal_requests,
        "pending_withdrawals": pending_withdrawals,
        "completed_withdrawals": completed_withdrawals,
        "failed_withdrawals": failed_withdrawals,
        "total_withdrawn": financial_data["total_withdrawn"],  # Use unified data
        
        # Payment Management - use unified data
        "payments": payments,
        "pending_payments": pending_payments,
        "completed_payments": completed_payments,
        "failed_payments": failed_payments,
        "total_payment_revenue": financial_data["successful_payments"],  # Use unified data
        
        # Account Management
        "all_users": all_users,
        "active_users": active_users,
        "inactive_users": inactive_users,
        "new_users": new_users_count,
        
        # Security Statistics for Trust & Security Card
        "users_with_2fa": 0,  # Will be populated below
        "verified_sellers": 0,  # Will be populated below
        "fraud_cases": 0,  # Will be populated below
        "total_verifications": 0,  # Will be populated below
        "pending_verifications": 0,  # Will be populated below
        "approved_verifications": 0,  # Will be populated below
    })
    
    # Add security statistics if security app is available
    try:
        context.update({
            "users_with_2fa": TwoFactorAuth.objects.filter(is_enabled=True).count() if TwoFactorAuth else 0,
            "verified_sellers": IdentityVerification.objects.filter(status='approved').count() if IdentityVerification else 0,
            "fraud_cases": FraudDetection.objects.filter(is_resolved=False).count() if FraudDetection else 0,
            "total_verifications": IdentityVerification.objects.count() if IdentityVerification else 0,
            "pending_verifications": IdentityVerification.objects.filter(status='pending').count() if IdentityVerification else 0,
            "approved_verifications": IdentityVerification.objects.filter(status='approved').count() if IdentityVerification else 0,
        })
    except Exception as e:
        print(f"Security stats error: {e}")
        # Keep default values if security app not available
    
    # Calculate total verifications after security stats are populated
    pending_verifications = context.get("pending_verifications", 0)
    approved_verifications = context.get("approved_verifications", 0)
    context["total_verifications"] = pending_verifications + approved_verifications
    
    return render(request, "documents/admin_dashboard.html", context)

# -------------------------
# Admin Management Views
# -------------------------

@login_required
def admin_manage_users(request):
    """Admin user management page"""
    if not request.user.is_superuser:
        return redirect("home")
    
    # Handle add user POST request
    if request.method == 'POST' and 'add_user' in request.POST:
        username = request.POST.get('username')
        email = request.POST.get('email')
        password = request.POST.get('password')
        confirm_password = request.POST.get('confirm_password')
        user_type = request.POST.get('user_type')
        is_staff = user_type == 'staff'
        is_seller = user_type == 'seller'
        
        # Validation
        if password != confirm_password:
            messages.error(request, 'Passwords do not match.')
        elif CustomUser.objects.filter(username=username).exists():
            messages.error(request, 'Username already exists.')
        elif CustomUser.objects.filter(email=email).exists():
            messages.error(request, 'Email already exists.')
        else:
            # Create user
            user = CustomUser.objects.create_user(
                username=username,
                email=email,
                password=password,
                is_staff=is_staff,
                is_seller=is_seller,
                is_active=True
            )
            messages.success(request, f'User {username} has been created successfully.')
    
    users = CustomUser.objects.all().order_by("-date_joined")
    
    # Filter by user type
    user_type = request.GET.get('type', 'all')
    if user_type == 'sellers':
        users = users.filter(is_seller=True)
    elif user_type == 'buyers':
        users = users.filter(is_seller=False)
    elif user_type == 'staff':
        users = users.filter(is_staff=True)
    
    # Filter by status
    status = request.GET.get('status', 'all')
    if status == 'active':
        users = users.filter(is_active=True)
    elif status == 'inactive':
        users = users.filter(is_active=False)
    
    context = {
        'users': users,
        'user_type': user_type,
        'status': status,
        'total_users': users.count(),
    }
    return render(request, 'documents/admin_manage_users.html', context)

@login_required
def admin_view_user(request, user_id):
    """Admin view user details"""
    if not request.user.is_superuser:
        return redirect("home")
    
    user = get_object_or_404(CustomUser, id=user_id)
    
    # Get user statistics
    user_documents = Document.objects.filter(seller=user)
    user_orders = Order.objects.filter(buyer=user)
    user_reviews = Review.objects.filter(reviewer=user)
    
    context = {
        'user': user,
        'user_documents': user_documents,
        'user_orders': user_orders,
        'user_reviews': user_reviews,
        'total_documents': user_documents.count(),
        'total_orders': user_orders.count(),
        'total_reviews': user_reviews.count(),
        'total_spent': user_orders.filter(status='paid').aggregate(
            total=Sum('amount_paid')
        )['total'] or 0,
        'total_earned': user_orders.filter(status='paid').aggregate(
            total=Sum(
                F('amount_paid') * Decimal(str(getattr(settings, "SELLER_SHARE", Decimal("0.60")))),
                output_field=DecimalField(),
            )
        )['total'] or 0,
    }
    return render(request, 'documents/admin_view_user.html', context)

@login_required
def admin_edit_user(request, user_id):
    """Admin edit user"""
    if not request.user.is_superuser:
        return redirect("home")
    
    user = get_object_or_404(CustomUser, id=user_id)
    
    if request.method == 'POST':
        # Update user fields
        user.username = request.POST.get('username', user.username)
        user.email = request.POST.get('email', user.email)
        user.first_name = request.POST.get('first_name', user.first_name)
        user.last_name = request.POST.get('last_name', user.last_name)
        user.is_seller = 'is_seller' in request.POST
        user.is_staff = 'is_staff' in request.POST
        
        # Handle password change if provided
        new_password = request.POST.get('new_password')
        if new_password:
            user.set_password(new_password)
        
        user.save()
        
        messages.success(request, f'User {user.username} has been updated successfully.')
        return redirect('documents:admin_manage_users')
    
    context = {'user': user}
    return render(request, 'documents/admin_edit_user.html', context)

@login_required
def admin_toggle_user_status(request, user_id):
    """Admin toggle user active status"""
    if not request.user.is_superuser:
        return redirect("home")
    
    user = get_object_or_404(CustomUser, id=user_id)
    
    # Prevent admin from deactivating themselves
    if user == request.user:
        messages.error(request, 'You cannot deactivate your own account.')
        return redirect('documents:admin_manage_users')
    
    # Toggle user status
    user.is_active = not user.is_active
    user.save()
    
    status = "activated" if user.is_active else "deactivated"
    messages.success(request, f'User {user.username} has been {status} successfully.')
    
    return redirect('documents:admin_manage_users')

@login_required
def admin_add_user(request):
    """Admin add new user"""
    if not request.user.is_superuser:
        return redirect("home")
    
    if request.method == 'POST':
        username = request.POST.get('username')
        email = request.POST.get('email')
        password = request.POST.get('password')
        confirm_password = request.POST.get('confirm_password')
        user_type = request.POST.get('user_type')
        is_staff = user_type == 'staff'
        is_seller = user_type == 'seller'
        
        # Validation
        if password != confirm_password:
            messages.error(request, 'Passwords do not match.')
            return render(request, 'documents/admin_add_user.html')
        
        if CustomUser.objects.filter(username=username).exists():
            messages.error(request, 'Username already exists.')
            return render(request, 'documents/admin_add_user.html')
        
        if CustomUser.objects.filter(email=email).exists():
            messages.error(request, 'Email already exists.')
            return render(request, 'documents/admin_add_user.html')
        
        # Create user
        user = CustomUser.objects.create_user(
            username=username,
            email=email,
            password=password,
            is_staff=is_staff,
            is_seller=is_seller,
            is_active=True
        )
        
        messages.success(request, f'User {username} has been created successfully.')
        return redirect('documents:admin_manage_users')
    
    return render(request, 'documents/admin_add_user.html')

@login_required
def admin_delete_user(request, user_id):
    """Admin delete user"""
    if not request.user.is_superuser:
        return redirect("home")
    
    user = get_object_or_404(CustomUser, id=user_id)
    
    # Prevent admin from deleting themselves
    if user == request.user:
        messages.error(request, 'You cannot delete your own account.')
        return redirect('documents:admin_manage_users')
    
    if request.method == 'POST':
        username = request.POST.get('confirm_username')
        if username == user.username:
            # Delete user and related data
            user.delete()
            messages.success(request, f'User {user.username} has been deleted successfully.')
            return redirect('documents:admin_manage_users')
        else:
            messages.error(request, 'Username confirmation does not match.')
    
    context = {'user': user}
    return render(request, 'documents/admin_delete_user.html', context)

@login_required
def admin_user_documents(request, user_id):
    """Admin view user's documents"""
    if not request.user.is_superuser:
        return redirect("home")
    
    user = get_object_or_404(CustomUser, id=user_id)
    documents = Document.objects.filter(seller=user).order_by("-created_at")
    
    context = {
        'user': user,
        'documents': documents.select_related('category'),
        'total_documents': documents.count(),
        'total_value': documents.aggregate(total=Sum('price'))['total'] or 0,
    }
    return render(request, 'documents/admin_user_documents.html', context)

@login_required
def admin_user_orders(request, user_id):
    """Admin view user's orders"""
    if not request.user.is_superuser:
        return redirect("home")
    
    user = get_object_or_404(CustomUser, id=user_id)
    orders = Order.objects.filter(buyer=user).order_by("-created_at")
    
    context = {
        'user': user,
        'orders': orders.select_related('document', 'document__seller'),
        'total_orders': orders.count(),
        'total_spent': orders.filter(status='paid').aggregate(total=Sum('amount_paid'))['total'] or 0,
        'pending_orders': orders.filter(status='pending').count(),
        'completed_orders': orders.filter(status='paid').count(),
    }
    return render(request, 'documents/admin_user_orders.html', context)

@login_required
def admin_user_reviews(request, user_id):
    """Admin view user's reviews"""
    if not request.user.is_superuser:
        return redirect("home")
    
    user = get_object_or_404(CustomUser, id=user_id)
    reviews = Review.objects.filter(reviewer=user).order_by("-created_at")
    
    context = {
        'user': user,
        'reviews': reviews.select_related('document', 'document__seller'),
        'total_reviews': reviews.count(),
        'average_rating': reviews.aggregate(avg=Avg('rating'))['avg'] or 0,
    }
    return render(request, 'documents/admin_user_reviews.html', context)

@login_required
def admin_edit_document(request, pk):
    """Admin edit document (can edit any document)"""
    if not request.user.is_superuser:
        return redirect("home")
    
    document = get_object_or_404(Document, pk=pk)

    if request.method == "POST":
        form = DocumentUploadForm(request.POST, request.FILES, instance=document)
        if form.is_valid():
            doc = form.save(commit=False)
            uploaded_file = request.FILES.get("file")

            if uploaded_file:
                # Generate preview and page count for new uploaded file
                preview_text, pages = generate_preview(uploaded_file, doc.description)
                doc.preview_text = preview_text
                doc.pages = pages

            doc.save()

            messages.success(request, f"✅ Document '{doc.title}' updated successfully.")
            return redirect("documents:admin_user_documents", doc.seller.id)
    else:
        form = DocumentUploadForm(instance=document)

    context = {
        "form": form, 
        "document": document,
        "is_admin_edit": True,
        "back_url": reverse("documents:admin_user_documents", args=[document.seller.id])
    }
    return render(request, "documents/admin_edit_document.html", context)

@login_required
def admin_delete_document(request, pk):
    """Admin delete document (can delete any document)"""
    if not request.user.is_superuser:
        return redirect("home")
    
    document = get_object_or_404(Document, pk=pk)
    seller_id = document.seller.id
    
    if request.method == "POST":
        title = document.title
        document.delete()
        messages.success(request, f"✅ Document '{title}' deleted successfully.")
        return redirect("documents:admin_user_documents", seller_id)
    
    context = {
        "document": document,
        "back_url": reverse("documents:admin_user_documents", args=[seller_id])
    }
    return render(request, "documents/admin_delete_document.html", context)

@login_required
def admin_manage_documents(request):
    """Admin document management page"""
    if not request.user.is_superuser:
        return redirect("home")
    
    documents = Document.objects.all().order_by("-created_at")
    
    # Filter by document type
    document_type = request.GET.get('document_type')
    if document_type:
        documents = documents.filter(document_type=document_type)
    
    # Filter by academic level
    academic_level = request.GET.get('academic_level')
    if academic_level:
        documents = documents.filter(academic_level=academic_level)
    
    # Filter by category
    category = request.GET.get('category')
    if category:
        documents = documents.filter(category_id=category)
    
    # Search functionality
    search = request.GET.get('search')
    if search:
        documents = documents.filter(
            Q(title__icontains=search) |
            Q(description__icontains=search) |
            Q(seller__username__icontains=search) |
            Q(subject__icontains=search) |
            Q(tags__icontains=search)
        )
    
    # Calculate statistics
    total_docs = Document.objects.count()
    docs_by_type = Document.objects.values('document_type').annotate(count=Count('id'))
    docs_by_level = Document.objects.values('academic_level').annotate(count=Count('id'))
    
    context = {
        'documents': documents.select_related('seller', 'category'),
        'categories': Category.objects.all(),
        'total_documents': total_docs,
        'document_types': Document.DOCUMENT_TYPES,
        'academic_levels': Document.ACADEMIC_LEVELS,
        'docs_by_type': dict(docs_by_type),
        'docs_by_level': dict(docs_by_level),
    }
    return render(request, 'documents/admin_manage_documents.html', context)

@login_required
def admin_manage_reviews(request):
    """Admin review management page"""
    if not request.user.is_superuser:
        return redirect("home")
    
    reviews = Review.objects.all().order_by("-created_at")
    
    # Filter by rating
    rating_filter = request.GET.get('rating')
    if rating_filter:
        reviews = reviews.filter(rating=rating_filter)
    
    context = {
        'reviews': reviews.select_related('reviewer', 'document'),
        'total_reviews': reviews.count(),
        'average_rating': reviews.aggregate(avg=Avg('rating'))['avg'] or 0,
    }
    return render(request, 'documents/admin_manage_reviews.html', context)

@login_required
def admin_manage_payments(request):
    """Admin payment management page"""
    if not request.user.is_superuser:
        return redirect("home")
    
    # Get orders with payments (more comprehensive than just payments)
    orders = Order.objects.all().order_by("-created_at")
    
    # Filter by status
    status = request.GET.get('status')
    if status:
        orders = orders.filter(status=status)
    
    # Search functionality
    search_query = request.GET.get('search', '').strip()
    if search_query:
        orders = orders.filter(
            Q(document__title__icontains=search_query) |
            Q(buyer__username__icontains=search_query) |
            Q(buyer__email__icontains=search_query) |
            Q(document__seller__username__icontains=search_query) |
            Q(payment_method__icontains=search_query)
        )
    
    # Pagination
    paginator = Paginator(orders, 10)  # 10 items per page
    page_number = request.GET.get('page')
    detailed_orders = paginator.get_page(page_number)
    
    # Get payment statistics
    payments = Payment.objects.all()
    total_revenue = payments.filter(status='success').aggregate(
        total=Sum('amount')
    )['total'] or 0
    
    context = {
        'detailed_orders': detailed_orders,
        'payments': payments.select_related('order', 'order__buyer', 'order__document'),
        'total_transactions': orders.count(),
        'total_revenue': total_revenue,
        'pending_payments': payments.filter(status='pending').count(),
        'completed_payments': payments.filter(status='success').count(),
        'failed_payments': payments.filter(status='failed').count(),
        'search_query': search_query,
        'is_paginated': detailed_orders.has_other_pages(),
        'has_previous': detailed_orders.has_previous(),
        'has_next': detailed_orders.has_next(),
        'page_number': detailed_orders.number,
        'num_pages': detailed_orders.paginator.num_pages,
    }
    return render(request, 'documents/admin_manage_payments.html', context)


@login_required
def admin_payment_details(request, order_id):
    """Return payment details for an order (admin-only, used by Manage Payments modal)."""
    if not request.user.is_superuser:
        return JsonResponse({"success": False, "error": "Forbidden"}, status=403)

    if request.method != "GET":
        return JsonResponse({"success": False, "error": "Method not allowed"}, status=405)

    order = get_object_or_404(
        Order.objects.select_related("buyer", "document", "document__seller"),
        id=order_id,
    )

    try:
        payment = order.payment
    except Payment.DoesNotExist:
        payment = None

    if payment is None:
        payment_data = None
    else:
        payment_data = {
            "payment_method": payment.payment_method,
            "status": payment.status,
            "transaction_id": payment.transaction_id,
            "amount": str(payment.amount),
            "currency": payment.currency,
            "failure_reason": payment.failure_reason,
            "created_at": payment.created_at.isoformat() if payment.created_at else None,
            "updated_at": payment.updated_at.isoformat() if payment.updated_at else None,
        }

    data = {
        "success": True,
        "order": {
            "id": order.id,
            "status": order.status,
            "created_at": order.created_at.isoformat() if order.created_at else None,
            "amount_paid": str(getattr(order, "amount_paid", "") or ""),
            "payment_method": getattr(order, "payment_method", None),
            "paypal_payment_id": getattr(order, "paypal_payment_id", None),
            "stripe_payment_intent": getattr(order, "stripe_payment_intent", None),
        },
        "buyer": {
            "username": getattr(order.buyer, "username", None) if getattr(order, "buyer", None) else None,
            "email": getattr(order.buyer, "email", None) if getattr(order, "buyer", None) else None,
        },
        "seller": {
            "username": getattr(order.document.seller, "username", None)
            if getattr(order, "document", None) and getattr(order.document, "seller", None)
            else None,
        },
        "document": {
            "title": getattr(order.document, "title", None) if getattr(order, "document", None) else None,
        },
        "payment": payment_data,
    }

    return JsonResponse(data)


@login_required
def admin_download_receipt(request, order_id):
    """Download a simple text receipt for an order (admin-only)."""
    if not request.user.is_superuser:
        return HttpResponse("Forbidden", status=403, content_type="text/plain")

    if request.method != "GET":
        return HttpResponse("Method not allowed", status=405, content_type="text/plain")

    order = get_object_or_404(
        Order.objects.select_related("buyer", "document", "document__seller"),
        id=order_id,
    )

    try:
        payment = order.payment
    except Payment.DoesNotExist:
        payment = None

    transaction_id = None
    payment_status = None
    payment_method = None
    currency = "USD"

    if payment is not None:
        transaction_id = payment.transaction_id
        payment_status = payment.status
        payment_method = payment.payment_method
        currency = payment.currency or currency

    if not transaction_id:
        transaction_id = getattr(order, "paypal_payment_id", None) or getattr(order, "stripe_payment_intent", None)

    if not payment_method:
        payment_method = getattr(order, "payment_method", None)

    amount_paid = getattr(order, "amount_paid", None)

    receipt_lines = [
        "SharpDocs - Payment Receipt",
        "==========================",
        f"Order ID: {order.id}",
        f"Order Status: {order.status}",
        f"Order Date: {order.created_at.isoformat() if order.created_at else ''}",
        "",
        f"Document: {getattr(order.document, 'title', '') if getattr(order, 'document', None) else ''}",
        f"Seller: {getattr(order.document.seller, 'username', '') if getattr(order, 'document', None) and getattr(order.document, 'seller', None) else ''}",
        f"Buyer: {getattr(order.buyer, 'username', '') if getattr(order, 'buyer', None) else ''}",
        f"Buyer Email: {getattr(order.buyer, 'email', '') if getattr(order, 'buyer', None) else ''}",
        "",
        f"Payment Method: {payment_method or ''}",
        f"Payment Status: {payment_status or ''}",
        f"Transaction ID: {transaction_id or ''}",
        f"Amount Paid: {amount_paid if amount_paid is not None else ''} {currency}",
        "",
        f"Generated At: {timezone.now().isoformat()}",
    ]

    response = HttpResponse("\n".join(receipt_lines), content_type="text/plain; charset=utf-8")
    response["Content-Disposition"] = f'attachment; filename="receipt_order_{order.id}.txt"'
    return response

@login_required
def admin_manage_withdrawals(request):
    """Admin withdrawal management page"""
    if not request.user.is_superuser:
        return redirect("home")
    
    # Handle specific withdrawal ID from URL parameter
    specific_withdrawal_id = request.GET.get('withdrawal_id')
    
    # Get all withdrawals
    withdrawals = WithdrawalRequest.objects.all().order_by("-requested_at")
    
    # Filter by status
    status = request.GET.get('status')
    if status:
        withdrawals = WithdrawalRequest.objects.filter(status=status)
    
    # If we have a specific withdrawal ID, ensure it's included
    if specific_withdrawal_id:
        specific_withdrawal = WithdrawalRequest.objects.filter(id=specific_withdrawal_id).first()
        if specific_withdrawal:
            # Check if it's already in the filtered queryset
            if not withdrawals.filter(id=specific_withdrawal_id).exists():
                # Add the specific withdrawal to the queryset (maintains queryset)
                withdrawals = withdrawals | WithdrawalRequest.objects.filter(id=specific_withdrawal_id)
            else:
                # Convert to list if we added the specific withdrawal (maintains list)
                withdrawals = list(withdrawals) + [specific_withdrawal]
        
        # Sort to maintain chronological order
        withdrawals = withdrawals.order_by("-requested_at") if isinstance(withdrawals, list) else withdrawals.order_by("-requested_at")
    
    # Calculate statistics using the final withdrawals (which includes the specific one if added)
    total_withdrawn = withdrawals.filter(status='completed').aggregate(
        total=Sum('amount')
    )['total'] or 0
    
    # Pagination
    page = request.GET.get('page', 1)
    paginator = Paginator(withdrawals, 10)  # Show 10 withdrawals per page
    page_number = int(page) if page else 1
    
    try:
        withdrawals_page = paginator.page(page_number)
    except:
        withdrawals_page = paginator.page(1)
    
    # Calculate statistics using the final withdrawals queryset (which may be a list)
    if isinstance(withdrawals, list):
        total_withdrawn = sum(w.amount for w in withdrawals if w.status == 'completed')
    else:
        total_withdrawn = withdrawals.filter(status='completed').aggregate(
            total=Sum('amount')
        )['total'] or 0
    
    # Get commission data from sales
    from sales.models import Sale
    sales = Sale.objects.all()
    total_commission = sales.aggregate(
        total=Sum('commission_amount')
    )['total'] or 0
    
    # Calculate seller earnings (net amount after commission)
    seller_earnings = sales.aggregate(
        total=Sum('net_amount')
    )['total'] or 0
    
    # Calculate commission rate statistics
    commission_stats_raw = sales.values('commission_rate').annotate(
        count=Count('id'),
        total_commission=Sum('commission_amount'),
        total_sales=Sum('gross_amount')
    ).order_by('-total_commission')
    
    # Process commission stats to add calculated percentages
    commission_stats = []
    for stat in commission_stats_raw:
        commission_rate_percentage = stat['commission_rate'] * 100
        commission_percentage = (stat['total_commission'] / stat['total_sales'] * 100) if stat['total_sales'] > 0 else 0
        
        commission_stats.append({
            'commission_rate': stat['commission_rate'],
            'commission_rate_percentage': commission_rate_percentage,
            'count': stat['count'],
            'total_commission': stat['total_commission'],
            'total_sales': stat['total_sales'],
            'commission_percentage': commission_percentage,
        })
    
    context = {
        'withdrawals': withdrawals_page,
        'total_withdrawals': paginator.count,
        'total_withdrawn': total_withdrawn,
        'pending_withdrawals': len([w for w in withdrawals if w.status == 'pending']),
        'completed_withdrawals': len([w for w in withdrawals if w.status == 'completed']),
        'failed_withdrawals': len([w for w in withdrawals if w.status == 'failed']),
        'total_withdrawn': total_withdrawn,
        'total_commission': total_commission,
        'seller_earnings': seller_earnings,
        'commission_stats': commission_stats,
        'specific_withdrawal_id': specific_withdrawal_id,
        'current_page': page_number,
        'has_previous': withdrawals_page.has_previous(),
        'has_next': withdrawals_page.has_next(),
        'previous_page': page_number - 1 if page_number > 1 else None,
        'next_page': page_number + 1 if withdrawals_page.has_next() else None,
        'num_pages': paginator.num_pages,
    }
    return render(request, 'documents/admin_manage_withdrawals.html', context)


@login_required
def admin_manage_refunds(request):
    """Admin refund/complaint management page (manual PayPal refunds with tracking)."""
    if not request.user.is_superuser:
        return redirect("home")

    from sales.models import Sale, Wallet, Transaction

    if request.method == "POST":
        refund_id = request.POST.get("refund_id")
        new_status = request.POST.get("status", "").strip()
        paypal_refund_id = request.POST.get("paypal_refund_id", "").strip() or None
        admin_notes = request.POST.get("admin_notes", "").strip() or None

        rr = get_object_or_404(RefundRequest, id=refund_id)
        if new_status not in dict(RefundRequest.STATUS_CHOICES):
            messages.error(request, "Invalid refund status.")
            return redirect("documents:admin_manage_refunds")

        # If marking refunded, require a PayPal refund id for reconciliation.
        if new_status == "refunded" and not paypal_refund_id:
            messages.error(request, "PayPal refund ID is required to mark a request as refunded.")
            return redirect("documents:admin_manage_refunds")

        with transaction.atomic():
            rr = RefundRequest.objects.select_for_update().select_related("order", "order__document").get(id=rr.id)
            order = rr.order

            # Apply status update
            rr.status = new_status
            rr.paypal_refund_id = paypal_refund_id if new_status == "refunded" else rr.paypal_refund_id
            rr.admin_notes = admin_notes
            if new_status in {"rejected", "refunded"}:
                rr.resolved_at = timezone.now()
            rr.save(update_fields=["status", "paypal_refund_id", "admin_notes", "resolved_at", "updated_at"])

            # If refunded, mark order refunded and reverse seller earnings (best-effort; should be within hold window).
            if new_status == "refunded":
                order.status = "refunded"
                order.save(update_fields=["status"])

                sale = Sale.objects.filter(order=order).select_for_update().first()
                if sale:
                    seller_wallet, _ = Wallet.objects.select_for_update().get_or_create(user=order.document.seller)

                    # Reverse commission record (commission was recorded when sale was created).
                    seller_wallet.total_commission_paid = max(
                        Decimal("0.00"),
                        Decimal(seller_wallet.total_commission_paid) - Decimal(sale.commission_amount),
                    )

                    if sale.wallet_released_at is None:
                        # Funds are still held; subtract from held amount.
                        seller_wallet.pending_balance = max(
                            Decimal("0.00"),
                            Decimal(seller_wallet.pending_balance) - Decimal(sale.net_amount),
                        )
                        seller_wallet.save(update_fields=["pending_balance", "total_commission_paid"])
                    else:
                        # Funds were released; subtract from available and total_earned.
                        # If seller already withdrew the funds, create debt that will be repaid from future earnings.
                        available = Decimal(str(seller_wallet.balance or 0))
                        reversal = Decimal(str(sale.net_amount or 0))
                        if available >= reversal:
                            seller_wallet.balance = available - reversal
                        else:
                            shortfall = reversal - available
                            seller_wallet.balance = Decimal("0.00")
                            seller_wallet.debt_balance = Decimal(str(getattr(seller_wallet, "debt_balance", 0) or 0)) + shortfall

                        seller_wallet.total_earned = max(
                            Decimal("0.00"),
                            Decimal(seller_wallet.total_earned) - Decimal(sale.net_amount),
                        )
                        seller_wallet.save(update_fields=["balance", "debt_balance", "total_earned", "total_commission_paid"])

                    Transaction.objects.create(
                        wallet=seller_wallet,
                        amount=-Decimal(sale.net_amount),
                        transaction_type="refund",
                        description=f"Sale reversed due to refund (Order #{order.id})",
                        commission_amount=Decimal("0.00"),
                        transaction_fee=Decimal("0.00"),
                        net_amount=-Decimal(sale.net_amount),
                        sale=sale,
                    )

        messages.success(request, "Refund request updated.")
        return redirect("documents:admin_manage_refunds")

    refund_requests = RefundRequest.objects.select_related("order", "buyer", "order__document", "order__document__seller").order_by("-created_at")

    status = request.GET.get("status")
    if status:
        refund_requests = refund_requests.filter(status=status)

    # Pagination
    page = request.GET.get("page", 1)
    paginator = Paginator(refund_requests, 10)
    try:
        refund_page = paginator.page(int(page))
    except Exception:
        refund_page = paginator.page(1)

    return render(
        request,
        "documents/admin_manage_refunds.html",
        {
            "refund_requests": refund_page,
            "status_filter": status or "",
            "status_choices": RefundRequest.STATUS_CHOICES,
        },
    )


@login_required
def seller_refunds(request):
    """Seller view of refund/complaint requests for their documents."""
    if not getattr(request.user, "is_seller", False):
        return redirect("home")

    refund_requests = (
        RefundRequest.objects.select_related("order", "buyer", "order__document")
        .filter(order__document__seller=request.user)
        .order_by("-created_at")
    )

    status = request.GET.get("status")
    if status:
        refund_requests = refund_requests.filter(status=status)

    page = request.GET.get("page", 1)
    paginator = Paginator(refund_requests, 10)
    try:
        refund_page = paginator.page(int(page))
    except Exception:
        refund_page = paginator.page(1)

    return render(
        request,
        "documents/seller_refunds.html",
        {
            "refund_requests": refund_page,
            "status_filter": status or "",
            "status_choices": RefundRequest.STATUS_CHOICES,
        },
    )
    """Admin security log page"""
    if not request.user.is_superuser:
        return redirect("home")
    
    logs = SecurityLog.objects.all().order_by("-created_at")
    
    # Filter by event type
    event_type = request.GET.get('event_type')
    if event_type:
        logs = logs.filter(event_type=event_type)
    
    # Filter by severity
    severity = request.GET.get('severity')
    if severity:
        logs = logs.filter(severity=severity)
    
    context = {
        'logs': logs.select_related('user'),
        'total_logs': logs.count(),
        'critical_events': logs.filter(severity='critical').count(),
        'event_types': SecurityLog.EVENT_TYPES,
        'severity_levels': ['low', 'medium', 'high', 'critical'],
    }
    return render(request, 'documents/admin_security_log.html', context)

@login_required
def admin_security_log(request):
    """Admin security log page"""
    if not request.user.is_superuser:
        return redirect("home")
    
    logs = SecurityLog.objects.all().order_by("-created_at")
    
    # Filter by event type
    event_type = request.GET.get('event_type')
    if event_type:
        logs = logs.filter(event_type=event_type)
    
    # Filter by severity
    severity = request.GET.get('severity')
    if severity:
        logs = logs.filter(severity=severity)
    
    context = {
        'logs': logs.select_related('user'),
        'total_logs': logs.count(),
        'critical_events': logs.filter(severity='critical').count(),
        'event_types': SecurityLog.EVENT_TYPES,
        'severity_levels': ['low', 'medium', 'high', 'critical'],
    }
    return render(request, 'documents/admin_security_log.html', context)

@login_required
def admin_identity_verifications(request):
    """Admin identity verification management page"""
    if not request.user.is_superuser:
        return redirect("home")
    
    verifications = IdentityVerification.objects.all().order_by("-created_at")
    
    # Filter by status
    status = request.GET.get('status')
    if status:
        verifications = verifications.filter(status=status)
    
    context = {
        'verifications': verifications.select_related('user', 'verified_by'),
        'total_verifications': verifications.count(),
        'pending_verifications': verifications.filter(status='pending').count(),
        'approved_verifications': verifications.filter(status='approved').count(),
        'rejected_verifications': verifications.filter(status='rejected').count(),
        'verification_types': IdentityVerification.VERIFICATION_TYPES,
    }
    return render(request, 'documents/admin_identity_verifications.html', context)

@login_required
def admin_commission_tracking(request):
    """Admin commission tracking page"""
    if not request.user.is_superuser:
        return redirect("home")
    
    from sales.models import Sale
    from datetime import datetime, timedelta
    
    # Get all commission data
    sales = Sale.objects.all().select_related('document', 'seller', 'buyer')
    
    # Total commission
    total_commission = sales.aggregate(
        total=Sum('commission_amount')
    )['total'] or 0
    
    # Total sales for calculations
    total_sales = sales.aggregate(
        total=Sum('gross_amount')
    )['total'] or 0
    
    # Commission transactions count
    commission_transactions = sales.count()
    
    # This month's commission
    current_month_start = datetime.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    monthly_commission = sales.filter(
        created_at__gte=current_month_start
    ).aggregate(
        total=Sum('commission_amount')
    )['total'] or 0
    
    # Commission stats by rate
    commission_stats_raw = sales.values('commission_rate').annotate(
        count=Count('id'),
        total_commission=Sum('commission_amount'),
        total_sales=Sum('gross_amount')
    ).order_by('-total_commission')
    
    commission_stats = []
    for stat in commission_stats_raw:
        commission_rate_percentage = stat['commission_rate'] * 100
        commission_percentage = (stat['total_commission'] / stat['total_sales'] * 100) if stat['total_sales'] > 0 else 0
        
        commission_stats.append({
            'commission_rate': stat['commission_rate'],
            'commission_rate_percentage': commission_rate_percentage,
            'count': stat['count'],
            'total_commission': stat['total_commission'],
            'total_sales': stat['total_sales'],
            'commission_percentage': commission_percentage,
        })
    
    # Monthly commission trend (last 12 months)
    monthly_commission_trend = []
    for i in range(12):
        month_start = datetime.now().replace(day=1) - timedelta(days=30*i)
        month_end = month_start.replace(day=28) + timedelta(days=4)
        month_end = month_end - timedelta(days=month_end.day)
        
        month_commission = sales.filter(
            created_at__gte=month_start,
            created_at__lte=month_end
        ).aggregate(
            total=Sum('commission_amount'),
            count=Count('id')
        )
        
        month_name = month_start.strftime('%b %Y')
        monthly_commission_trend.append({
            'month': month_name,
            'commission': month_commission['total'] or 0,
            'transactions': month_commission['count'] or 0
        })
    
    # Recent commission transactions
    recent_commission_transactions = []
    for sale in sales.order_by('-created_at')[:20]:
        recent_commission_transactions.append({
            'id': sale.id,
            'created_at': sale.created_at,
            'document': sale.document,
            'seller': sale.seller,
            'buyer': sale.buyer,
            'gross_amount': sale.gross_amount,
            'commission_rate': sale.commission_rate,
            'commission_rate_percentage': sale.commission_rate * 100,
            'commission_amount': sale.commission_amount,
            'net_amount': sale.net_amount,
        })
    
    # Top sellers by commission generated
    top_sellers_by_commission = sales.values('seller__username').annotate(
        sales_count=Count('id'),
        total_revenue=Sum('gross_amount'),
        total_commission=Sum('commission_amount')
    ).order_by('-total_commission')[:10]
    
    # Calculate additional stats
    average_commission = total_commission / commission_transactions if commission_transactions > 0 else 0
    commission_rate_percentage = (total_commission / total_sales * 100) if total_sales > 0 else 0
    commission_percentage_of_revenue = (total_commission / total_sales * 100) if total_sales > 0 else 0
    
    # Find peak commission month
    peak_commission_month = max(monthly_commission_trend, key=lambda x: x['commission']) if monthly_commission_trend else {'month': 'N/A', 'commission': 0}
    
    # Process commission stats with calculated values
    processed_commission_stats = []
    for stat in commission_stats:
        commission_rate_percentage = stat['commission_rate'] * 100
        commission_percentage = (stat['total_commission'] / stat['total_sales'] * 100) if stat['total_sales'] > 0 else 0
        average_commission_per_sale = stat['total_commission'] / stat['count'] if stat['count'] > 0 else 0
        
        processed_commission_stats.append({
            'commission_rate': stat['commission_rate'],
            'commission_rate_percentage': commission_rate_percentage,
            'count': stat['count'],
            'total_commission': stat['total_commission'],
            'total_sales': stat['total_sales'],
            'commission_percentage': commission_percentage,
            'average_commission_per_sale': average_commission_per_sale,
        })
    
    context = {
        'total_commission': total_commission,
        'monthly_commission': monthly_commission,
        'commission_transactions': commission_transactions,
        'total_sales': total_sales,
        'commission_stats': processed_commission_stats,
        'monthly_commission_trend': monthly_commission_trend[::-1],  # Reverse to show oldest to newest
        'recent_commission_transactions': recent_commission_transactions,
        'top_sellers_by_commission': top_sellers_by_commission,
        'average_commission': average_commission,
        'commission_rate_percentage': commission_rate_percentage,
        'commission_percentage_of_revenue': commission_percentage_of_revenue,
        'peak_commission_month': peak_commission_month,
    }
    
    return render(request, 'documents/admin_commission_tracking.html', context)

@login_required
def admin_view_financials(request):
    """Admin financial overview page"""
    if not request.user.is_superuser:
        return redirect("home")
    
    # Get order statistics first (more reliable)
    orders = Order.objects.all().order_by("-created_at")
    total_orders = orders.count()
    completed_orders = orders.filter(status='paid').count()
    
    # Calculate revenue from orders directly
    total_revenue = orders.filter(status='paid').aggregate(
        total=Sum('amount_paid')
    )['total'] or 0
    
    # Get commission data from sales
    from sales.models import Sale
    sales = Sale.objects.all()
    total_commission = sales.aggregate(
        total=Sum('commission_amount')
    )['total'] or 0
    
    # VALIDATION: Ensure commission doesn't exceed revenue
    if total_commission > total_revenue:
        print(f"WARNING: Commission (${total_commission:,.2f}) exceeds revenue (${total_revenue:,.2f})")
        print("This indicates data inconsistency. Running data synchronization...")
        try:
            from .financial_utils import synchronize_financial_data
            synchronize_financial_data()
            # Recalculate after sync
            total_commission = sales.aggregate(
                total=Sum('commission_amount')
            )['total'] or 0
            print(f"Post-sync commission: ${total_commission:,.2f}")
        except Exception as e:
            print(f"Error during sync: {e}")
    
    # Calculate seller earnings from sales data
    seller_earnings = sales.aggregate(
        total=Sum('net_amount')
    )['total'] or 0
    
    # Get payment statistics for additional info
    payments = Payment.objects.all().order_by("-created_at")
    
    # Get withdrawal statistics
    withdrawals = WithdrawalRequest.objects.all().order_by("-requested_at")
    total_withdrawn = withdrawals.filter(status='completed').aggregate(
        total=Sum('amount')
    )['total'] or 0
    
    # Get recent transactions (last 20)
    recent_payments = payments[:20]
    recent_withdrawals = withdrawals[:20]
    recent_orders = orders[:20]
    
    # Get detailed transaction data with document information - with pagination and search
    search_query = request.GET.get('search', '').strip()
    detailed_orders_queryset = Order.objects.filter(status='paid').select_related(
        'buyer', 'document', 'document__seller'
    ).order_by("-created_at")
    
    # Apply search filter
    if search_query:
        detailed_orders_queryset = detailed_orders_queryset.filter(
            Q(document__title__icontains=search_query) |
            Q(buyer__username__icontains=search_query) |
            Q(buyer__email__icontains=search_query) |
            Q(document__seller__username__icontains=search_query) |
            Q(payment_method__icontains=search_query)
        )
    
    # Pagination
    paginator = Paginator(detailed_orders_queryset, 10)  # 10 items per page
    page_number = request.GET.get('page')
    detailed_orders = paginator.get_page(page_number)
    
    # Get withdrawal requests with seller information - with pagination and search
    withdrawal_search_query = request.GET.get('withdrawal_search', '').strip()
    withdrawal_requests_queryset = WithdrawalRequest.objects.select_related(
        'user', 'withdrawal_method'
    ).order_by("-requested_at")
    
    # Apply search filter to withdrawal requests
    if withdrawal_search_query:
        withdrawal_requests_queryset = withdrawal_requests_queryset.filter(
            Q(user__username__icontains=withdrawal_search_query) |
            Q(user__email__icontains=withdrawal_search_query) |
            Q(withdrawal_method__method_type__icontains=withdrawal_search_query) |
            Q(status__icontains=withdrawal_search_query)
        )
    
    # Pagination for withdrawal requests
    withdrawal_paginator = Paginator(withdrawal_requests_queryset, 10)  # 10 items per page
    withdrawal_page_number = request.GET.get('withdrawal_page')
    withdrawal_requests = withdrawal_paginator.get_page(withdrawal_page_number)
    
    # Monthly revenue (last 6 months) from orders
    from datetime import datetime, timedelta
    monthly_revenue = []
    for i in range(6):
        month_start = datetime.now().replace(day=1) - timedelta(days=30*i)
        month_end = month_start.replace(day=28) + timedelta(days=4)
        month_end = month_end - timedelta(days=month_end.day)
        
        month_revenue = orders.filter(
            status='paid',
            created_at__gte=month_start,
            created_at__lte=month_end
        ).aggregate(total=Sum('amount_paid'))['total'] or 0
        
        month_name = month_start.strftime('%B %Y')
        monthly_revenue.append({
            'month': month_name,
            'revenue': month_revenue
        })
    
    # Top sellers by revenue
    top_sellers = orders.filter(status='paid').values(
        'document__seller__username'
    ).annotate(
        total_revenue=Sum('amount_paid'),
        order_count=Count('id')
    ).order_by('-total_revenue')[:10]
    
    # Top documents by revenue
    top_documents_search_query = request.GET.get('top_documents_search', '').strip()
    top_documents_queryset = orders.filter(status='paid').values(
        'document__title', 'document__seller__username'
    ).annotate(
        total_revenue=Sum('amount_paid'),
        order_count=Count('id')
    ).order_by('-total_revenue')
    
    # Pagination for top documents
    top_documents_paginator = Paginator(top_documents_queryset, 10)  # 10 items per page
    top_documents_page_number = request.GET.get('top_documents_page')
    top_documents = top_documents_paginator.get_page(top_documents_page_number)
    
    # Payment method breakdown from orders (more reliable)
    payment_methods = orders.filter(status='paid').values('payment_method').annotate(
        count=Count('id'),
        total=Sum('amount_paid')
    ).order_by('-total')
    
    # Withdrawal status breakdown - with pagination and search
    withdrawal_status_search_query = request.GET.get('withdrawal_status_search', '').strip()
    withdrawal_status_queryset = withdrawals.values('status').annotate(
        count=Count('id'),
        total=Sum('amount')
    ).order_by('-total')
    
    # Apply search filter to withdrawal status
    if withdrawal_status_search_query:
        withdrawal_status_queryset = withdrawal_status_queryset.filter(
            Q(status__icontains=withdrawal_status_search_query)
        )
    
    # Pagination for withdrawal status
    withdrawal_status_paginator = Paginator(withdrawal_status_queryset, 10)  # 10 items per page
    withdrawal_status_page_number = request.GET.get('withdrawal_status_page')
    withdrawal_status = withdrawal_status_paginator.get_page(withdrawal_status_page_number)
    
    # Calculate commission rate statistics
    commission_stats_raw = sales.values('commission_rate').annotate(
        count=Count('id'),
        total_commission=Sum('commission_amount'),
        total_sales=Sum('gross_amount')
    ).order_by('-total_commission')
    
    # Process commission stats to add calculated percentages
    commission_stats = []
    for stat in commission_stats_raw:
        commission_rate_percentage = stat['commission_rate'] * 100
        commission_percentage = (stat['total_commission'] / stat['total_sales'] * 100) if stat['total_sales'] > 0 else 0
        
        commission_stats.append({
            'commission_rate': stat['commission_rate'],
            'commission_rate_percentage': commission_rate_percentage,
            'count': stat['count'],
            'total_commission': stat['total_commission'],
            'total_sales': stat['total_sales'],
            'commission_percentage': commission_percentage,
        })
    
    context = {
        'total_revenue': total_revenue,
        'total_commission': total_commission,
        'seller_earnings': seller_earnings,
        'total_withdrawn': total_withdrawn,
        'net_profit': total_revenue - total_withdrawn,
        'total_orders': total_orders,
        'completed_orders': completed_orders,
        'order_completion_rate': (completed_orders / total_orders * 100) if total_orders > 0 else 0,
        'monthly_revenue': monthly_revenue[::-1],  # Reverse to show oldest to newest
        'pending_payments': payments.filter(status='pending').count(),
        'pending_withdrawals': withdrawals.filter(status='pending').count(),
        'recent_payments': recent_payments,
        'recent_withdrawals': recent_withdrawals,
        'recent_orders': recent_orders,
        'detailed_orders': detailed_orders,
        'withdrawal_requests': withdrawal_requests,
        'top_sellers': top_sellers,
        'top_documents': top_documents,
        'top_documents_total': top_documents_queryset.count(),
        'payment_methods': payment_methods,
        'withdrawal_status': withdrawal_status,
        'commission_stats': commission_stats,
        'search_query': search_query,
        'withdrawal_search_query': withdrawal_search_query,
        'top_documents_search_query': top_documents_search_query,
        'withdrawal_status_search_query': withdrawal_status_search_query,
        'is_paginated': detailed_orders.has_other_pages(),
        'has_previous': detailed_orders.has_previous(),
        'has_next': detailed_orders.has_next(),
        'page_number': detailed_orders.number,
        'num_pages': detailed_orders.paginator.num_pages,
        'withdrawal_is_paginated': withdrawal_requests.has_other_pages(),
        'withdrawal_has_previous': withdrawal_requests.has_previous(),
        'withdrawal_has_next': withdrawal_requests.has_next(),
        'withdrawal_page_number': withdrawal_requests.number,
        'withdrawal_num_pages': withdrawal_requests.paginator.num_pages,
        'top_documents_is_paginated': top_documents.has_other_pages(),
        'top_documents_has_previous': top_documents.has_previous(),
        'top_documents_has_next': top_documents.has_next(),
        'top_documents_page_number': top_documents.number,
        'top_documents_num_pages': top_documents.paginator.num_pages,
        'withdrawal_status_is_paginated': withdrawal_status.has_other_pages(),
        'withdrawal_status_has_previous': withdrawal_status.has_previous(),
        'withdrawal_status_has_next': withdrawal_status.has_next(),
        'withdrawal_status_page_number': withdrawal_status.number,
        'withdrawal_status_num_pages': withdrawal_status.paginator.num_pages,
        'withdrawal_status_total': withdrawal_status.paginator.count,
        # Total transactions should include all orders, not just paid ones
        'total_transactions': total_orders,
    }
    return render(request, 'documents/admin_view_financials.html', context)

@login_required
def buyer_dashboard(request):
    """
    Buyer dashboard with access to all buyer functionality
    """
    # Get buyer's data
    orders = Order.objects.filter(buyer=request.user).select_related("document", "document__seller")
    purchased_documents = Document.objects.filter(
        orders__buyer=request.user, 
        orders__status="paid"
    ).distinct()
    
    # Get buyer's reviews
    given_reviews = Review.objects.filter(reviewer=request.user).select_related("document")
    
    # Get buyer's security activities
    recent_activities = []
    try:
        recent_activities = list(SecurityLog.objects.filter(user=request.user).order_by("-timestamp")[:10])
    except:
        recent_activities = []
    
    # Get education data
    study_sessions = []
    if StudySession:
        study_sessions = list(StudySession.objects.filter(user=request.user).order_by("-created_at")[:5])
    
    context = {
        # Purchase Statistics
        "total_purchases": orders.filter(status="paid").count(),
        "total_spent": orders.filter(status="paid").aggregate(
            total=Sum(F("amount_paid"))
        )["total"] or 0,
        "pending_orders": orders.filter(status="pending").count(),
        
        # Documents
        "purchased_documents": purchased_documents[:6],
        "recent_orders": orders.order_by("-created_at")[:5],
        
        # Reviews
        "given_reviews": given_reviews[:5],
        "reviews_count": given_reviews.count(),
        
        # Education
        "study_sessions": study_sessions,
        "study_time_today": 0,  # Default if StudySession not available
        # if StudySession else StudySession.objects.filter(
        #     user=request.user,
        #     created_at__date=timezone.now().date()
        # ).aggregate(total=Sum("duration"))["total"] or 0,
        
        # Security
        "recent_activities": recent_activities,
        "last_login": recent_activities[0] if recent_activities else None,
        
        # Quick Actions
        "unread_notifications": 0,  # Default if Notification not available
        # if Notification else Notification.objects.filter(
        #     user=request.user, 
        #     is_read=False
        # ).count(),
    }
    
    return render(request, "documents/buyer_dashboard.html", context)


# -------------------------
# Purchases & Downloads (fixed)
# -------------------------


@login_required
def download_owner_document(request, document_id):
    """
    Stream a document for the document owner.
    """
    document = get_object_or_404(Document, id=document_id, seller=request.user)

    if not document.file:
        messages.error(request, "⚠️ No file is associated with this document.")
        return render(request, "documents/download_failed.html", {"document": document})

    download_filename = os.path.basename(document.file.name or "") or f"{document.slug or document.id}"
    content_type, _ = mimetypes.guess_type(download_filename)

    try:
        file_handle = document.file.open("rb")
    except FileNotFoundError:
        logger.warning("Owner download: file missing on storage (document_id=%s, name=%s)", document.id, document.file.name)
        messages.error(request, "⚠️ File not found on server. Please re-upload the document.")
        return render(request, "documents/download_failed.html", {"document": document})
    except Exception:
        logger.exception("Owner download: failed to open file (document_id=%s)", document.id)
        messages.error(request, "⚠️ Download failed. Please try again later.")
        return render(request, "documents/download_failed.html", {"document": document})

    response = FileResponse(
        file_handle,
        as_attachment=True,
        filename=download_filename,
        content_type=content_type or "application/octet-stream",
    )

    DownloadLog.objects.create(
        user=request.user,
        document=document,
        ip_address=request.META.get("REMOTE_ADDR"),
        user_agent=request.META.get("HTTP_USER_AGENT", ""),
    )
    return response

@login_required
def download_document(request, order_id):
    """
    Stream a purchased document.
    """
    order = get_object_or_404(Order, id=order_id, buyer=request.user)
    if order.status != "paid":
        messages.error(request, "⚠️ This order is not marked as paid yet. Please try again shortly.")
        return render(request, "documents/download_failed.html", {"document": order.document})
    document = order.document

    if not document.file:
        messages.error(request, "⚠️ File not found for this document.")
        return render(request, "documents/download_failed.html", {"document": document})

    download_filename = os.path.basename(document.file.name or "") or f"{document.slug or document.id}"
    content_type, _ = mimetypes.guess_type(download_filename)

    try:
        file_handle = document.file.open("rb")
    except FileNotFoundError:
        logger.warning(
            "Buyer download: file missing on storage (order_id=%s, document_id=%s, name=%s)",
            order.id,
            document.id,
            document.file.name,
        )
        messages.error(request, "⚠️ File not found on server. Please contact support or try again later.")
        return render(request, "documents/download_failed.html", {"document": document})
    except Exception:
        logger.exception("Buyer download: failed to open file (order_id=%s)", order.id)
        messages.error(request, "⚠️ Download failed. Please try again later.")
        return render(request, "documents/download_failed.html", {"document": document})

    response = FileResponse(
        file_handle,
        as_attachment=True,
        filename=download_filename,
        content_type=content_type or "application/octet-stream",
    )

    DownloadLog.objects.create(
        user=request.user,
        document=document,
        ip_address=request.META.get("REMOTE_ADDR"),
        user_agent=request.META.get("HTTP_USER_AGENT", ""),
    )
    return response

@login_required
def my_purchases(request):
    """
    Show all purchased documents with links to the Django streaming download.
    Users can redownload files at any time.
    """
    orders = Order.objects.filter(buyer=request.user, status="paid").select_related("document")

    given_reviews = set(
        Review.objects.filter(reviewer=request.user, document_id__in=orders.values_list("document_id", flat=True))
        .values_list("document_id", flat=True)
    )

    refund_requests = {
        rr.order_id: rr
        for rr in RefundRequest.objects.filter(buyer=request.user, order_id__in=orders.values_list("id", flat=True))
    }
    purchases = []

    for order in orders:
        document = order.document
        if not document.file:
            continue

        is_reviewed = document.id in given_reviews
        refund_request = refund_requests.get(order.id)

        # Refund window: 14 days from purchase time (aligned with the holding period).
        refund_window_days = 14
        can_request_refund = (timezone.now() - order.created_at).days <= refund_window_days and refund_request is None

        purchases.append({
            "order": order,
            # link to our streaming download view
            "download_url": reverse("documents:download_document", args=[order.id]),
            "document_title": document.title,
            "document_author": document.seller.username,
            "document_description": document.description,  # Add document description
            "document_price": document.price,  # Add document price
            "is_reviewed": is_reviewed,
            "refund_request": refund_request,
            "can_request_refund": can_request_refund,
            "refund_window_days": refund_window_days,
        })

    if not purchases:
        messages.info(request, "You haven’t purchased any documents or files are unavailable.")

    unreviewed_count = len([p for p in purchases if not p["is_reviewed"]])
    return render(
        request,
        "documents/my_purchases.html",
        {"purchases": purchases, "unreviewed_count": unreviewed_count},
    )


@login_required
def request_refund(request, order_id):
    """
    Buyer creates a refund/complaint request for a paid order.

    Refunds are tracked in-app but performed manually via PayPal by an admin (who records the PayPal refund ID).
    """
    order = get_object_or_404(Order, id=order_id, buyer=request.user)
    if order.status != "paid":
        messages.error(request, "Refund requests are only available for paid orders.")
        return redirect("documents:my_purchases")

    # 14-day refund window
    refund_window_days = 14
    if (timezone.now() - order.created_at).days > refund_window_days:
        messages.error(request, f"Refund window expired. Refunds are available within {refund_window_days} days of purchase.")
        return redirect("documents:my_purchases")

    if hasattr(order, "refund_request"):
        messages.info(request, "A refund request already exists for this purchase.")
        return redirect("documents:my_purchases")

    if request.method == "POST":
        form = RefundRequestForm(request.POST)
        if form.is_valid():
            rr = form.save(commit=False)
            rr.order = order
            rr.buyer = request.user
            rr.status = "open"
            rr.save()
            messages.success(request, "Refund request submitted. Support will review it shortly.")
            return redirect("documents:my_purchases")
    else:
        form = RefundRequestForm()

    # Download status (shown to admin later; also useful context for buyer)
    downloaded = DownloadLog.objects.filter(user=request.user, document=order.document).exists()

    return render(
        request,
        "documents/request_refund.html",
        {"order": order, "form": form, "downloaded": downloaded, "refund_window_days": refund_window_days},
    )


# -------------------------
# Orders / Checkout
# -------------------------

@login_required
def create_order(request, slug):
    document = get_object_or_404(Document, slug=slug)

    if document.seller == request.user:
        messages.error(request, "❌ You cannot purchase your own document.")
        return redirect("documents:document_detail", slug=slug)

    if request.method == "POST":
        payment_method = request.POST.get("payment_method", "stripe")
        currency = request.POST.get("currency", "usd")

        order = Order.objects.create(
            buyer=request.user,
            document=document,
            payment_method=payment_method,
            currency=currency,
            status="pending",
            amount_paid=document.price,
        )

        # Send notification to admin about new purchase
        try:
            send_new_purchase_notification(order)
        except Exception as e:
            # Don't fail order creation if email fails
            print(f"Failed to send new purchase notification: {e}")

        if payment_method == "stripe":
            return redirect("payments:stripe_checkout", order_id=order.id)
        elif payment_method == "paypal":
            return redirect("payments:paypal_checkout", order_id=order.id)
        else:
            messages.error(request, "Invalid payment method.")
            return redirect("documents:document_detail", slug=slug)

    return redirect("documents:document_detail", slug=slug)


# Service Worker View
def service_worker(request):
    """Serve the service worker file"""
    sw_content = """// Service Worker for SharpDocs
const CACHE_NAME = 'sharpdocs-v1';
const urlsToCache = [
  '/',
  '/static/css/style.css',
  '/static/js/main.js',
  '/manifest.json'
];

// Install event - cache resources
self.addEventListener('install', function(event) {
  event.waitUntil(
    caches.open(CACHE_NAME)
      .then(function(cache) {
        return cache.addAll(urlsToCache);
      })
  );
});

// Fetch event - serve from cache when offline
self.addEventListener('fetch', function(event) {
  event.respondWith(
    caches.match(event.request)
      .then(function(response) {
        // Cache hit - return response
        if (response) {
          return response;
        }

        return fetch(event.request).then(
          function(response) {
            // Check if valid response
            if(!response || response.status !== 200 || response.type !== 'basic') {
              return response;
            }

            // Clone response
            var responseToCache = response.clone();

            caches.open(CACHE_NAME)
              .then(function(cache) {
                cache.put(event.request, responseToCache);
              });

            return response;
          }
        );
      })
    );
});

// Activate event - clean up old caches
self.addEventListener('activate', function(event) {
  event.waitUntil(
    caches.keys().then(function(cacheNames) {
      return Promise.all(
        cacheNames.map(function(cacheName) {
          if (cacheName !== CACHE_NAME) {
            return caches.delete(cacheName);
          }
        })
      );
    })
  );
});"""
    
    return HttpResponse(sw_content, content_type='application/javascript')


# Admin Notifications Views
@login_required
@user_passes_test(lambda u: u.is_superuser)
def check_new_notifications(request):
    """Check for new notifications since last check"""
    from withdrawals.models import AdminNotification
    
    try:
        # Get notifications from last 5 minutes
        since = timezone.now() - timezone.timedelta(minutes=5)
        notifications = AdminNotification.objects.filter(
            created_at__gte=since,
            is_read=False
        ).order_by('-created_at')[:5]
        
        # Serialize notifications
        notification_data = []
        for notification in notifications:
            notification_data.append({
                'id': str(notification.id),
                'title': notification.title,
                'message': notification.message,
                'notification_type': notification.notification_type,
                'priority': notification.priority,
                'created_at': notification.created_at.isoformat(),
                'withdrawal_request': str(notification.withdrawal_request.id) if notification.withdrawal_request else None
            })
        
        return JsonResponse({
            'has_new': len(notification_data) > 0,
            'notifications': notification_data
        })
    except Exception as e:
        return JsonResponse({'has_new': False, 'error': str(e)})


@login_required
@user_passes_test(lambda u: u.is_superuser)
def admin_notifications(request):
    """Admin notifications dashboard"""
    
    # Get notification filters
    notification_type = request.GET.get('notification_type', '')
    priority = request.GET.get('priority', '')
    status = request.GET.get('status', '')
    time_range = request.GET.get('time_range', '')
    
    # Build query
    from withdrawals.models import AdminNotification
    
    notifications = AdminNotification.objects.all()
    
    # Apply filters
    if notification_type:
        notifications = notifications.filter(notification_type=notification_type)
    
    if priority:
        notifications = notifications.filter(priority=priority)
    
    if status == 'unread':
        notifications = notifications.filter(is_read=False)
    elif status == 'read':
        notifications = notifications.filter(is_read=True)
    
    # Apply time filter
    if time_range:
        hours = int(time_range)
        since = timezone.now() - timezone.timedelta(hours=hours)
        notifications = notifications.filter(created_at__gte=since)
    
    # Order by created_at descending
    notifications = notifications.order_by('-created_at')
    
    # Pagination
    paginator = Paginator(notifications, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Calculate statistics
    unread_count = AdminNotification.objects.filter(is_read=False).count()
    urgent_count = AdminNotification.objects.filter(priority='urgent', is_read=False).count()
    today_count = AdminNotification.objects.filter(
        created_at__date=timezone.now().date()
    ).count()
    total_count = AdminNotification.objects.count()
    
    # Get filter options
    notification_types = AdminNotification.NOTIFICATION_TYPES
    priority_levels = AdminNotification.PRIORITY_LEVELS
    
    context = {
        'notifications': page_obj,
        'page_obj': page_obj,
        'is_paginated': page_obj.has_other_pages(),
        'unread_count': unread_count,
        'urgent_count': urgent_count,
        'today_count': today_count,
        'total_count': total_count,
        'notification_types': notification_types,
        'priority_levels': priority_levels,
    }
    
    return render(request, 'documents/admin_notifications.html', context)


@login_required
@user_passes_test(lambda u: u.is_superuser)
@require_POST
def mark_notification_read(request, notification_id):
    """Mark a notification as read"""
    from withdrawals.models import AdminNotification
    
    try:
        notification = AdminNotification.objects.get(id=notification_id)
        notification.mark_as_read()
        return JsonResponse({'success': True})
    except AdminNotification.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Notification not found'})


@login_required
@user_passes_test(lambda u: u.is_superuser)
@require_POST
def mark_all_notifications_read(request):
    """Mark all notifications as read"""
    from withdrawals.models import AdminNotification
    
    try:
        unread = AdminNotification.objects.filter(is_read=False)
        count = unread.count()
        unread.update(is_read=True)
        return JsonResponse({'success': True, 'count': count})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})


@login_required
@user_passes_test(lambda u: u.is_superuser)
@require_POST
def delete_notification(request, notification_id):
    """Delete a notification"""
    from withdrawals.models import AdminNotification
    
    try:
        notification = AdminNotification.objects.get(id=notification_id)
        notification.delete()
        return JsonResponse({'success': True})
    except AdminNotification.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Notification not found'})


@login_required
@user_passes_test(lambda u: u.is_superuser)
@require_POST
def clear_read_notifications(request):
    """Delete all read notifications"""
    from withdrawals.models import AdminNotification
    
    try:
        read = AdminNotification.objects.filter(is_read=True)
        count = read.count()
        read.delete()
        return JsonResponse({'success': True, 'count': count})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})


# ================================
# SYSTEM MAINTENANCE VIEWS
# ================================

@login_required
@user_passes_test(lambda u: u.is_superuser)
def database_maintenance(request):
    """Perform database maintenance operations"""
    if request.method == 'POST':
        try:
            from django.core.management import call_command
            from django.db import connection
            
            # Clean up old sessions
            call_command('clearsessions')
            
            # Optimize database tables (for SQLite)
            with connection.cursor() as cursor:
                cursor.execute("VACUUM;")
                cursor.execute("ANALYZE;")
            
            # Clean up old download logs (older than 90 days)
            from sharp_student_documents.models import DownloadLog
            from datetime import timedelta
            cutoff_date = timezone.now() - timedelta(days=90)
            deleted_logs = DownloadLog.objects.filter(download_time__lt=cutoff_date).delete()[0]
            
            # Clean up old security logs (older than 180 days)
            from security.models import SecurityLog
            security_cutoff = timezone.now() - timedelta(days=180)
            deleted_security_logs = SecurityLog.objects.filter(created_at__lt=security_cutoff).delete()[0]
            
            messages.success(request, f'Database maintenance completed successfully! '
                                      f'Cleaned {deleted_logs} download logs and {deleted_security_logs} security logs.')
            
        except Exception as e:
            messages.error(request, f'Database maintenance failed: {str(e)}')
        
        return redirect('documents:admin_dashboard')
    
    return render(request, 'documents/maintenance/database_maintenance.html')


@login_required
@user_passes_test(lambda u: u.is_superuser)
def email_queue_process(request):
    """Process pending email queue"""
    if request.method == 'POST':
        try:
            from django.core.mail import send_mail
            from django.conf import settings
            from withdrawals.models import AdminNotification
            
            # Get pending notifications that need email sending
            pending_notifications = AdminNotification.objects.filter(
                is_read=False,
                created_at__gte=timezone.now() - timedelta(hours=24)
            )
            
            sent_count = 0
            for notification in pending_notifications:
                if notification.requires_email:
                    try:
                        send_mail(
                            subject=f'SharpDocs: {notification.title}',
                            message=notification.message,
                            from_email=settings.DEFAULT_FROM_EMAIL,
                            recipient_list=[getattr(settings, "ADMIN_EMAIL", settings.EMAIL_HOST_USER)],
                            fail_silently=False,
                        )
                        notification.email_sent = True
                        notification.save()
                        sent_count += 1
                    except Exception as e:
                        # Log error but continue with others
                        pass
            
            messages.success(request, f'Email queue processed successfully! Sent {sent_count} emails.')
            
        except Exception as e:
            messages.error(request, f'Email queue processing failed: {str(e)}')
        
        return redirect('documents:admin_dashboard')
    
    return render(request, 'documents/maintenance/email_queue.html')


@login_required
@user_passes_test(lambda u: u.is_superuser)
def security_audit(request):
    """Run security audit checks"""
    if request.method == 'POST':
        try:
            audit_results = []
            
            # Check for suspicious login patterns
            from security.models import SecurityLog
            from datetime import timedelta
            
            recent_failed_logins = SecurityLog.objects.filter(
                event_type='LOGIN_FAILED',
                created_at__gte=timezone.now() - timedelta(hours=24)
            ).values('ip_address').annotate(
                failed_count=Count('id')
            ).filter(failed_count__gt=5)
            
            if recent_failed_logins:
                audit_results.append(f'Found {len(recent_failed_logins)} IPs with suspicious login attempts')
            
            # Check for users without 2FA (should be enabled for admins)
            from accounts.models import CustomUser
            admins_without_2fa = CustomUser.objects.filter(
                is_staff=True,
                two_factor__isnull=True
            ).count()
            
            if admins_without_2fa > 0:
                audit_results.append(f'{admins_without_2fa} admin accounts without 2FA protection')
            
            # Check for pending identity verifications older than 7 days
            from security.models import IdentityVerification
            old_pending_verifications = IdentityVerification.objects.filter(
                status='PENDING',
                created_at__lt=timezone.now() - timedelta(days=7)
            ).count()
            
            if old_pending_verifications > 0:
                audit_results.append(f'{old_pending_verifications} identity verifications pending for over 7 days')
            
            # Check for unusual document upload patterns
            from .models import Document
            recent_uploads = Document.objects.filter(
                created_at__gte=timezone.now() - timedelta(hours=1)
            ).values('seller').annotate(
                upload_count=Count('id')
            ).filter(upload_count__gt=10)
            
            if recent_uploads:
                audit_results.append(f'Found {len(recent_uploads)} users with unusual upload patterns')
            
            if audit_results:
                messages.warning(request, f'Security audit completed. Found {len(audit_results)} issues:')
                for result in audit_results:
                    messages.warning(request, result)
            else:
                messages.success(request, 'Security audit completed. No critical issues found.')
            
        except Exception as e:
            messages.error(request, f'Security audit failed: {str(e)}')
        
        return redirect('documents:admin_dashboard')
    
    return render(request, 'documents/maintenance/security_audit.html')


@login_required
@user_passes_test(lambda u: u.is_superuser)
def backup_system(request):
    """Create system backups"""
    if request.method == 'POST':
        try:
            import os
            import shutil
            from django.conf import settings
            from django.core.management import call_command
            from datetime import datetime
            
            # Create backup directory if it doesn't exist
            backup_dir = os.path.join(settings.BASE_DIR, 'backups')
            os.makedirs(backup_dir, exist_ok=True)
            
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            
            # Database backup
            db_backup_file = os.path.join(backup_dir, f'db_backup_{timestamp}.json')
            with open(db_backup_file, 'w', encoding='utf-8') as f:
                call_command('dumpdata', stdout=f)
            
            # Media files backup
            media_backup_dir = os.path.join(backup_dir, f'media_backup_{timestamp}')
            if os.path.exists(settings.MEDIA_ROOT):
                shutil.copytree(settings.MEDIA_ROOT, media_backup_dir)
            
            # Clean up old backups (keep last 10)
            all_backups = [f for f in os.listdir(backup_dir) if f.startswith('db_backup_')]
            all_backups.sort()
            if len(all_backups) > 10:
                for old_backup in all_backups[:-10]:
                    old_path = os.path.join(backup_dir, old_backup)
                    if os.path.isfile(old_path):
                        os.remove(old_path)
            
            messages.success(request, f'System backup completed successfully! '
                                      f'Database: {db_backup_file}, Media: {media_backup_dir}')
            
        except Exception as e:
            messages.error(request, f'System backup failed: {str(e)}')
        
        return redirect('documents:admin_dashboard')
    
    return render(request, 'documents/maintenance/backup_system.html')
