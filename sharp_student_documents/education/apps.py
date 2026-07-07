# Education app for SharpDocs marketplace
# Provides study planner, note-taking, flashcards, progress tracking, and collaboration tools

from django.apps import AppConfig

class EducationConfig(AppConfig):
    name = 'education'
    verbose_name = 'Education'
    verbose_name_plural = 'Education'
    
    def ready(self):
        import education.signals
