from django.contrib.sitemaps import Sitemap
from django.urls import reverse
from .models import Document, Category
from reviews.models import HelpArticle

class StaticViewSitemap(Sitemap):
    def items(self):
        return [
            {"route": "home", "priority": 1.0, "changefreq": "daily"},
            {"route": "documents:document_list", "priority": 0.9, "changefreq": "daily"},
            {"route": "reviews:faq", "priority": 0.6, "changefreq": "weekly"},
            {"route": "reviews:help_center", "priority": 0.7, "changefreq": "weekly"},
            {"route": "reviews:contact", "priority": 0.5, "changefreq": "monthly"},
            {"route": "reviews:resources", "priority": 0.6, "changefreq": "weekly"},
            {"route": "reviews:terms", "priority": 0.4, "changefreq": "yearly"},
            {"route": "reviews:privacy", "priority": 0.4, "changefreq": "yearly"},
        ]

    def location(self, item):
        return reverse(item["route"])

    def priority(self, item):
        return item["priority"]

    def changefreq(self, item):
        return item["changefreq"]

class DocumentSitemap(Sitemap):
    def items(self):
        return Document.objects.exclude(slug="").order_by('-created_at')

    def lastmod(self, obj):
        return obj.created_at

    def changefreq(self, obj):
        return "daily"

    def priority(self, obj):
        if getattr(obj, "created_at", None):
            return 0.9
        return 0.8

    def location(self, obj):
        return reverse('documents:document_detail', kwargs={'slug': obj.slug})


class CategorySitemap(Sitemap):
    changefreq = "weekly"
    priority = 0.8

    def items(self):
        return Category.objects.filter(is_active=True).exclude(slug="").order_by("sort_order", "name")

    def location(self, obj):
        return reverse("documents:category_detail", kwargs={"slug": obj.slug})


class HelpArticleSitemap(Sitemap):
    changefreq = "monthly"
    priority = 0.5

    def items(self):
        return HelpArticle.objects.filter(published=True).order_by("order", "pk")

    def location(self, obj):
        return reverse("reviews:help_article_detail", kwargs={"pk": obj.pk})
