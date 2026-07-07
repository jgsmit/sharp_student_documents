# Education signals for automated learning progress tracking

from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth import get_user_model
from django.utils import timezone

from .models import Note, Flashcard, StudySession, LearningProgress

User = get_user_model()

@receiver(post_save, sender=Note)
def update_learning_progress_notes(sender, instance, created, **kwargs):
    """Update learning progress when notes are created"""
    if created:
        progress, created = LearningProgress.objects.get_or_create(
            user=instance.user,
            document=instance.document,
            defaults={'total_pages': instance.document.pages or 0}
        )
        
        progress.notes_count = Note.objects.filter(
            user=instance.user,
            document=instance.document
        ).count()
        progress.save()

@receiver(post_save, sender=Flashcard)
def update_learning_progress_flashcards(sender, instance, created, **kwargs):
    """Update learning progress when flashcards are created"""
    if created:
        progress, created = LearningProgress.objects.get_or_create(
            user=instance.user,
            document=instance.document,
            defaults={'total_pages': instance.document.pages or 0}
        )
        
        progress.flashcards_count = Flashcard.objects.filter(
            user=instance.user,
            document=instance.document
        ).count()
        progress.save()

@receiver(post_save, sender=StudySession)
def update_learning_progress_sessions(sender, instance, created, **kwargs):
    """Update learning progress when study sessions are completed"""
    if instance.is_completed:
        progress, created = LearningProgress.objects.get_or_create(
            user=instance.user,
            document=instance.document,
            defaults={'total_pages': instance.document.pages or 0}
        )
        
        progress.time_spent_minutes += instance.duration_minutes or 0
        progress.pages_completed += instance.pages_studied
        progress.study_sessions_count += 1
        progress.last_study_date = timezone.now()
        progress.update_progress()
