from django.urls import path
from rest_framework.routers import DefaultRouter
from .views import InventoryItemViewSet, AcceptVanStockTransferView

router = DefaultRouter()
router.register("items", InventoryItemViewSet, basename="inventory-item")

urlpatterns = [
    path('transfers/<int:transfer_id>/accept/', AcceptVanStockTransferView.as_view(), name='accept-van-transfer'),
] + router.urls