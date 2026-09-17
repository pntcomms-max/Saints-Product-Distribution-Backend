from django.contrib import admin
from .models import CheckIn


@admin.register(CheckIn)
class CheckInAdmin(admin.ModelAdmin):
    list_display = ["ba", "region", "source", "created_at"]
    list_filter = ["region", "source"]
