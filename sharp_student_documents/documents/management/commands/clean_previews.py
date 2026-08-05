import collections
import re

from django.core.management.base import BaseCommand

from documents.models import Document
from documents.preview_utils import normalize_preview_text


class Command(BaseCommand):
    help = "Re-clean existing document preview_text using normalize_preview_text"

    def handle(self, *args, **options):
        self.stdout.write("=== CLEANING DOCUMENT PREVIEWS ===")

        qs = Document.objects.exclude(preview_text="").exclude(preview_text__isnull=True)
        docs = list(qs)
        self.stdout.write(f"Found {len(docs)} documents with preview text")

        # Build a corpus-derived set of known words so real words are
        # never merged into a preceding word fragment.
        counter = collections.Counter()
        for doc in docs:
            for word in re.split(r"[^A-Za-z]+", doc.preview_text):
                if len(word) >= 3:
                    counter[word.lower()] += 1
        known_words = {w for w, c in counter.items() if c >= 3}
        self.stdout.write(f"Corpus-derived known words: {len(known_words)}")

        changed = 0
        for doc in docs:
            cleaned = normalize_preview_text(doc.preview_text, known_words)
            if cleaned != doc.preview_text:
                doc.preview_text = cleaned
                doc.save(update_fields=["preview_text"])
                changed += 1

        self.stdout.write(f"Updated previews: {changed}")
        self.stdout.write("=== CLEANUP COMPLETE ===")
