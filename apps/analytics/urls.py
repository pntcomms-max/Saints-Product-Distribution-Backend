from django.urls import path
from .views import (
    DemandForecastView,
    DashboardOverviewView,
    LiveMapView,
    ManufacturerDashboardView,
)

urlpatterns = [
    path("demand-forecast/", DemandForecastView.as_view(), name="demand-forecast"),
    path("dashboard/overview/", DashboardOverviewView.as_view(), name="dashboard-overview"),
    path("dashboard/", DashboardOverviewView.as_view(), name="analytics-dashboard"), # Alias for legacy dashboard call
    path("live-map/", LiveMapView.as_view(), name="live-map"),
    path("manufacturer/<int:manufacturer_id>/dashboard/", ManufacturerDashboardView.as_view(), name="manufacturer-dashboard"),
]