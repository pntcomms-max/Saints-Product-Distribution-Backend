from django.conf import settings
from django.db import models


class InventoryItem(models.Model):
    ba = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        related_name="inventory_items", limit_choices_to={"role": "BA"},
    )
    product = models.ForeignKey("catalog.Product", on_delete=models.CASCADE, related_name="inventory_items")
    quantity = models.PositiveIntegerField(default=0)
    low_stock_threshold = models.PositiveIntegerField(default=5)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ["ba", "product"]

    @property
    def status(self):
        if self.quantity <= 0:
            return "OUT"
        if self.quantity <= self.low_stock_threshold:
            return "LOW"
        return "OK"

    def __str__(self):
        return f"{self.ba} — {self.product}: {self.quantity}"
