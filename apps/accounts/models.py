from django.contrib.auth.models import AbstractUser
from django.db import models
from apps.catalog.models import Product


class UserRole(models.TextChoices):
    ADMIN = 'ADMIN', 'Admin'
    MANAGER = 'MANAGER', 'Manager'
    SUPERVISOR = 'SUPERVISOR', 'Supervisor'
    SALES_REP = 'SALES_REP', 'Sales Representative'
    DRIVER = 'DRIVER', 'Delivery Driver'

class User(AbstractUser):
    role = models.CharField(max_length=20, choices=UserRole.choices, default=UserRole.SALES_REP)
    phone_number = models.CharField(max_length=20, unique=True, null=True, blank=True)
    assigned_territory = models.CharField(max_length=255, blank=True)
    daily_sales_target = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    region = models.ForeignKey(
            "apps_catalog.Region", null=True, blank=True,
            on_delete=models.SET_NULL, related_name="users",
        )
    # Only meaningful when role == SALES_REP: which supervisor manages them.

       
    supervisor = models.ForeignKey(
        "self", null=True, blank=True,
        on_delete=models.SET_NULL, related_name="team_members",
        limit_choices_to={"role": "SUPERVISOR"},
    )
    is_active_field_agent = models.BooleanField(default=True)
    # Set True for anyone created via bulk import — forces a
    # password reset on first real login instead of shipping
    # temp passwords into permanent use.
    must_change_password = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.get_full_name() or self.username} ({self.role})"


class DeviceToken(models.Model):
    """
    FCM registration token for a user's device, so we know where to send
    push notifications (alerts, for supervisors/managers). A user can
    have more than one (phone + tablet, or after a reinstall).
    """
    class Platform(models.TextChoices):
        ANDROID = "ANDROID", "Android"
        IOS = "IOS", "iOS"

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="device_tokens")
    token = models.CharField(max_length=255, unique=True)
    platform = models.CharField(max_length=10, choices=Platform.choices, default=Platform.ANDROID)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user} — {self.platform}"

    class CustomerStore(models.Model):
        """Retailers, wholesalers, Spaza shops visited by Sales Reps"""
        store_name = models.CharField(max_length=255)
        owner_name = models.CharField(max_length=255)
        phone = models.CharField(max_length=30)
        address = models.TextField()
        latitude = models.FloatField(null=True, blank=True)
        longitude = models.FloatField(null=True, blank=True)
        assigned_rep = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='customer_stores')
        credit_limit = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
        current_balance = models.DecimalField(max_digits=10, decimal_places=2, default=0.00) # Unpaid debt
        created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.store_name} ({self.owner_name})"
