from django.contrib import admin
from django.urls import path, include
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

admin.site.site_header = "Saints Distribution Admin"
admin.site.site_title = "Saints Distribution Portal"
admin.site.index_title = "Welcome to Saints Distribution Management System"

urlpatterns = [
    path("admin/", admin.site.urls),

    path("api/auth/token/", TokenObtainPairView.as_view(), name="token_obtain_pair"),
    path("api/auth/token/refresh/", TokenRefreshView.as_view(), name="token_refresh"),

    path("api/accounts/", include("apps.accounts.urls")),
    path("api/catalog/", include("apps.catalog.urls")),
    path("api/inventory/", include("apps.inventory.urls")),
    path("api/sales/", include("apps.sales.urls")),
    path("api/tracking/", include("apps.tracking.urls")),
    path("api/analytics/", include("apps.analytics.urls")),
    path("api/", include("apps.alerts.urls")),
]
