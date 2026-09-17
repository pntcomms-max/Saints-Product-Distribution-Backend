from django.conf import settings
from django.db import models


class Alert(models.Model):
    """
    A persisted, deduplicated alert. We store these (rather than just
    computing on the fly like the demand forecast) for two reasons:
    1. So a push notification is only ever sent once per condition,
       not every time the detection job runs.
    2. So supervisors/managers can acknowledge ("resolve") one, and it
       stays resolved even if the underlying condition briefly recurs.
    """
    class Kind(models.TextChoices):
        OUT_OF_STOCK = "OUT_OF_STOCK", "Out of stock"
        LOW_STOCK = "LOW_STOCK", "Low stock"
        INACTIVE_BA = "INACTIVE_BA", "BA inactive"

    kind = models.CharField(max_length=20, choices=Kind.choices)
    ba = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="alerts")
    product = models.ForeignKey("catalog.Product", on_delete=models.CASCADE, null=True, blank=True, related_name="alerts")
    message = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)
    resolved_at = models.DateTimeField(null=True, blank=True)
    notified_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]
        # one open alert per (ba, kind, product) at a time — reopening
        # happens naturally if it's resolved and the condition recurs
        constraints = [
            models.UniqueConstraint(
                fields=["ba", "kind", "product"],
                condition=models.Q(resolved_at__isnull=True),
                name="one_open_alert_per_ba_kind_product",
            )
        ]

    def __str__(self):
        return f"[{self.kind}] {self.ba}: {self.message}"
