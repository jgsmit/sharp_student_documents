from django.urls import path
from . import views

app_name = 'notifications'

urlpatterns = [
    path('test/', views.test_email_page, name='test_email_page'),
    path('send/', views.send_test_email_view, name='send_test_email'),
    path('check-new/', views.check_new_notifications, name='check_new'),
    path('', views.notification_list, name='list'),
    path('<int:notification_id>/mark-read/', views.mark_notification_read, name='mark_read'),
    path('mark-all-read/', views.mark_all_notifications_read, name='mark_all_read'),
    path('<int:notification_id>/delete/', views.delete_notification, name='delete'),
]
