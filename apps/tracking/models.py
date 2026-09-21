from django.conf import settings
from django.db import models


class CheckIn(models.Model):
    class Source(models.TextChoices):
        MANUAL = "MANUAL", "Manual check-in"
        PASSIVE = "PASSIVE", "Passive background ping"

    sales_rep = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        related_name="checkins", limit_choices_to={"role": "SALES_REP"},
    )
    region = models.ForeignKey("catalog.Region", on_delete=models.SET_NULL, null=True, related_name="checkins")
    latitude = models.FloatField(null=True, blank=True)
    longitude = models.FloatField(null=True, blank=True)
    accuracy_m = models.FloatField(null=True, blank=True)
    source = models.CharField(max_length=10, choices=Source.choices, default=Source.MANUAL)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.sales_rep} @ {self.created_at:%Y-%m-%d %H:%M}"
