from django.contrib import admin
from .models import Alert


@admin.register(Alert)
class AlertAdmin(admin.ModelAdmin):
    list_display = ["kind", "ba", "product", "message", "created_at", "resolved_at", "notified_at"]
    list_filter = ["kind", "resolved_at"]
