from django.urls import path
from . import views

app_name = 'notifications'

urlpatterns = [
    path('test/', views.test_email_page, name='test_email_page'),
    path('send/', views.send_test_email_view, name='send_test_email'),
]
