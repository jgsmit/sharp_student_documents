from django.db import models
from django.conf import settings
from django.utils import timezone
from django.contrib.auth import get_user_model
import json

User = get_user_model()

class StudyPlanner(models.Model):
    """
    Integrated calendar and study scheduling system
    """
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="study_plans"
    )
    document = models.ForeignKey(
        'documents.Document',
        on_delete=models.CASCADE,
        related_name="study_plans"
    )
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    start_date = models.DateTimeField()
    end_date = models.DateTimeField()
    study_duration = models.IntegerField(help_text="Duration in minutes per session")
    study_frequency = models.CharField(
        max_length=20,
        choices=[
            ('daily', 'Daily'),
            ('weekly', 'Weekly'),
            ('bi_weekly', 'Bi-weekly'),
            ('monthly', 'Monthly'),
            ('custom', 'Custom'),
        ],
        default='weekly'
    )
    target_completion = models.DateTimeField()
    priority = models.CharField(
        max_length=10,
        choices=[
            ('low', 'Low'),
            ('medium', 'Medium'),
            ('high', 'High'),
            ('urgent', 'Urgent'),
        ],
        default='medium'
    )
    is_completed = models.BooleanField(default=False)
    completion_percentage = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['start_date']
        indexes = [
            models.Index(fields=['user', 'start_date']),
            models.Index(fields=['user', 'is_completed']),
            models.Index(fields=['document', 'user']),
        ]
    
    def __str__(self):
        return f"{self.user.username} - {self.title}"
    
    def is_overdue(self):
        return timezone.now() > self.target_completion and not self.is_completed
    
    def days_remaining(self):
        if self.is_completed:
            return 0
        delta = self.target_completion - timezone.now()
        return max(0, delta.days)

class StudySession(models.Model):
    """
    Individual study sessions tracking
    """
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="study_sessions"
    )
    planner = models.ForeignKey(
        StudyPlanner,
        on_delete=models.CASCADE,
        related_name="sessions"
    )
    document = models.ForeignKey(
        'documents.Document',
        on_delete=models.CASCADE,
        related_name="study_sessions"
    )
    start_time = models.DateTimeField()
    end_time = models.DateTimeField(null=True, blank=True)
    duration_minutes = models.IntegerField(null=True, blank=True)
    pages_studied = models.IntegerField(default=0)
    notes_taken = models.TextField(blank=True)
    is_completed = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-start_time']
        indexes = [
            models.Index(fields=['user', 'start_time']),
            models.Index(fields=['planner', 'is_completed']),
            models.Index(fields=['document', 'user']),
        ]
    
    def __str__(self):
        return f"{self.user.username} - {self.document.title} session"
    
    def calculate_duration(self):
        if self.end_time and self.start_time:
            delta = self.end_time - self.start_time
            self.duration_minutes = int(delta.total_seconds() / 60)
            self.save()

class Note(models.Model):
    """
    Built-in note-taking system with document highlighting
    """
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="notes"
    )
    document = models.ForeignKey(
        'documents.Document',
        on_delete=models.CASCADE,
        related_name="notes"
    )
    title = models.CharField(max_length=200)
    content = models.TextField()
    highlighted_text = models.TextField(blank=True, help_text="Highlighted portions from document")
    page_number = models.IntegerField(null=True, blank=True)
    position_data = models.JSONField(default=dict, help_text="Position data for highlights")
    tags = models.CharField(max_length=500, blank=True, help_text="Comma-separated tags")
    is_public = models.BooleanField(default=False)
    is_favorite = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-updated_at']
        indexes = [
            models.Index(fields=['user', 'document']),
            models.Index(fields=['user', 'is_favorite']),
            models.Index(fields=['document', 'is_public']),
            models.Index(fields=['tags']),
        ]
    
    def __str__(self):
        return f"{self.user.username} - {self.title}"
    
    def get_tag_list(self):
        return [tag.strip() for tag in self.tags.split(',') if tag.strip()]

class Flashcard(models.Model):
    """
    Auto-generated flashcards from document content
    """
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="flashcards"
    )
    document = models.ForeignKey(
        'documents.Document',
        on_delete=models.CASCADE,
        related_name="flashcards"
    )
    question = models.TextField()
    answer = models.TextField()
    difficulty = models.CharField(
        max_length=10,
        choices=[
            ('easy', 'Easy'),
            ('medium', 'Medium'),
            ('hard', 'Hard'),
        ],
        default='medium'
    )
    category = models.CharField(max_length=100, blank=True)
    source_page = models.IntegerField(null=True, blank=True)
    is_auto_generated = models.BooleanField(default=True)
    is_edited = models.BooleanField(default=False)
    
    # Spaced repetition data
    last_reviewed = models.DateTimeField(null=True, blank=True)
    next_review = models.DateTimeField(null=True, blank=True)
    review_count = models.IntegerField(default=0)
    correct_count = models.IntegerField(default=0)
    ease_factor = models.FloatField(default=2.5)
    interval_days = models.IntegerField(default=1)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['next_review', 'created_at']
        indexes = [
            models.Index(fields=['user', 'next_review']),
            models.Index(fields=['document', 'difficulty']),
            models.Index(fields=['is_auto_generated']),
        ]
    
    def __str__(self):
        return f"{self.user.username} - {self.question[:50]}..."
    
    def calculate_next_review(self, quality):
        """
        Calculate next review date based on SM-2 algorithm
        quality: 0-5 (0=blackout, 5=perfect)
        """
        self.review_count += 1
        self.last_reviewed = timezone.now()
        
        if quality >= 3:
            if self.review_count == 1:
                self.interval_days = 1
            elif self.review_count == 2:
                self.interval_days = 6
            else:
                self.interval_days = int(self.interval_days * self.ease_factor)
            
            self.next_review = timezone.now() + timezone.timedelta(days=self.interval_days)
        else:
            self.interval_days = 1
            self.next_review = timezone.now() + timezone.timedelta(days=1)
        
        self.ease_factor = max(1.3, self.ease_factor + 0.1 - (5 - quality) * (0.08 + (5 - quality) * 0.02))
        self.save()

class FlashcardReview(models.Model):
    """
    Track flashcard review sessions
    """
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="flashcard_reviews"
    )
    flashcard = models.ForeignKey(
        Flashcard,
        on_delete=models.CASCADE,
        related_name="reviews"
    )
    quality = models.IntegerField(help_text="0-5 rating (0=blackout, 5=perfect)")
    response_time_seconds = models.IntegerField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', 'created_at']),
            models.Index(fields=['flashcard', 'created_at']),
        ]
    
    def __str__(self):
        return f"{self.user.username} - {self.flashcard.question[:30]}... - Quality: {self.quality}"

class LearningProgress(models.Model):
    """
    Learning analytics and completion tracking
    """
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="learning_progress"
    )
    document = models.ForeignKey(
        'documents.Document',
        on_delete=models.CASCADE,
        related_name="learning_progress"
    )
    
    # Progress metrics
    total_pages = models.IntegerField(default=0)
    pages_completed = models.IntegerField(default=0)
    completion_percentage = models.FloatField(default=0.0)
    time_spent_minutes = models.IntegerField(default=0)
    
    # Learning metrics
    notes_count = models.IntegerField(default=0)
    flashcards_count = models.IntegerField(default=0)
    study_sessions_count = models.IntegerField(default=0)
    
    # Performance metrics
    average_flashcard_score = models.FloatField(default=0.0)
    study_streak_days = models.IntegerField(default=0)
    last_study_date = models.DateTimeField(null=True, blank=True)
    
    # Goals and targets
    target_completion_date = models.DateTimeField(null=True, blank=True)
    daily_study_goal_minutes = models.IntegerField(default=30)
    
    is_completed = models.BooleanField(default=False)
    completed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-updated_at']
        indexes = [
            models.Index(fields=['user', 'document']),
            models.Index(fields=['user', 'is_completed']),
            models.Index(fields=['document', 'completion_percentage']),
        ]
    
    def __str__(self):
        return f"{self.user.username} - {self.document.title} ({self.completion_percentage}%)"
    
    def update_progress(self):
        """Update progress based on study sessions and activities"""
        if self.total_pages > 0:
            self.completion_percentage = (self.pages_completed / self.total_pages) * 100
            self.is_completed = self.completion_percentage >= 100
            if self.is_completed and not self.completed_at:
                self.completed_at = timezone.now()
        
        # Update study streak
        if self.last_study_date:
            days_since_last = (timezone.now().date() - self.last_study_date.date()).days
            if days_since_last == 1:
                self.study_streak_days += 1
            elif days_since_last > 1:
                self.study_streak_days = 1
        
        self.save()

class CollaborationGroup(models.Model):
    """
    Real-time collaboration groups for document study
    """
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    document = models.ForeignKey(
        'documents.Document',
        on_delete=models.CASCADE,
        related_name="collaboration_groups"
    )
    creator = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="created_groups"
    )
    members = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        related_name="collaboration_groups",
        blank=True
    )
    is_public = models.BooleanField(default=False)
    max_members = models.IntegerField(default=10)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['document', 'is_public']),
            models.Index(fields=['creator']),
        ]
    
    def __str__(self):
        return f"{self.name} - {self.document.title}"

class Discussion(models.Model):
    """
    Real-time document discussions and annotations
    """
    group = models.ForeignKey(
        CollaborationGroup,
        on_delete=models.CASCADE,
        related_name="discussions"
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="discussions"
    )
    document = models.ForeignKey(
        'documents.Document',
        on_delete=models.CASCADE,
        related_name="discussions"
    )
    
    # Content
    message = models.TextField()
    page_number = models.IntegerField(null=True, blank=True)
    position_data = models.JSONField(default=dict, help_text="Position data for annotation")
    
    # Thread management
    parent = models.ForeignKey('self', on_delete=models.CASCADE, null=True, blank=True, related_name='replies')
    
    # Metadata
    is_edited = models.BooleanField(default=False)
    edited_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['created_at']
        indexes = [
            models.Index(fields=['group', 'parent']),
            models.Index(fields=['document', 'page_number']),
            models.Index(fields=['user', 'created_at']),
        ]
    
    def __str__(self):
        return f"{self.user.username} - {self.message[:50]}..."

class Annotation(models.Model):
    """
    Real-time document annotations
    """
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="annotations"
    )
    document = models.ForeignKey(
        'documents.Document',
        on_delete=models.CASCADE,
        related_name="annotations"
    )
    group = models.ForeignKey(
        CollaborationGroup,
        on_delete=models.CASCADE,
        related_name="annotations",
        null=True,
        blank=True
    )
    
    # Annotation data
    annotation_type = models.CharField(
        max_length=20,
        choices=[
            ('highlight', 'Highlight'),
            ('note', 'Note'),
            ('bookmark', 'Bookmark'),
            ('question', 'Question'),
            ('correction', 'Correction'),
        ],
        default='highlight'
    )
    content = models.TextField(blank=True)
    highlighted_text = models.TextField(blank=True)
    page_number = models.IntegerField(null=True, blank=True)
    position_data = models.JSONField(default=dict)
    
    # Styling
    color = models.CharField(max_length=7, default='#ffff00', help_text="Hex color code")
    is_public = models.BooleanField(default=False)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', 'document']),
            models.Index(fields=['document', 'page_number']),
            models.Index(fields=['group', 'is_public']),
        ]
    
    def __str__(self):
        return f"{self.user.username} - {self.annotation_type} on {self.document.title}"
