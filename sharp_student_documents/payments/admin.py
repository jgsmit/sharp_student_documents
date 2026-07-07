from django.contrib import admin
from .models import Payment

@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ("id", "order", "payment_method", "amount", "currency", "status", "created_at")
    list_filter = ("payment_method", "status")
    search_fields = ("transaction_id", "order__id")
