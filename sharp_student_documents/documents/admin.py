from django.contrib import admin
from .models import Document, Order, RefundRequest


@admin.register(Document)
class DocumentAdmin(admin.ModelAdmin):
    list_display = ("title", "seller", "price", "pages", "created_at")
    search_fields = ("title", "description", "seller__username")
    list_filter = ("seller", "created_at")
    prepopulated_fields = {"slug": ("title",)}
    ordering = ("-created_at",)
    date_hierarchy = "created_at"
    list_per_page = 25


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ("id", "buyer", "document", "status", "payment_method", "amount_paid", "created_at")
    search_fields = ("buyer__username", "document__title", "stripe_payment_intent", "paypal_payment_id")
    list_filter = ("status", "payment_method", "currency", "created_at")
    ordering = ("-created_at",)
    date_hierarchy = "created_at"
    list_per_page = 25


@admin.register(RefundRequest)
class RefundRequestAdmin(admin.ModelAdmin):
    list_display = ("id", "order", "buyer", "status", "reason", "paypal_refund_id", "created_at")
    search_fields = ("buyer__username", "order__paypal_payment_id", "order__document__title", "paypal_refund_id")
    list_filter = ("status", "reason", "created_at")
    ordering = ("-created_at",)
    date_hierarchy = "created_at"
    list_per_page = 25
