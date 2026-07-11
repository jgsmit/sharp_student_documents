from django.contrib.sitemaps import Sitemap
from django.urls import reverse
from django.utils import timezone
from .models import Document, Category
from reviews.models import HelpArticle


class StaticViewSitemap(Sitemap):
    protocol = "https"

    def items(self):
        return [
            {"route": "home",                    "priority": 1.0, "changefreq": "daily"},
            {"route": "documents:document_list", "priority": 0.9, "changefreq": "daily"},
            {"route": "documents:advanced_search","priority": 0.6, "changefreq": "weekly"},
            {"route": "reviews:help_center",     "priority": 0.8, "changefreq": "weekly"},
            {"route": "reviews:faq",             "priority": 0.7, "changefreq": "weekly"},
            {"route": "reviews:resources",       "priority": 0.6, "changefreq": "weekly"},
            {"route": "reviews:contact",         "priority": 0.5, "changefreq": "monthly"},
            {"route": "reviews:terms",           "priority": 0.3, "changefreq": "yearly"},
            {"route": "reviews:privacy",         "priority": 0.3, "changefreq": "yearly"},
            {"route": "accounts:register",       "priority": 0.5, "changefreq": "monthly"},
            {"route": "accounts:login",          "priority": 0.4, "changefreq": "monthly"},
            {"route": "security:trust_security", "priority": 0.5, "changefreq": "monthly"},
        ]

    def location(self, item):
        return reverse(item["route"])

    def priority(self, item):
        return item["priority"]

    def changefreq(self, item):
        return item["changefreq"]

    def lastmod(self, item):
        return timezone.now().date()


class DocumentSitemap(Sitemap):
    protocol = "https"
    changefreq = "weekly"
    limit = 50000  # Google sitemap limit

    def items(self):
        # No is_approved field — all documents with a slug are public
        return (
            Document.objects
            .exclude(slug="")
            .select_related("category", "seller")
            .order_by("-created_at")
        )

    def lastmod(self, obj):
        # Document model only has created_at
        return obj.created_at

    def priority(self, obj):
        return 0.8

    def location(self, obj):
        return reverse("documents:document_detail", kwargs={"slug": obj.slug})


class CategorySitemap(Sitemap):
    protocol = "https"
    changefreq = "weekly"
    priority = 0.8

    def items(self):
        return (
            Category.objects
            .filter(is_active=True)
            .exclude(slug="")
            .order_by("sort_order", "name")
        )

    def lastmod(self, obj):
        return timezone.now().date()

    def location(self, obj):
        return reverse("documents:category_detail", kwargs={"slug": obj.slug})


class HelpArticleSitemap(Sitemap):
    protocol = "https"
    changefreq = "monthly"
    priority = 0.5

    def items(self):
        return HelpArticle.objects.filter(published=True).order_by("order", "pk")

    def location(self, obj):
        return reverse("reviews:help_article_detail", kwargs={"pk": obj.pk})
