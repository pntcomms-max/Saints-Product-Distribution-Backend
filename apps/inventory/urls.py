from rest_framework.routers import DefaultRouter
from .views import InventoryItemViewSet

router = DefaultRouter()
router.register("items", InventoryItemViewSet, basename="inventory-item")
urlpatterns = router.urls
