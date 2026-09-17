from django.contrib import admin
from .models import Region, Manufacturer, Brand, Product


@admin.register(Region)
class RegionAdmin(admin.ModelAdmin):
    list_display = ["name"]


@admin.register(Manufacturer)
class ManufacturerAdmin(admin.ModelAdmin):
    list_display = ["name"]


@admin.register(Brand)
class BrandAdmin(admin.ModelAdmin):
    list_display = ["name", "manufacturer"]
    list_filter = ["manufacturer"]


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ["name", "brand", "sku", "price", "unit", "is_active"]
    list_filter = ["brand__manufacturer", "brand", "is_active"]
    search_fields = ["name", "sku"]
