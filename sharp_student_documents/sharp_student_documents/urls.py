# sharp_student_documents/urls.py (project urls)
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.views.generic.base import RedirectView
from documents.sitemaps import StaticViewSitemap, DocumentSitemap, CategorySitemap, HelpArticleSitemap
from documents import views as documents_views
from . import views

handler400 = "sharp_student_documents.views.bad_request"
handler403 = "sharp_student_documents.views.permission_denied"
handler404 = "sharp_student_documents.views.page_not_found"
handler500 = "sharp_student_documents.views.server_error"

sitemaps = {
    'static': StaticViewSitemap,
    'documents': DocumentSitemap,
    'categories': CategorySitemap,
    'help_articles': HelpArticleSitemap,
}

urlpatterns = [
    path('admin/', admin.site.urls),

    # PWA (django-pwa)
    path('', include('pwa.urls')),
    # Some templates/browsers request /sw.js; keep it compatible.
    path('sw.js', RedirectView.as_view(url='/serviceworker.js', permanent=False)),
    path('favicon.ico', RedirectView.as_view(url='/static/sharp.png', permanent=True)),

    path('accounts/', include('accounts.urls')),
    path('documents/', include('documents.urls')),
    path('payments/', include('payments.urls')),
    path('reviews/', include('reviews.urls')),
    path('withdrawals/', include('withdrawals.urls')),
    path('security/', include('security.urls')),
    path('education/', include('education.urls')),
    path('notifications/', include('notifications.urls')),

    # Legacy downloads (older templates/links used /download/<order_id>/)
    path('download/<int:order_id>/', documents_views.download_document, name='legacy_download'),
    path('', views.home, name='home'),
    
    # Sitemap
    path('sitemap.xml', views.sitemap_xml, {'sitemaps': sitemaps}, name='django.contrib.sitemaps.views.sitemap'),
    
    # Robots.txt
    path('robots.txt', views.robots_txt, name='robots_txt'),
]

# Serve media files during development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
