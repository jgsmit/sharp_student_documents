import os, sys
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'sharp_student_documents.settings')
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'sharp_student_documents'))
import django
django.setup()
from documents.models import Document
print(f'Total documents: {Document.objects.count()}')
print(f'With file: {Document.objects.exclude(file="").exclude(file__isnull=True).count()}')
docs = Document.objects.exclude(file="").exclude(file__isnull=True)[:5]
for d in docs:
    print(f'  ID={d.id} title={d.title!r} file={d.file.name}')
