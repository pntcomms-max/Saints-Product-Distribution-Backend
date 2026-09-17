from django.contrib import admin
from .models import Sale


@admin.register(Sale)
class SaleAdmin(admin.ModelAdmin):
    list_display = ["ba", "product", "quantity", "amount", "region", "created_at"]
    list_filter = ["region", "product__brand"]
    readonly_fields = ["amount"]
