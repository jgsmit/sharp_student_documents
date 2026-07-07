from django.core.management.base import BaseCommand
from django.urls import reverse
from django.template.loader import render_to_string
from django.conf import settings
import os
from datetime import datetime


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
            # Generate sitemap data
            sitemap_data = self.generate_sitemap_data()
            
            # Render XML
            xml_content = render_to_string('sitemap.xml', {'sitemap_data': sitemap_data})
            
            # Write to file
            output_path = os.path.join(settings.BASE_DIR, options['output'])
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(xml_content)
            
            self.stdout.write(self.style.SUCCESS(f'Sitemap generated successfully: {output_path}'))
            
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Error generating sitemap: {e}'))

    def generate_sitemap_data(self):
        """Generate sitemap data for all important pages"""
        from documents.models import Document
        
        urls = []
        current_time = datetime.now().isoformat()
        site_url = settings.SITE_URL
        
        # Homepage
        urls.append({
            'location': f'{site_url}/',
            'lastmod': current_time,
            'changefreq': 'daily',
            'priority': '1.0'
        })
        
        # Document list page
        urls.append({
            'location': f'{site_url}{reverse("documents:document_list")}',
            'lastmod': current_time,
            'changefreq': 'daily',
            'priority': '0.9'
        })

        for route_name, priority, changefreq in [
            ("reviews:faq", "0.6", "weekly"),
            ("reviews:help_center", "0.7", "weekly"),
            ("reviews:contact", "0.5", "monthly"),
            ("reviews:resources", "0.6", "weekly"),
            ("reviews:terms", "0.4", "yearly"),
            ("reviews:privacy", "0.4", "yearly"),
        ]:
            urls.append({
                'location': f'{site_url}{reverse(route_name)}',
                'lastmod': current_time,
                'changefreq': changefreq,
                'priority': priority,
            })
        
        # Public document pages
        documents = Document.objects.order_by('-created_at')
        for doc in documents:
            urls.append({
                'location': f'{site_url}{reverse("documents:document_detail", kwargs={"slug": doc.slug})}',
                'lastmod': doc.created_at.isoformat(),
                'changefreq': 'weekly',
                'priority': '0.8'
            })

        try:
            from reviews.models import HelpArticle

            for article in HelpArticle.objects.filter(published=True).order_by('order', 'pk'):
                urls.append({
                    'location': f'{site_url}{reverse("reviews:help_article_detail", kwargs={"pk": article.pk})}',
                    'lastmod': current_time,
                    'changefreq': 'monthly',
                    'priority': '0.5',
                })
        except Exception:
            pass
        
        return urls
