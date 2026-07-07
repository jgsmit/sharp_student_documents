from django.urls import path
from . import views

app_name = 'education'

urlpatterns = [
    # Education Dashboard
    path('', views.education_dashboard, name='education_dashboard'),
    
    # Study Planner
    path('planner/', views.study_planner, name='study_planner'),
    path('planner/create/<int:document_id>/', views.create_study_plan, name='create_study_plan'),
    
    # Study Sessions
    path('session/start/<int:planner_id>/', views.start_study_session, name='start_study_session'),
    path('session/<int:session_id>/', views.study_session, name='study_session'),
    path('session/complete/<int:session_id>/', views.complete_study_session, name='complete_study_session'),
    
    # Note Editor
    path('notes/<int:document_id>/', views.note_editor, name='note_editor'),
    path('notes/save/', views.save_note, name='save_note'),
    path('notes/', views.notes_dashboard, name='notes_dashboard'),
    path('notes/delete/<int:note_id>/', views.delete_note, name='delete_note'),
    path('notes/get/<int:note_id>/', views.get_note, name='get_note'),
    path('notes/document/<int:document_id>/', views.get_document_notes, name='get_document_notes'),
    
    # Flashcard System
    path('flashcards/<int:document_id>/', views.flashcard_system, name='flashcard_system'),
    path('flashcards/generate/', views.generate_flashcards, name='generate_flashcards'),
    path('flashcards/review/', views.review_flashcard, name='review_flashcard'),
    
    # Learning Analytics
    path('analytics/', views.learning_analytics, name='learning_analytics'),
    
    # Collaboration Tools
    path('collaboration/<int:document_id>/', views.collaboration_hub, name='collaboration_hub'),
    path('collaboration/group/create/', views.create_collaboration_group, name='create_collaboration_group'),
    path('collaboration/discussion/add/', views.add_discussion, name='add_discussion'),
    path('collaboration/annotation/create/', views.create_annotation, name='create_annotation'),
]
