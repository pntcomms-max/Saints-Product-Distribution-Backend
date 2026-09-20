from django.contrib import admin
from .models import Sale


@admin.register(Sale)
class SaleAdmin(admin.ModelAdmin):
    list_display = ("sales_rep", "product", "quantity", "amount", "created_at")
    list_filter = ("created_at", "product")
    search_fields = ("sales_rep__username", "sales_rep__first_name", "sales_rep__last_name", "product__name")