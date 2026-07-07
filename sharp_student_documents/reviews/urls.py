from django.urls import path
from . import views

app_name = 'reviews'

urlpatterns = [
    path("my-reviews/", views.my_reviews, name="my_reviews"),
    path("add/<int:document_id>/", views.add_review, name="add_review"),
    path('moderation/', views.review_moderation, name='moderation'),
    path('contact/', views.contact, name='contact'),
    path('resources/', views.resources, name='resources'),
    path('faq/', views.faq_view, name='faq'),
    path('help-center/', views.help_center_view, name='help_center'),
    path('help-article/<int:pk>/', views.help_article_detail_view, name='help_article_detail'),
    path('terms/', views.terms, name='terms'),
    path('privacy/', views.privacy, name='privacy'),
]
