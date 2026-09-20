from django.db import models

class ProductUnit(models.TextChoices):
    PACK = "PACK", "Pack"
    CARTON = "CARTON", "Carton"
    CASE = "CASE", "Case"

class Manufacturer(models.Model):
    """Product owners (e.g. CRP Cigarettes)"""
    name = models.CharField(max_length=255, unique=True)
    contact_person = models.CharField(max_length=255, blank=True)
    email = models.EmailField(blank=True)
    phone = models.CharField(max_length=30, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name

class Category(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)

class Meta:
        verbose_name_plural = "Categories"

def __str__(self):
        return self.name


class Region(models.Model):
    name = models.CharField(max_length=100, unique=True)

class Meta:
        ordering = ["name"]

def __str__(self):
        return self.name

class Product(models.Model):
    manufacturer = models.ForeignKey("Manufacturer", on_delete=models.CASCADE, related_name="products")
    category = models.ForeignKey("Category", on_delete=models.SET_NULL, null=True, blank=True)
    name = models.CharField(max_length=255)  # e.g. CRP Gold
    sku = models.CharField(max_length=100, unique=True)
    unit_type = models.CharField(max_length=20, choices=ProductUnit.choices, default=ProductUnit.PACK)
    units_per_carton = models.PositiveIntegerField(default=10, help_text="Number of packs per carton")
    cartons_per_case = models.PositiveIntegerField(default=50, help_text="Number of cartons per case")
    wholesale_price = models.DecimalField(max_digits=10, decimal_places=2)
    retail_price = models.DecimalField(max_digits=10, decimal_places=2)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f"[{self.manufacturer.name}] {self.name} ({self.get_unit_type_display()})"

class Brand(models.Model):
    """e.g. Boss, RG — a product line under a manufacturer."""
    manufacturer = models.ForeignKey(Manufacturer, on_delete=models.CASCADE, related_name="brands")
    name = models.CharField(max_length=120)

class Meta:
        unique_together = ["manufacturer", "name"]

def __str__(self):
        return f"{self.name} ({self.manufacturer.name})"


class Product(models.Model):
    """
    A sellable SKU. New product lines (new brand, new manufacturer, new
    pack size) are added here as data — no code or migration needed
    beyond the initial schema.
    """
    brand = models.ForeignKey(Brand, on_delete=models.CASCADE, related_name="products")
    name = models.CharField(max_length=150)
    sku = models.CharField(max_length=40, unique=True)
    unit = models.CharField(max_length=60, default="carton")  # e.g. "carton (10 packs)"
    price = models.DecimalField(max_digits=10, decimal_places=2)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["brand__manufacturer__name", "brand__name", "name"]

    def __str__(self):
        return f"{self.name} — {self.brand}"
