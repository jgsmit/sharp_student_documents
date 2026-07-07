# Google Indexing Guide for SharpDocs

## 🚀 Getting Your Website Indexed by Google

### Step 1: Google Search Console Setup

1. **Go to Google Search Console**
   - Visit: [https://search.google.com/search-console](https://search.google.com/search-console)
   - Sign in with your Google account

2. **Add Your Property**
   - Click "Add Property"
   - Choose "URL prefix"
   - Enter your domain: `https://yourdomain.com`
   - Verify ownership

3. **Verify Ownership** (Choose one method):
   - **HTML file upload** (easiest)
   - **DNS record**
   - **Google Analytics**
   - **Google Tag Manager**

### Step 2: Generate Sitemap

#### Create Dynamic Sitemap
```python
# documents/sitemaps.py
from django.contrib.sitemaps import Sitemap
from django.urls import reverse
from .models import Document, Category

class StaticViewSitemap(Sitemap):
    priority = 1.0
    changefreq = 'daily'

    def items(self):
        return ['home', 'documents:list', 'accounts:register', 'accounts:login']

    def location(self, item):
        return reverse(item)

class DocumentSitemap(Sitemap):
    changefreq = 'weekly'
    priority = 0.8

    def items(self):
        return Document.objects.filter(status='published')

    def lastmod(self, obj):
        return obj.updated_at

    def location(self, obj):
        return f'/documents/{obj.slug}/'

class CategorySitemap(Sitemap):
    changefreq = 'monthly'
    priority = 0.6

    def items(self):
        return Category.objects.filter(is_active=True)

    def location(self, obj):
        return f'/documents/category/{obj.slug}/'
```

#### Update URLs
```python
# sharp_student_documents/urls.py
from django.contrib.sitemaps.views import sitemap
from documents.sitemaps import StaticViewSitemap, DocumentSitemap, CategorySitemap

sitemaps = {
    'static': StaticViewSitemap,
    'documents': DocumentSitemap,
    'categories': CategorySitemap,
}

urlpatterns = [
    # ... your existing URLs
    path('sitemap.xml', sitemap, {'sitemaps': sitemaps}, name='django.contrib.sitemaps.views.sitemap'),
]
```

### Step 3: robots.txt Configuration

#### Create robots.txt
```python
# Create templates/robots.txt
User-agent: *
Allow: /
Disallow: /admin/
Disallow: /accounts/
Disallow: /api/
Disallow: /static/
Disallow: /media/

# Sitemap location
Sitemap: https://yourdomain.com/sitemap.xml

# Crawl delay (optional)
Crawl-delay: 1
```

#### Add robots.txt URL
```python
# sharp_student_documents/urls.py
from django.views.generic import TemplateView

urlpatterns = [
    # ... existing URLs
    path('robots.txt', TemplateView.as_view(template_name='robots.txt', content_type='text/plain')),
]
```

### Step 4: SEO Optimization

#### Meta Tags Enhancement
```html
<!-- base.html -->
<head>
    <title>{% block title %}SharpDocs - Academic Document Marketplace{% endblock %}</title>
    
    <!-- Meta Description -->
    <meta name="description" content="{% block meta_description %}Buy and sell academic documents, study notes, and educational materials{% endblock %}">
    
    <!-- Meta Keywords -->
    <meta name="keywords" content="{% block meta_keywords %}academic documents, study notes, educational marketplace, student resources{% endblock %}">
    
    <!-- Open Graph -->
    <meta property="og:title" content="{% block og_title %}SharpDocs{% endblock %}">
    <meta property="og:description" content="{% block og_description %}Academic document marketplace{% endblock %}">
    <meta property="og:type" content="{% block og_type %}website{% endblock %}">
    <meta property="og:url" content="{% block og_url %}{{ request.build_absolute_uri }}{% endblock %}">
    <meta property="og:image" content="{% block og_image %}{% static 'images/og-image.jpg' %}{% endblock %}">
    
    <!-- Twitter Card -->
    <meta name="twitter:card" content="summary_large_image">
    <meta name="twitter:title" content="{% block twitter_title %}SharpDocs{% endblock %}">
    <meta name="twitter:description" content="{% block twitter_description %}Academic document marketplace{% endblock %}">
    
    <!-- Canonical URL -->
    <link rel="canonical" href="{{ request.build_absolute_uri }}">
    
    <!-- Hreflang for international -->
    <link rel="alternate" hreflang="en" href="{{ request.build_absolute_uri }}">
</head>
```

#### Structured Data (JSON-LD)
```html
<!-- Add to document detail template -->
<script type="application/ld+json">
{
    "@context": "https://schema.org",
    "@type": "EducationalOrganization",
    "name": "SharpDocs",
    "url": "https://yourdomain.com",
    "description": "Academic document marketplace for students",
    "sameAs": [
        "https://www.facebook.com/sharpdocs",
        "https://www.twitter.com/sharpdocs"
    ]
}
</script>

<!-- Document structured data -->
<script type="application/ld+json">
{
    "@context": "https://schema.org",
    "@type": "EducationalAudience",
    "educationalRole": "student",
    "audience": {
        "@type": "EducationalAudience",
        "educationalRole": "student"
    }
}
</script>
```

### Step 5: Submit to Google

#### Submit Sitemap
1. **Go to Google Search Console**
2. **Select your property**
3. **Go to "Sitemaps"**
4. **Enter**: `sitemap.xml`
5. **Click "Submit"**

#### Request Indexing
1. **Go to "URL Inspection"**
2. **Enter your homepage**: `https://yourdomain.com`
3. **Click "Request Indexing"**
4. **Do this for important pages**:
   - Homepage
   - Document listings
   - Category pages
   - Registration page

### Step 6: Performance Monitoring

#### Google Analytics Setup
```html
<!-- Add to base.html -->
<!-- Google Analytics -->
<script async src="https://www.googletagmanager.com/gtag/js?id=GA_MEASUREMENT_ID"></script>
<script>
  window.dataLayer = window.dataLayer || [];
  function gtag(){dataLayer.push(arguments);}
  gtag('js', new Date());
  gtag('config', 'GA_MEASUREMENT_ID');
</script>
```

#### Core Web Vitals
```python
# Add to settings.py
# Performance optimizations
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = 'DENY'

# Cache settings
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
        'LOCATION': 'unique-snowflake',
    }
}
```

## 📊 SEO Checklist

### ✅ Technical SEO
- [ ] robots.txt created
- [ ] sitemap.xml generated
- [ ] SSL certificate installed
- [ ] Fast loading speed
- [ ] Mobile-friendly design
- [ ] No broken links

### ✅ Content SEO
- [ ] Unique page titles
- [ ] Meta descriptions
- [ ] Header tags (H1, H2, H3)
- [ ] Image alt text
- [ ] Internal linking
- [ ] Quality content

### ✅ Off-Page SEO
- [ ] Backlinks from educational sites
- [ ] Social media presence
- [ ] Local business listings
- [ ] Guest blogging
- [ ] Forum participation

## 🚀 Advanced SEO

### Schema Markup
```html
<!-- Product schema for documents -->
<script type="application/ld+json">
{
    "@context": "https://schema.org",
    "@type": "Product",
    "name": "{{ document.title }}",
    "description": "{{ document.description }}",
    "brand": {
        "@type": "Brand",
        "name": "SharpDocs"
    },
    "offers": {
        "@type": "Offer",
        "price": "{{ document.price }}",
        "priceCurrency": "USD",
        "availability": "https://schema.org/InStock"
    }
}
</script>
```

### Page Speed Optimization
```python
# Compress images
from django.core.files.storage import default_storage
from PIL import Image

def compress_image(image_path, quality=85):
    img = Image.open(default_storage.open(image_path))
    img.save(image_path, optimize=True, quality=quality)
```

## 📞 Google Support Resources

### Search Console Help
- **Documentation**: [Search Console Help](https://support.google.com/webmasters/)
- **Community**: [Google Webmasters Forum](https://support.google.com/webmasters/community)
- **YouTube**: [Google Webmasters Channel](https://www.youtube.com/c/googlewebmasters)

### SEO Tools
- **Google PageSpeed Insights**: [pagespeed.web.dev](https://pagespeed.web.dev)
- **Google Mobile-Friendly Test**: [testmysite.thinkwithgoogle.com](https://testmysite.thinkwithgoogle.com)
- **Google Rich Results Test**: [search.google.com/test/rich-results](https://search.google.com/test/rich-results)

## 🎯 Timeline for Indexing

### Day 1-3: Setup
- [ ] Create accounts
- [ ] Verify ownership
- [ ] Generate sitemap
- [ ] Submit to Google

### Week 1: Initial Indexing
- [ ] Submit important URLs
- [ ] Monitor crawl stats
- [ ] Fix any errors

### Week 2-4: Content Indexing
- [ ] Add new content regularly
- [ ] Monitor search performance
- [ ] Optimize based on data

### Month 1-3: Ranking Improvement
- [ ] Build backlinks
- [ ] Improve user engagement
- [ ] Monitor keyword rankings

## 🔍 Troubleshooting

### Common Issues
- **Not indexed**: Check robots.txt and sitemap
- **Low ranking**: Improve content and backlinks
- **Crawl errors**: Fix broken links
- **Mobile issues**: Ensure responsive design

### Monitoring Tools
- **Google Search Console**: Crawl stats, indexing issues
- **Google Analytics**: Traffic and user behavior
- **Google PageSpeed**: Performance metrics
- **Screaming Frog**: Technical SEO audit
