from django.db import models


class Region(models.Model):
    name = models.CharField(max_length=100, unique=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class Manufacturer(models.Model):
    """e.g. CRP. Adding a new manufacturer is just adding a row here."""
    name = models.CharField(max_length=120, unique=True)

    def __str__(self):
        return self.name


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
