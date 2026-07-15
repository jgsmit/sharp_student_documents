from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.contrib.admin.views.decorators import staff_member_required
from documents.models import Document, Order
from .models import Review, FAQ, HelpArticle, HelpCategory
from django.db.models import Q, Avg
from .forms import ReviewForm
from django.core.paginator import Paginator

@login_required
def my_reviews(request):
    """
    Display reviews for the current user's documents (seller perspective)
    """
    # Get reviews for documents owned by the current user
    reviews = Review.objects.filter(
        document__seller=request.user
    ).select_related('reviewer', 'document').order_by('-created_at')
    
    # Pagination
    paginator = Paginator(reviews, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Statistics
    total_reviews = reviews.count()
    average_rating = reviews.aggregate(avg_rating=Avg('rating'))['avg_rating'] or 0
    
    context = {
        'page_obj': page_obj,
        'total_reviews': total_reviews,
        'average_rating': average_rating,
    }
    
    return render(request, 'reviews/my_reviews.html', context)

@login_required
def add_review(request, document_id):
    document = get_object_or_404(Document, id=document_id)

    # Only allow if user purchased the document
    if not Order.objects.filter(document=document, buyer=request.user, status="paid").exists():
        messages.error(request, "You can only review documents you purchased.")
        return redirect("documents:document_detail", slug=document.slug)

    # Prevent duplicate reviews from the same buyer.
    if Review.objects.filter(document=document, reviewer=request.user).exists():
        messages.info(request, "You already reviewed this document.")
        return redirect("document_detail", slug=document.slug)

    if request.method == "POST":
        form = ReviewForm(request.POST)
        if form.is_valid():
            review = form.save(commit=False)
            review.document = document
            review.reviewer = request.user
            review.save()
            # Notify seller about new review
            try:
                from notifications.models import UserNotification
                UserNotification.create_notification(
                    user=document.seller, notification_type='review_received',
                    title=f'New Review: {document.title}',
                    message=f'{request.user.username} left a {review.rating}-star review on your document "{document.title}".',
                    link=document.get_absolute_url()
                )
            except Exception:
                pass
            messages.success(request, "Review submitted successfully.")
            return redirect("documents:document_detail", slug=document.slug)
    else:
        form = ReviewForm()

    return render(request, "reviews/add_review.html", {"form": form, "document": document})


@staff_member_required
def review_moderation(request):
    """
    View for moderators to review and moderate user reviews
    """
    # Get all reviews that need moderation
    reviews = Review.objects.all().select_related('document', 'reviewer').order_by('-created_at')
    
    # Filter by status if provided
    status_filter = request.GET.get('status')
    if status_filter:
        reviews = reviews.filter(status=status_filter)
    
    context = {
        'reviews': reviews,
        'status_filter': status_filter,
    }
    return render(request, 'reviews/review_moderation.html', context)



# FAQ Page
def faq_view(request):
    faqs = FAQ.objects.all()
    return render(request, 'reviews/faq.html', {'faqs': faqs})

# Help Center with Search & Categories

def help_center_view(request):
    query = request.GET.get('q', '')
    category_slug = request.GET.get('category', '')

    articles = HelpArticle.objects.filter(published=True)

    if category_slug:
        articles = articles.filter(category__slug=category_slug)

    if query:
        articles = articles.filter(Q(title__icontains=query) | Q(content__icontains=query))

    categories = HelpCategory.objects.all()

    return render(request, 'reviews/help_center.html', {
        'articles': articles,
        'categories': categories,
        'query': query,
        'selected_category': category_slug
    })

# Single Help Article
def help_article_detail_view(request, pk):
    article = get_object_or_404(HelpArticle, pk=pk, published=True)
    return render(request, 'reviews/help_article_detail.html', {'article': article})

# Static Pages
def contact(request):
    return render(request, 'reviews/contact.html')

def resources(request):
    return render(request, 'reviews/resources.html')

def terms(request):
    return render(request, 'reviews/terms.html')

def privacy(request):
    return render(request, 'reviews/privacy.html')
