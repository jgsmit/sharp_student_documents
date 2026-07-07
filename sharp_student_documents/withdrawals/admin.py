from django.contrib import admin
from django.utils import timezone
from .models import WithdrawalMethod, WithdrawalRequest, WithdrawalSchedule, WithdrawalTransaction

@admin.register(WithdrawalMethod)
class WithdrawalMethodAdmin(admin.ModelAdmin):
    list_display = ['user', 'method_type', 'is_active', 'is_verified', 'created_at']
    list_filter = ['method_type', 'is_active', 'is_verified', 'created_at']
    search_fields = ['user__username', 'user__email', 'paypal_email']
    readonly_fields = ['created_at', 'updated_at']
    
    fieldsets = (
        ('Basic Info', {
            'fields': ('user', 'method_type', 'is_active', 'is_verified')
        }),
        ('Stripe Details', {
            'fields': ('stripe_account_id', 'stripe_refresh_token'),
            'classes': ('collapse',),
        }),
        ('PayPal Details', {
            'fields': ('paypal_email', 'paypal_verified'),
            'classes': ('collapse',),
        }),
        ('Bank Details', {
            'fields': ('bank_name', 'bank_account_number', 'bank_routing_number'),
            'classes': ('collapse',),
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',),
        }),
    )

@admin.register(WithdrawalRequest)
class WithdrawalRequestAdmin(admin.ModelAdmin):
    list_display = ['user', 'amount', 'fee', 'net_amount', 'payout_type', 'status', 'requested_at']
    list_filter = ['status', 'payout_type', 'withdrawal_method__method_type', 'requested_at']
    search_fields = ['user__username', 'user__email', 'stripe_transfer_id', 'paypal_payout_id']
    readonly_fields = ['id', 'requested_at', 'processed_at', 'completed_at']
    
    actions = ['mark_as_completed', 'mark_as_failed']
    
    def mark_as_completed(self, request, queryset):
        queryset.update(status='completed', completed_at=timezone.now())
    mark_as_completed.short_description = "Mark selected withdrawals as completed"
    
    def mark_as_failed(self, request, queryset):
        queryset.update(status='failed')
    mark_as_failed.short_description = "Mark selected withdrawals as failed"

@admin.register(WithdrawalSchedule)
class WithdrawalScheduleAdmin(admin.ModelAdmin):
    list_display = ['day_of_week', 'processing_time', 'is_active', 'last_processed', 'next_processing']
    list_filter = ['is_active', 'day_of_week']
    readonly_fields = ['last_processed', 'next_processing', 'created_at', 'updated_at']
    
    fieldsets = (
        ('Schedule', {
            'fields': ('day_of_week', 'processing_time', 'is_active')
        }),
        ('Processing Info', {
            'fields': ('last_processed', 'next_processing'),
            'classes': ('collapse',),
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',),
        }),
    )

@admin.register(WithdrawalTransaction)
class WithdrawalTransactionAdmin(admin.ModelAdmin):
    list_display = ['transaction_id', 'withdrawal_request', 'status', 'created_at', 'processed_at']
    list_filter = ['status', 'created_at', 'withdrawal_request__withdrawal_method__method_type']
    search_fields = ['transaction_id', 'stripe_transfer_id', 'paypal_payout_item_id', 'withdrawal_request__user__username']
    readonly_fields = ['transaction_id', 'created_at', 'processed_at', 'response_data']
    
    fieldsets = (
        ('Basic Info', {
            'fields': ('transaction_id', 'withdrawal_request', 'status')
        }),
        ('External IDs', {
            'fields': ('stripe_transfer_id', 'paypal_payout_item_id'),
            'classes': ('collapse',),
        }),
        ('Response Data', {
            'fields': ('response_data', 'error_message'),
            'classes': ('collapse',),
        }),
        ('Timestamps', {
            'fields': ('created_at', 'processed_at'),
            'classes': ('collapse',),
        }),
    )
