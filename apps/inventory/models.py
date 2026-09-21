from django.conf import settings
from django.db import models
from apps.catalog.models import Product

class InventoryItem(models.Model):
    sales_rep = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        related_name="inventory_items", limit_choices_to={"role": "Sales_Rep"},
    )
    product = models.ForeignKey("catalog.Product", on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(default=0)
    low_stock_threshold = models.PositiveIntegerField(default=5)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ["sales_rep", "product"]

    @property
    def status(self):
        if self.quantity <= 0:
            return "OUT"
        if self.quantity <= self.low_stock_threshold:
            return "LOW"
        return "OK"

    def __str__(self):
        return f"{self.sales_rep} — {self.product}: {self.quantity}"

class StorageType(models.TextChoices):
    MAIN_DEPOT = 'MAIN_DEPOT', 'Main Depot / Warehouse'
    TRANSIT_VAN = 'TRANSIT_VAN', 'Transit Van / Sales Rep'

class InventoryLocation(models.Model):
    name = models.CharField(max_length=255) # e.g. "Harare Central Depot" or "Van 04 - Tinashe"
    location_type = models.CharField(max_length=20, choices=StorageType.choices, default=StorageType.TRANSIT_VAN)
    assigned_rep = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='inventory_locations')
    
    def __str__(self):
        return f"{self.name} ({self.get_location_type_display()})"

class StockTransferStatus(models.TextChoices):
    PENDING = 'PENDING', 'Pending Rep Acceptance'
    ACCEPTED = 'ACCEPTED', 'Accepted into Van Stock'
    REJECTED = 'REJECTED', 'Rejected / Damaged in Transit'

class StockTransfer(models.Model):
    """Stock movement from Warehouse to Sales Rep Van"""
    transfer_number = models.CharField(max_length=50, unique=True)
    source_location = models.ForeignKey(InventoryLocation, on_delete=models.CASCADE, related_name='transfers_sent')
    destination_location = models.ForeignKey(InventoryLocation, on_delete=models.CASCADE, related_name='transfers_received')
    status = models.CharField(max_length=20, choices=StockTransferStatus.choices, default=StockTransferStatus.PENDING)
    created_at = models.DateTimeField(auto_now_add=True)
    accepted_at = models.DateTimeField(null=True, blank=True)

class StockTransferItem(models.Model):
    transfer = models.ForeignKey(StockTransfer, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey('catalog.Product', on_delete=models.CASCADE)
    cases_quantity = models.PositiveIntegerField(default=0)
    cartons_quantity = models.PositiveIntegerField(default=0)
    packs_quantity = models.PositiveIntegerField(default=0)