from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    """
    A single user model for every role in the network. Role drives what
    a person can see in both the API (see permissions.py) and the app.
    """

    class Role(models.TextChoices):
        BA = "BA", "Brand Ambassador"
        SUPERVISOR = "SUPERVISOR", "Regional Supervisor"
        MANAGER = "MANAGER", "Management"
        ADMIN = "ADMIN", "Admin"

    role = models.CharField(max_length=20, choices=Role.choices, default=Role.BA)
    phone = models.CharField(max_length=20, blank=True)
    region = models.ForeignKey(
        "catalog.Region", null=True, blank=True,
        on_delete=models.SET_NULL, related_name="users",
    )
    # Only meaningful when role == BA: which supervisor manages them.
    supervisor = models.ForeignKey(
        "self", null=True, blank=True,
        on_delete=models.SET_NULL, related_name="team_members",
        limit_choices_to={"role": Role.SUPERVISOR},
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
