# backend/apps/accounts/models.py
from django.db import models
from django.contrib.auth.models import AbstractUser
from django.conf import settings
from django.db import transaction
from apps.catalog.models import Product

class PaymentMethod(models.TextChoices):
    CASH = 'CASH', 'Cash'
    ECOCASH = 'ECOCASH', 'EcoCash'
    BANK_TRANSFER = 'BANK_TRANSFER', 'Bank Transfer'
    CREDIT = 'CREDIT', 'On Credit'

class SalesOrder(models.Model):
    rep = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='sales_orders')
    customer_store = models.ForeignKey('accounts.CustomerStore', on_delete=models.CASCADE)
    total_amount = models.DecimalField(max_digits=10, decimal_places=2)
    amount_paid = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    payment_method = models.CharField(max_length=20, choices=PaymentMethod.choices)
    is_fully_paid = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
   
    product = models.ForeignKey("catalog.Product", on_delete=models.PROTECT, related_name="order_items")
    region = models.ForeignKey("catalog.Region", on_delete=models.PROTECT, related_name="order_items")
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
        return f"{self.sales_rep} sold {self.quantity} x {self.product} (${self.amount})"

class Sale(models.Model):
    sales_rep = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.CASCADE, 
        related_name="sales", 
        limit_choices_to={"role": "SALES_REP"}
    )
    product = models.ForeignKey("catalog.Product", on_delete=models.PROTECT, related_name="direct_sales")
    region = models.ForeignKey("catalog.Region", on_delete=models.PROTECT, related_name="direct_sales")
    quantity = models.PositiveIntegerField()
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)
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
        return f"{self.sales_rep} sold {self.quantity} x {self.product} (${self.amount})"


@transaction.atomic
def record_sale_and_decrement_stock(*, sales_rep, product, quantity, latitude=None, longitude=None, note=""):
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
