from django.core.management.base import BaseCommand
from documents.models import Document
from decimal import Decimal


class Command(BaseCommand):
    help = 'Show documents ready for PayPal testing'

    def handle(self, *args, **options):
        self.stdout.write('=== DOCUMENTS READY FOR PAYPAL TESTING ===')
        
        ready_docs = Document.objects.filter(
            price__gt=0,
            file__isnull=False
        ).exclude(file='')
        
        if not ready_docs:
            self.stdout.write('No documents ready for testing!')
            return
        
        for doc in ready_docs:
            self.stdout.write(f'Document: {doc.title}')
            self.stdout.write(f'  Price: ${doc.price}')
            self.stdout.write(f'  Seller: {doc.seller.username}')
            self.stdout.write(f'  Has file: {bool(doc.file)}')
            self.stdout.write('---')
        
        self.stdout.write(f'\\nFound {ready_docs.count()} documents ready for PayPal testing')
        
        # Recommend the best test document
        latest_doc = ready_docs.order_by('-created_at').first()
        if latest_doc:
            self.stdout.write(f'\\nRECOMMENDED FOR TESTING:')
            self.stdout.write(f'Document: {latest_doc.title}')
            self.stdout.write(f'Price: ${latest_doc.price}')
            self.stdout.write(f'Seller: {latest_doc.seller.username}')
