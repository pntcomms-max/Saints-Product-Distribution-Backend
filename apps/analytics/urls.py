from django.urls import path
from .views import DemandForecastView, DashboardOverviewView, LiveMapView

urlpatterns = [
    path("demand-forecast/", DemandForecastView.as_view(), name="demand-forecast"),
    path("dashboard/overview/", DashboardOverviewView.as_view(), name="dashboard-overview"),
    path("live-map/", LiveMapView.as_view(), name="live-map"),
]
