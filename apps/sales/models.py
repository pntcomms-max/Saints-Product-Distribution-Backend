from django.conf import settings
from django.db import models
from django.db import transaction


class Sale(models.Model):
    """
    Every sale is cash-basis: recorded the moment it happens, at the
    location it happened, and immediately decrements the BA's stock.
    """
    ba = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        related_name="sales", limit_choices_to={"role": "BA"},
    )
    product = models.ForeignKey("catalog.Product", on_delete=models.PROTECT, related_name="sales")
    region = models.ForeignKey("catalog.Region", on_delete=models.PROTECT, related_name="sales")
    quantity = models.PositiveIntegerField()
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)  # snapshot at sale time
    amount = models.DecimalField(max_digits=10, decimal_places=2, editable=False)
    latitude = models.FloatField(null=True, blank=True)
    longitude = models.FloatField(null=True, blank=True)
    note = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def save(self, *args, **kwargs):
        self.amount = self.unit_price * self.quantity
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.ba} sold {self.quantity} x {self.product} (${self.amount})"


@transaction.atomic
def record_sale_and_decrement_stock(*, ba, product, quantity, latitude=None, longitude=None, note=""):
    """
    Single entry point used by the API (and importable from anywhere
    else, e.g. a management command or a future POS integration) so
    "sell" and "decrement inventory" can never drift out of sync.
    """
    from apps.inventory.models import InventoryItem

    item, _ = InventoryItem.objects.select_for_update().get_or_create(ba=ba, product=product)
    if item.quantity < quantity:
        raise ValueError(f"Not enough stock: {item.quantity} available, {quantity} requested.")

    item.quantity -= quantity
    item.save(update_fields=["quantity", "updated_at"])

    sale = Sale.objects.create(
        ba=ba, product=product, region=ba.region, quantity=quantity,
        unit_price=product.price, latitude=latitude, longitude=longitude, note=note,
    )
    return sale
