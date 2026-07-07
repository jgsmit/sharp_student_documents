from django.contrib import admin
from django.utils.html import format_html
from django.utils.safestring import mark_safe
from .models import TwoFactorAuth, IdentityVerification, SecurityLog, FraudDetection, Watermark


@admin.register(TwoFactorAuth)
class TwoFactorAuthAdmin(admin.ModelAdmin):
    list_display = ('user', 'is_enabled', 'created_at', 'last_used')
    list_filter = ('is_enabled', 'created_at')
    search_fields = ('user__username', 'user__email')
    readonly_fields = ('created_at', 'last_used')
    ordering = ('-created_at',)
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('user')


@admin.register(IdentityVerification)
class IdentityVerificationAdmin(admin.ModelAdmin):
    list_display = ('user', 'verification_type', 'status', 'created_at', 'verified_by')
    list_filter = ('verification_type', 'status', 'created_at')
    search_fields = ('user__username', 'user__email')
    readonly_fields = ('created_at', 'updated_at')
    ordering = ('-created_at',)
    
    fieldsets = (
        ('Verification Information', {
            'fields': ('user', 'verification_type', 'status')
        }),
        ('Verification Data', {
            'fields': ('verification_data',)
        }),
        ('Review Process', {
            'fields': ('verified_by', 'verified_at', 'rejection_reason')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at', 'expires_at')
        }),
    )
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('user', 'verified_by')


@admin.register(SecurityLog)
class SecurityLogAdmin(admin.ModelAdmin):
    list_display = ('user', 'event_type', 'severity', 'ip_address', 'created_at')
    list_filter = ('event_type', 'severity', 'created_at')
    search_fields = ('user__username', 'user__email', 'ip_address')
    readonly_fields = ('user', 'event_type', 'ip_address', 'user_agent', 'details', 'severity', 'created_at')
    ordering = ('-created_at',)
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('user')
    
    def has_add_permission(self, request):
        return False  # Security logs should not be manually added
    
    def has_change_permission(self, request, obj=None):
        return False  # Security logs should not be modified


@admin.register(FraudDetection)
class FraudDetectionAdmin(admin.ModelAdmin):
    list_display = ('user', 'pattern_type', 'risk_score', 'is_confirmed', 'auto_action_taken', 'created_at')
    list_filter = ('pattern_type', 'is_confirmed', 'auto_action_taken', 'created_at')
    search_fields = ('user__username', 'user__email')
    readonly_fields = ('created_at', 'details')
    ordering = ('-risk_score', '-created_at')
    
    fieldsets = (
        ('Case Information', {
            'fields': ('user', 'pattern_type', 'risk_score', 'is_confirmed')
        }),
        ('Case Details', {
            'fields': ('details',)
        }),
        ('Review Process', {
            'fields': ('reviewed_by', 'reviewed_at', 'auto_action_taken')
        }),
        ('Timestamps', {
            'fields': ('created_at',)
        }),
    )
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('user', 'reviewed_by')
    
    def risk_score_color(self, obj):
        if obj.risk_score >= 80:
            return mark_safe('<span style="color: red; font-weight: bold;">{}</span>'.format(obj.risk_score))
        elif obj.risk_score >= 50:
            return mark_safe('<span style="color: orange; font-weight: bold;">{}</span>'.format(obj.risk_score))
        else:
            return mark_safe('<span style="color: green;">{}</span>'.format(obj.risk_score))
    risk_score_color.short_description = 'Risk Score'


@admin.register(Watermark)
class WatermarkAdmin(admin.ModelAdmin):
    list_display = ('user', 'is_enabled', 'watermark_text', 'watermark_opacity', 'watermark_position', 'created_at')
    list_filter = ('is_enabled', 'watermark_position', 'created_at')
    search_fields = ('user__username', 'user__email', 'watermark_text')
    ordering = ('-created_at',)
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('user')


# Customize admin site header and title
admin.site.site_header = 'SharpDocs Security Administration'
admin.site.site_title = 'Security Admin'
admin.site.index_title = 'Security Management'
