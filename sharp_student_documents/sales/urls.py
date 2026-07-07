from django.urls import path
from . import views

app_name = 'sales'

urlpatterns = [
    path('dashboard/', views.seller_dashboard, name='seller_dashboard'),
    path('history/', views.sales_history, name='sales_history'),
    path('withdraw/', views.request_withdrawal, name='request_withdrawal'),
    path('transactions/', views.transaction_history, name='transaction_history'),
    path('export/', views.export_sales_csv, name='export_sales_csv'),
    
    # Admin URLs
    path('admin/withdrawals/', views.manage_withdrawals, name='manage_withdrawals'),
    path('admin/approve/<int:request_id>/', views.approve_withdrawal, name='approve_withdrawal'),
]
