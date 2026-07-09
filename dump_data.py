import os, sys, json
os.environ['DJANGO_SETTINGS_MODULE'] = 'sharp_student_documents.settings'
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'sharp_student_documents'))
import django
django.setup()
from django.core.management import call_command
from io import StringIO
buf = StringIO()
call_command('dumpdata', '--indent', '2', stdout=buf)
data = json.loads(buf.getvalue())
with open('data.json', 'w') as f:
    json.dump(data, f, indent=2)
print(f'Dumped {len(data)} objects')