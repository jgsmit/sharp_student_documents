import os
import time
import logging
from django.conf import settings
from django.core.management.base import BaseCommand
from documents.models import Document
import cloudinary
import cloudinary.uploader
from cloudinary.utils import cloudinary_url

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Migrate existing local document files to Cloudinary"

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Simulate migration without uploading',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        media_root = settings.MEDIA_ROOT
        success = 0
        skipped = 0
        errors = 0
        total = 0

        for doc in Document.objects.exclude(file='').exclude(file__isnull=True):
            total += 1
            file_name = doc.file.name

            # Check if already on Cloudinary via API
            try:
                cloudinary.api.resource(file_name, resource_type='raw')
                skipped += 1
                self.stdout.write(f'  [{skipped}] SKIP (already on Cloudinary): {doc.id} - {doc.title[:60]}')
                continue
            except cloudinary.exceptions.NotFound:
                pass
            except Exception:
                pass

            # Try to find the local file — handle double documents/ prefix from previous failed migration
            local_path = os.path.join(media_root, file_name)
            if not os.path.exists(local_path):
                # Try stripping duplicate "documents/" prefix
                if file_name.startswith('documents/documents/'):
                    local_path = os.path.join(media_root, file_name[len('documents/'):])
            if not os.path.exists(local_path):
                self.stdout.write(self.style.WARNING(
                    f'  [WARN] Local file not found for doc #{doc.id}: {local_path}'))
                errors += 1
                continue

            self.stdout.write(f'  [{total}] Uploading doc #{doc.id}: {doc.title[:60]}...')

            if dry_run:
                self.stdout.write(f'       Would upload: {local_path}')
                continue

            try:
                with open(local_path, 'rb') as f:
                    result = cloudinary.uploader.upload(f, resource_type='raw', use_filename=True, unique_filename=False)
                public_id = result['public_id']

                # Update the document's file field with the Cloudinary public_id
                doc.file.name = public_id
                doc.save(update_fields=['file'])

                # Verify it works
                verify_url, _ = cloudinary_url(public_id, resource_type='raw', sign_url=True, expires_at=int(time.time()) + 60)
                self.stdout.write(self.style.SUCCESS(f'       OK -> {public_id}'))
                success += 1
            except Exception as e:
                errors += 1
                logger.exception(f'Failed to upload doc #{doc.id}: {e}')
                self.stdout.write(self.style.ERROR(f'       FAILED: {e}'))

        summary = f'\nDone. {success} uploaded, {skipped} already on Cloudinary, {errors} errors out of {total} total.'
        self.stdout.write(self.style.SUCCESS(summary) if not errors else self.style.WARNING(summary))
