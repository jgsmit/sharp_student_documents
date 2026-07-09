from django.urls import path
from django.views.generic import RedirectView
from . import views
from . import views_analytics

app_name = 'documents'

urlpatterns = [
    # Redirect bare /documents/ to /documents/all/ (prevents 404 from crawled links)
    path("", RedirectView.as_view(url="/documents/all/", permanent=True)),

    # Document Management
    path("all/", views.document_list, name="document_list"),
    path("category/<slug:slug>/", views.category_detail, name="category_detail"),
    path("upload/", views.upload_document, name="upload_document"),
    path("seller-documents/", views.seller_documents, name="seller_documents"),
    path("seller-refunds/", views.seller_refunds, name="seller_refunds"),
    path("my-purchases/", views.my_purchases, name="my_purchases"),
    path("refunds/request/<int:order_id>/", views.request_refund, name="request_refund"),
    path("download/<int:order_id>/", views.download_document, name="download_document"),
    path("download-owner/<int:document_id>/", views.download_owner_document, name="download_owner_document"),
    path("<int:pk>/edit/", views.edit_document, name="edit_document"),
    path("<int:pk>/delete/", views.delete_document, name="delete_document"),
    
    # Unified Dashboard System
    path("dashboard/", views.dashboard, name="dashboard"),
    path("admin-dashboard/", views.admin_dashboard, name="admin_dashboard"),
    path("seller-dashboard/", views.seller_dashboard, name="seller_dashboard"),
    path("buyer-dashboard/", views.buyer_dashboard, name="buyer_dashboard"),
    
    # Search URLs
    path("advanced-search/", views.advanced_search, name="advanced_search"),
    
    # Admin Management URLs
    path("admin/manage-users/", views.admin_manage_users, name="admin_manage_users"),
    path("admin/user/add/", views.admin_add_user, name="admin_add_user"),
    path("admin/user/<int:user_id>/view/", views.admin_view_user, name="admin_view_user"),
    path("admin/user/<int:user_id>/edit/", views.admin_edit_user, name="admin_edit_user"),
    path("admin/user/<int:user_id>/delete/", views.admin_delete_user, name="admin_delete_user"),
    path("admin/user/<int:user_id>/toggle-status/", views.admin_toggle_user_status, name="admin_toggle_user_status"),
    path("admin/user/<int:user_id>/documents/", views.admin_user_documents, name="admin_user_documents"),
    path("admin/user/<int:user_id>/orders/", views.admin_user_orders, name="admin_user_orders"),
    path("admin/user/<int:user_id>/reviews/", views.admin_user_reviews, name="admin_user_reviews"),
    path("admin/document/<int:pk>/edit/", views.admin_edit_document, name="admin_edit_document"),
    path("admin/document/<int:pk>/delete/", views.admin_delete_document, name="admin_delete_document"),
    path("admin/manage-documents/", views.admin_manage_documents, name="admin_manage_documents"),
    path("admin/manage-reviews/", views.admin_manage_reviews, name="admin_manage_reviews"),
    path("admin/manage-payments/", views.admin_manage_payments, name="admin_manage_payments"),
    path("admin/manage-payments/<int:order_id>/details/", views.admin_payment_details, name="admin_payment_details"),
    path("admin/manage-payments/<int:order_id>/receipt/", views.admin_download_receipt, name="admin_download_receipt"),
    path("admin/manage-withdrawals/", views.admin_manage_withdrawals, name="admin_manage_withdrawals"),
    path("admin/manage-refunds/", views.admin_manage_refunds, name="admin_manage_refunds"),
    path("admin/notifications/", views.admin_notifications, name="admin_notifications"),
    path("admin/notifications/check-new/", views.check_new_notifications, name="check_new_notifications"),
    path("admin/notifications/<int:notification_id>/mark-read/", views.mark_notification_read, name="mark_notification_read"),
    path("admin/notifications/mark-all-read/", views.mark_all_notifications_read, name="mark_all_notifications_read"),
    path("admin/notifications/<int:notification_id>/delete/", views.delete_notification, name="delete_notification"),
    path("admin/notifications/clear-read/", views.clear_read_notifications, name="clear_read_notifications"),
    path("admin/security-log/", views.admin_security_log, name="admin_security_log"),
    path("admin/identity-verifications/", views.admin_identity_verifications, name="admin_identity_verifications"),
    path("admin/view-financials/", views.admin_view_financials, name="admin_view_financials"),
    path("admin/commission-tracking/", views.admin_commission_tracking, name="admin_commission_tracking"),
    
    # System Maintenance URLs
    path("admin/maintenance/database/", views.database_maintenance, name="database_maintenance"),
    path("admin/maintenance/email-queue/", views.email_queue_process, name="email_queue_process"),
    path("admin/maintenance/security-audit/", views.security_audit, name="security_audit"),
    path("admin/maintenance/backup/", views.backup_system, name="backup_system"),
    
    # Orders / Checkout
    path("<slug:slug>/buy/", views.create_order, name="create_order"),  
    
    # Analytics URLs
    path('analytics/', views_analytics.seller_analytics, name='seller_analytics'),
    path('analytics/marketplace/', views_analytics.marketplace_analytics, name='marketplace_analytics'),
    path('analytics/document/<int:document_id>/', views_analytics.document_performance, name='document_performance'),
    path('analytics/api/', views_analytics.analytics_api, name='analytics_api'),
    path('analytics/marketplace/api/', views_analytics.marketplace_analytics_api, name='marketplace_analytics_api'),
    
    # Document Detail (must be last to avoid conflicts)
    path("<slug:slug>/", views.document_detail, name="document_detail"),
    
    # Service Worker
    path('sw.js', views.service_worker, name='service_worker'),
]
