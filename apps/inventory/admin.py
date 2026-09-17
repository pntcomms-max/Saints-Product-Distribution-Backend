from django.contrib import admin
from .models import InventoryItem


@admin.register(InventoryItem)
class InventoryItemAdmin(admin.ModelAdmin):
    list_display = ["ba", "product", "quantity", "status", "updated_at"]
    list_filter = ["ba__region", "product__brand"]
