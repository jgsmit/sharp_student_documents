from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.utils import timezone
import random

User = get_user_model()

class Command(BaseCommand):
    help = 'Populate review models with test data for dashboard testing'

    def handle(self, *args, **options):
        self.stdout.write('Populating review data for dashboard testing...')
        
        # Get users and documents
        users = User.objects.all()
        from documents.models import Document
        documents = Document.objects.all()
        
        if not users:
            self.stdout.write('No users found. Please run populate_security_data first.')
            return
        
        if not documents:
            self.stdout.write('No documents found. Creating test documents...')
            # Create test documents
            seller = users[0]
            for i in range(3):
                Document.objects.create(
                    title=f'Test Document {i}',
                    description=f'Test description for document {i}',
                    seller=seller,
                    price=10.00 + i * 5,
                    document_type='essay',
                    academic_level='undergraduate',
                    subject='Computer Science'
                )
            documents = Document.objects.all()
        
        # Create reviews
        self.create_reviews(users, documents)
        
        self.stdout.write(self.style.SUCCESS('Review data populated successfully!'))

    def create_reviews(self, users, documents):
        """Create sample reviews"""
        from reviews.models import Review
        
        for document in documents:
            for reviewer in users[1:4]:  # Use different users as reviewers
                if random.choice([True, False]):  # Randomly create reviews
                    Review.objects.create(
                        document=document,
                        reviewer=reviewer,
                        rating=random.randint(3, 5),
                        comment=f'This is a test review for {document.title}. Great content!',
                        created_at=timezone.now() - timezone.timedelta(days=random.randint(1, 30))
                    )
        
        self.stdout.write(f'Created {Review.objects.count()} reviews')
