from django.core.management.base import BaseCommand
from django.core.files.base import ContentFile
from documents.models import Document
import os


class Command(BaseCommand):
    help = 'Create test PDF files for documents without files'

    def handle(self, *args, **options):
        self.stdout.write('=== CREATING TEST PDF FILES ===')
        
        # Create a simple PDF content (this is a basic text file that will work as a test)
        pdf_content = b'''%PDF-1.4
1 0 obj
<<
/Type /Catalog
/Pages 2 0 R
>>
endobj

2 0 obj
<<
/Type /Pages
/Kids [3 0 R]
/Count 1
>>
endobj

3 0 obj
<<
/Type /Page
/Parent 2 0 R
/MediaBox [0 0 612 792]
/Contents 4 0 R
/Resources <<
/Font <<
/F1 5 0 R
>>
>>
>>
endobj

4 0 obj
<<
/Length 44
>>
stream
BT
/F1 12 Tf
72 720 Td
(Test Document) Tj
ET
endstream
endobj

5 0 obj
<<
/Type /Font
/Subtype /Type1
/BaseFont /Helvetica
>>
endobj

xref
0 6
0000000000 65535 f 
0000000009 00000 n 
0000000054 00000 n 
0000000101 00000 n 
0000000203 00000 n 
0000000271 00000 n 
trailer
<<
/Size 6
/Root 1 0 R
>>
startxref
336
%%EOF
'''
        
        # Find documents without files
        docs_without_files = Document.objects.filter(file='')
        
        for doc in docs_without_files:
            # Create a simple test file
            filename = f'test_document_{doc.id}.pdf'
            content_file = ContentFile(pdf_content, name=filename)
            
            # Attach the file to the document
            doc.file.save(filename, content_file, save=True)
            
            self.stdout.write(f'Created test file for: {doc.title}')
        
        self.stdout.write(f'Created test files for {docs_without_files.count()} documents')
        
        # Check the specific test document
        try:
            test_doc = Document.objects.get(title='Test Document for PayPal Testing')
            if test_doc.file:
                self.stdout.write(f'SUCCESS: Test document now has file: {test_doc.file.name}')
            else:
                self.stdout.write('ERROR: Test document still has no file')
        except Document.DoesNotExist:
            self.stdout.write('ERROR: Test document not found')
        
        self.stdout.write('=== TEST FILES CREATED ===')
