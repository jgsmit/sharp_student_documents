import gzip
import os

from django.conf import settings
from django.core.management.base import BaseCommand
from django.template.loader import render_to_string
from django.urls import reverse
from django.utils import timezone


class Command(BaseCommand):
    help = 'Generate XML sitemap for better SEO'

    def add_arguments(self, parser):
        parser.add_argument(
            '--output',
            type=str,
            default='sitemap.xml',
            help='Output file name'
        )

    def handle(self, *args, **options):
        self.stdout.write('Generating sitemap...')

        try:
            sitemap_data = self.generate_sitemap_data()
            xml_content = render_to_string('sitemap.xml', {'sitemap_data': sitemap_data})
            output_path = os.path.join(settings.BASE_DIR, options['output'])
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(xml_content)
            self.stdout.write(self.style.SUCCESS(f'Sitemap generated successfully: {output_path}'))
            gz_path = output_path + '.gz'
            with gzip.open(gz_path, 'wt', encoding='utf-8') as f:
                f.write(xml_content)
            self.stdout.write(self.style.SUCCESS(f'Gzipped sitemap generated: {gz_path}'))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Error generating sitemap: {e}'))

    def generate_sitemap_data(self):
        from documents.models import Document, Category
        from reviews.models import HelpArticle

        urls = []
        now = timezone.now()
        site_url = settings.SITE_URL.rstrip("/")

        # Static pages
        static_pages = [
            ("home", "1.0", "daily"),
            ("documents:document_list", "0.9", "daily"),
            ("documents:advanced_search", "0.6", "weekly"),
            ("reviews:help_center", "0.8", "weekly"),
            ("reviews:faq", "0.7", "weekly"),
            ("reviews:resources", "0.6", "weekly"),
            ("reviews:contact", "0.5", "monthly"),
            ("reviews:terms", "0.3", "yearly"),
            ("reviews:privacy", "0.3", "yearly"),
            ("accounts:register", "0.5", "monthly"),
            ("accounts:login", "0.4", "monthly"),
            ("security:trust_security", "0.5", "monthly"),
        ]
        for route_name, priority, changefreq in static_pages:
            urls.append({
                'location': f'{site_url}{reverse(route_name)}',
                'lastmod': now,
                'changefreq': changefreq,
                'priority': priority,
            })

        # Active categories
        categories = Category.objects.filter(is_active=True).exclude(slug="").order_by("sort_order", "name")
        for cat in categories:
            urls.append({
                'location': f'{site_url}{reverse("documents:category_detail", kwargs={"slug": cat.slug})}',
                'lastmod': now,
                'changefreq': 'weekly',
                'priority': '0.8',
            })

        # Public documents
        documents = Document.objects.exclude(slug="").order_by("-created_at")
        for doc in documents:
            urls.append({
                'location': f'{site_url}{reverse("documents:document_detail", kwargs={"slug": doc.slug})}',
                'lastmod': doc.created_at,
                'changefreq': 'weekly',
                'priority': '0.8',
            })

        # Published help articles
        for article in HelpArticle.objects.filter(published=True).order_by('order', 'pk'):
            urls.append({
                'location': f'{site_url}{reverse("reviews:help_article_detail", kwargs={"pk": article.pk})}',
                'lastmod': now,
                'changefreq': 'monthly',
                'priority': '0.5',
            })

        return urls
