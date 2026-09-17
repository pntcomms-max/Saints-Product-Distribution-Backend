from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User


@admin.register(User)
class CustomUserAdmin(UserAdmin):
    list_display = ["username", "get_full_name", "role", "region", "supervisor", "is_active"]
    list_filter = ["role", "region"]
    fieldsets = UserAdmin.fieldsets + (
        ("Network role", {"fields": ("role", "phone", "region", "supervisor", "is_active_field_agent", "must_change_password")}),
    )
