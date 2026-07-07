from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse, HttpResponse
from django.utils import timezone
from django.db.models import Count, Sum, Avg, Q, F
from django.views.decorators.http import require_POST
from django.core.paginator import Paginator
import json
import re
from datetime import timedelta, datetime

from documents.models import Document, Order
from .models import (
    StudyPlanner, StudySession, Note, Flashcard, FlashcardReview,
    LearningProgress, CollaborationGroup, Discussion, Annotation
)

@login_required
def education_dashboard(request):
    """
    Education dashboard showing user's documents with access to flashcards and notes
    """
    # Get documents user has purchased
    purchased_documents = Document.objects.filter(
        orders__buyer=request.user,
        orders__status="paid"
    ).select_related('seller', 'category').annotate(
        has_notes=Count('notes'),
        has_flashcards=Count('flashcards')
    ).distinct()
    
    # Get documents user has uploaded (if seller)
    uploaded_documents = []
    if getattr(request.user, 'is_seller', False):
        uploaded_documents = Document.objects.filter(
            seller=request.user
        ).select_related('category').annotate(
            has_notes=Count('notes'),
            has_flashcards=Count('flashcards')
        )
    
    context = {
        'purchased_documents': purchased_documents,
        'uploaded_documents': uploaded_documents,
    }
    
    return render(request, 'education/education_dashboard.html', context)

@login_required
def study_planner(request):
    """
    Study planner dashboard with calendar and scheduling
    """
    # Get user's study plans
    study_plans = StudyPlanner.objects.filter(user=request.user).order_by('start_date')
    
    # Get upcoming sessions
    upcoming_sessions = StudySession.objects.filter(
        user=request.user,
        start_time__gte=timezone.now(),
        start_time__lte=timezone.now() + timedelta(days=7)
    ).order_by('start_time')
    
    # Get learning progress
    progress_data = LearningProgress.objects.filter(user=request.user).order_by('-updated_at')
    
    context = {
        'study_plans': study_plans,
        'upcoming_sessions': upcoming_sessions,
        'progress_data': progress_data,
    }
    
    return render(request, 'education/study_planner.html', context)

@login_required
def create_study_plan(request, document_id):
    """
    Create a new study plan for a document
    """
    document = get_object_or_404(Document, id=document_id)
    
    if request.method == 'POST':
        title = request.POST.get('title')
        description = request.POST.get('description', '')
        start_date = request.POST.get('start_date')
        end_date = request.POST.get('end_date')
        study_duration = int(request.POST.get('study_duration', 30))
        study_frequency = request.POST.get('study_frequency', 'weekly')
        priority = request.POST.get('priority', 'medium')
        
        # Parse dates
        start_dt = datetime.strptime(start_date, '%Y-%m-%dT%H:%M')
        end_dt = datetime.strptime(end_date, '%Y-%m-%dT%H:%M')
        
        # Create study plan
        plan = StudyPlanner.objects.create(
            user=request.user,
            document=document,
            title=title,
            description=description,
            start_date=start_dt,
            end_date=end_dt,
            study_duration=study_duration,
            study_frequency=study_frequency,
            target_completion=end_dt,
            priority=priority
        )
        
        # Create learning progress record
        progress, created = LearningProgress.objects.get_or_create(
            user=request.user,
            document=document,
            defaults={
                'total_pages': document.pages or 0,
                'target_completion_date': end_dt,
            }
        )
        
        messages.success(request, 'Study plan created successfully!')
        return redirect('education:study_planner')
    
    return render(request, 'education/create_study_plan.html', {'document': document})

@login_required
def note_editor(request, document_id):
    """
    Built-in note editor with document highlighting
    """
    document = get_object_or_404(Document, id=document_id)
    
    # Get user's notes for this document
    notes = Note.objects.filter(user=request.user, document=document).order_by('-updated_at')
    
    # Get user's annotations
    annotations = Annotation.objects.filter(user=request.user, document=document).order_by('page_number')
    
    context = {
        'document': document,
        'notes': notes,
        'annotations': annotations,
    }
    
    return render(request, 'education/note_editor.html', context)

@login_required
def notes_dashboard(request):
    """
    Dashboard showing all user's notes across all documents
    """
    # Get all user's notes with document information
    notes = Note.objects.filter(user=request.user).select_related('document', 'document__category').order_by('-updated_at')
    
    # Group notes by document
    notes_by_document = {}
    for note in notes:
        doc_id = note.document.id
        if doc_id not in notes_by_document:
            notes_by_document[doc_id] = {
                'document': note.document,
                'notes': [],
                'total_notes': 0
            }
        notes_by_document[doc_id]['notes'].append(note)
        notes_by_document[doc_id]['total_notes'] += 1
    
    # Calculate statistics
    total_notes = notes.count()
    total_documents_with_notes = len(notes_by_document)
    recent_notes = notes[:5]  # Last 5 notes
    
    context = {
        'notes_by_document': notes_by_document,
        'total_notes': total_notes,
        'total_documents_with_notes': total_documents_with_notes,
        'recent_notes': recent_notes,
        'notes': notes,  # For backward compatibility
    }
    
    return render(request, 'education/notes_dashboard.html', context)

@login_required
@require_POST
def save_note(request):
    """
    Save or update a note
    """
    note_id = request.POST.get('note_id')
    document_id = request.POST.get('document_id')
    title = request.POST.get('title')
    content = request.POST.get('content')
    highlighted_text = request.POST.get('highlighted_text', '')
    page_number = request.POST.get('page_number')
    position_data = request.POST.get('position_data', '{}')
    tags = request.POST.get('tags', '')
    is_favorite = request.POST.get('is_favorite') == 'on'
    
    document = get_object_or_404(Document, id=document_id)
    
    if note_id:
        # Update existing note
        note = get_object_or_404(Note, id=note_id, user=request.user)
        note.title = title
        note.content = content
        note.highlighted_text = highlighted_text
        note.page_number = int(page_number) if page_number else None
        note.position_data = json.loads(position_data)
        note.tags = tags
        note.is_favorite = is_favorite
        note.save()
        message = 'Note updated successfully!'
    else:
        # Create new note
        note = Note.objects.create(
            user=request.user,
            document=document,
            title=title,
            content=content,
            highlighted_text=highlighted_text,
            page_number=int(page_number) if page_number else None,
            position_data=json.loads(position_data),
            tags=tags,
            is_favorite=is_favorite
        )
        message = 'Note created successfully!'
    
    return JsonResponse({
        'status': 'success',
        'message': message,
        'note_id': note.id
    })

@login_required
def delete_note(request, note_id):
    """
    Delete a note
    """
    note = get_object_or_404(Note, id=note_id, user=request.user)
    note.delete()
    return JsonResponse({
        'status': 'success',
        'message': 'Note deleted successfully!'
    })

@login_required
def get_note(request, note_id):
    """
    Get a single note for editing
    """
    note = get_object_or_404(Note, id=note_id, user=request.user)
    return JsonResponse({
        'status': 'success',
        'note': {
            'id': note.id,
            'title': note.title,
            'content': note.content,
            'highlighted_text': note.highlighted_text,
            'page_number': note.page_number,
            'position_data': note.position_data,
            'tags': note.tags,
            'is_favorite': note.is_favorite,
            'updated_at': note.updated_at.isoformat()
        }
    })

@login_required
def get_document_notes(request, document_id):
    """
    Get all notes for a document
    """
    document = get_object_or_404(Document, id=document_id)
    notes = Note.objects.filter(user=request.user, document=document).order_by('-updated_at')
    
    return JsonResponse({
        'status': 'success',
        'notes': [
            {
                'id': note.id,
                'title': note.title,
                'content': note.content,
                'highlighted_text': note.highlighted_text,
                'page_number': note.page_number,
                'tags': note.tags,
                'is_favorite': note.is_favorite,
                'updated_at': note.updated_at.isoformat()
            }
            for note in notes
        ]
    })

@login_required
def flashcard_system(request, document_id):
    """
    Flashcard system with spaced repetition
    """
    document = get_object_or_404(Document, id=document_id)
    
    # Get flashcards due for review
    flashcards = Flashcard.objects.filter(
        user=request.user,
        document=document
    ).order_by('next_review')
    
    # Get statistics
    total_cards = flashcards.count()
    due_cards = flashcards.filter(next_review__lte=timezone.now()).count()
    new_cards = flashcards.filter(review_count=0).count()
    
    context = {
        'document': document,
        'flashcards': flashcards,
        'total_cards': total_cards,
        'due_cards': due_cards,
        'new_cards': new_cards,
    }
    
    return render(request, 'education/flashcard_system.html', context)

@login_required
@require_POST
def generate_flashcards(request):
    """
    Auto-generate flashcards from document content
    """
    document_id = request.POST.get('document_id')
    num_cards = int(request.POST.get('num_cards', 10))
    
    document = get_object_or_404(Document, id=document_id)
    
    # Get document content (preview_text or description)
    content = document.preview_text or document.description or ''
    
    if not content:
        return JsonResponse({
            'status': 'error',
            'message': 'No content available to generate flashcards from'
        })
    
    # Simple flashcard generation (in production, use NLP/ML)
    flashcards_created = 0
    
    # Split content into sentences
    sentences = re.split(r'[.!?]+', content)
    sentences = [s.strip() for s in sentences if len(s.strip()) > 20]
    
    for i, sentence in enumerate(sentences[:num_cards]):
        # Create question-answer pairs
        if len(sentence) > 50:
            # Split into question and answer
            words = sentence.split()
            mid = len(words) // 2
            question = ' '.join(words[:mid]) + '...'
            answer = ' '.join(words[mid:])
            
            Flashcard.objects.create(
                user=request.user,
                document=document,
                question=f"What comes after: {question}",
                answer=answer,
                difficulty='medium',
                is_auto_generated=True
            )
            flashcards_created += 1
    
    return JsonResponse({
        'status': 'success',
        'message': f'Generated {flashcards_created} flashcards successfully!',
        'cards_created': flashcards_created
    })

@login_required
@require_POST
def review_flashcard(request):
    """
    Review a flashcard and update spaced repetition
    """
    flashcard_id = request.POST.get('flashcard_id')
    quality = int(request.POST.get('quality', 3))  # 0-5 rating
    response_time = int(request.POST.get('response_time', 0))
    
    flashcard = get_object_or_404(Flashcard, id=flashcard_id, user=request.user)
    
    # Record the review
    FlashcardReview.objects.create(
        user=request.user,
        flashcard=flashcard,
        quality=quality,
        response_time_seconds=response_time
    )
    
    # Update flashcard with spaced repetition
    flashcard.calculate_next_review(quality)
    
    # Get next flashcard
    next_card = Flashcard.objects.filter(
        user=request.user,
        document=flashcard.document,
        next_review__lte=timezone.now()
    ).exclude(id=flashcard_id).first()
    
    return JsonResponse({
        'status': 'success',
        'next_card_id': next_card.id if next_card else None,
        'next_card_question': next_card.question if next_card else None,
        'next_card_answer': next_card.answer if next_card else None,
        'cards_remaining': Flashcard.objects.filter(
            user=request.user,
            document=flashcard.document,
            next_review__lte=timezone.now()
        ).count()
    })

@login_required
def learning_analytics(request):
    """
    Learning analytics and progress tracking
    """
    # Get user's learning progress
    progress_data = LearningProgress.objects.filter(user=request.user)
    
    # Calculate overall statistics
    total_documents = progress_data.count()
    completed_documents = progress_data.filter(is_completed=True).count()
    total_study_time = progress_data.aggregate(total=Sum('time_spent_minutes'))['total'] or 0
    total_notes = progress_data.aggregate(total=Sum('notes_count'))['total'] or 0
    total_flashcards = progress_data.aggregate(total=Sum('flashcards_count'))['total'] or 0
    
    # Get recent activity
    recent_sessions = StudySession.objects.filter(
        user=request.user
    ).order_by('-start_time')[:10]
    
    # Get study streak
    current_streak = 0
    if progress_data.exists():
        current_streak = max(p.study_streak_days for p in progress_data)
    
    # Get learning trends (last 30 days)
    thirty_days_ago = timezone.now() - timedelta(days=30)
    daily_study = StudySession.objects.filter(
        user=request.user,
        start_time__gte=thirty_days_ago
    ).extra({
        'date': 'date(start_time)'
    }).values('date').annotate(
        minutes=Sum('duration_minutes'),
        sessions=Count('id')
    ).order_by('date')
    
    context = {
        'progress_data': progress_data,
        'total_documents': total_documents,
        'completed_documents': completed_documents,
        'total_study_time': total_study_time,
        'total_notes': total_notes,
        'total_flashcards': total_flashcards,
        'recent_sessions': recent_sessions,
        'current_streak': current_streak,
        'daily_study': daily_study,
    }
    
    return render(request, 'education/learning_analytics.html', context)

@login_required
def collaboration_hub(request, document_id):
    """
    Real-time collaboration and discussion hub
    """
    document = get_object_or_404(Document, id=document_id)
    
    # Get user's collaboration groups for this document
    groups = CollaborationGroup.objects.filter(
        Q(document=document) & 
        (Q(members=request.user) | Q(creator=request.user))
    )
    
    # Get public groups
    public_groups = CollaborationGroup.objects.filter(
        document=document,
        is_public=True
    )
    
    # Get discussions
    discussions = Discussion.objects.filter(
        document=document,
        group__in=groups
    ).order_by('created_at')
    
    # Get annotations
    annotations = Annotation.objects.filter(
        document=document
    ).filter(
        Q(user=request.user) | Q(is_public=True)
    ).order_by('page_number')
    
    context = {
        'document': document,
        'groups': groups,
        'public_groups': public_groups,
        'discussions': discussions,
        'annotations': annotations,
    }
    
    return render(request, 'education/collaboration_hub.html', context)

@login_required
@require_POST
def create_collaboration_group(request):
    """
    Create a new collaboration group
    """
    document_id = request.POST.get('document_id')
    name = request.POST.get('name')
    description = request.POST.get('description', '')
    is_public = request.POST.get('is_public') == 'on'
    max_members = int(request.POST.get('max_members', 10))
    
    document = get_object_or_404(Document, id=document_id)
    
    group = CollaborationGroup.objects.create(
        name=name,
        description=description,
        document=document,
        creator=request.user,
        is_public=is_public,
        max_members=max_members
    )
    
    # Add creator as member
    group.members.add(request.user)
    
    return JsonResponse({
        'status': 'success',
        'message': 'Collaboration group created successfully!',
        'group_id': group.id
    })

@login_required
@require_POST
def add_discussion(request):
    """
    Add a new discussion or reply
    """
    group_id = request.POST.get('group_id')
    document_id = request.POST.get('document_id')
    message = request.POST.get('message')
    page_number = request.POST.get('page_number')
    parent_id = request.POST.get('parent_id')
    position_data = request.POST.get('position_data', '{}')
    
    group = get_object_or_404(CollaborationGroup, id=group_id)
    document = get_object_or_404(Document, id=document_id)
    parent = Discussion.objects.filter(id=parent_id).first() if parent_id else None
    
    discussion = Discussion.objects.create(
        group=group,
        user=request.user,
        document=document,
        message=message,
        page_number=int(page_number) if page_number else None,
        position_data=json.loads(position_data),
        parent=parent
    )
    
    return JsonResponse({
        'status': 'success',
        'message': 'Discussion added successfully!',
        'discussion_id': discussion.id,
        'created_at': discussion.created_at.strftime('%Y-%m-%d %H:%M:%S')
    })

@login_required
@require_POST
def create_annotation(request):
    """
    Create a new annotation
    """
    document_id = request.POST.get('document_id')
    group_id = request.POST.get('group_id')
    annotation_type = request.POST.get('annotation_type', 'highlight')
    content = request.POST.get('content', '')
    highlighted_text = request.POST.get('highlighted_text', '')
    page_number = request.POST.get('page_number')
    position_data = request.POST.get('position_data', '{}')
    color = request.POST.get('color', '#ffff00')
    is_public = request.POST.get('is_public') == 'on'
    
    document = get_object_or_404(Document, id=document_id)
    group = CollaborationGroup.objects.filter(id=group_id).first() if group_id else None
    
    annotation = Annotation.objects.create(
        user=request.user,
        document=document,
        group=group,
        annotation_type=annotation_type,
        content=content,
        highlighted_text=highlighted_text,
        page_number=int(page_number) if page_number else None,
        position_data=json.loads(position_data),
        color=color,
        is_public=is_public
    )
    
    return JsonResponse({
        'status': 'success',
        'message': 'Annotation created successfully!',
        'annotation_id': annotation.id
    })

@login_required
def start_study_session(request, planner_id):
    """
    Start a new study session
    """
    planner = get_object_or_404(StudyPlanner, id=planner_id, user=request.user)
    
    # Create new study session
    session = StudySession.objects.create(
        user=request.user,
        planner=planner,
        document=planner.document,
        start_time=timezone.now()
    )
    
    return redirect('education:study_session', session_id=session.id)

@login_required
def study_session(request, session_id):
    """
    Active study session view
    """
    session = get_object_or_404(StudySession, id=session_id, user=request.user)
    
    if session.is_completed:
        messages.info(request, 'This study session has already been completed.')
        return redirect('education:study_planner')
    
    # Get document and related notes
    document = session.document
    notes = Note.objects.filter(user=request.user, document=document)
    
    context = {
        'session': session,
        'document': document,
        'notes': notes,
    }
    
    return render(request, 'education/study_session.html', context)

@login_required
@require_POST
def complete_study_session(request, session_id):
    """
    Complete a study session
    """
    session = get_object_or_404(StudySession, id=session_id, user=request.user)
    
    if session.is_completed:
        return JsonResponse({'status': 'error', 'message': 'Session already completed'})
    
    # Update session
    session.end_time = timezone.now()
    session.is_completed = True
    session.notes_taken = request.POST.get('notes', '')
    session.pages_studied = int(request.POST.get('pages_studied', 0))
    session.calculate_duration()
    
    # Update learning progress
    progress, created = LearningProgress.objects.get_or_create(
        user=request.user,
        document=session.document,
        defaults={'total_pages': session.document.pages or 0}
    )
    
    progress.time_spent_minutes += session.duration_minutes or 0
    progress.pages_completed += session.pages_studied
    progress.study_sessions_count += 1
    progress.last_study_date = timezone.now()
    progress.update_progress()
    
    return JsonResponse({
        'status': 'success',
        'message': 'Study session completed successfully!',
        'duration': session.duration_minutes,
        'pages_studied': session.pages_studied
    })
