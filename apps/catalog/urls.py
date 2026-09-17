from rest_framework.routers import DefaultRouter
from .views import RegionViewSet, ManufacturerViewSet, BrandViewSet, ProductViewSet

router = DefaultRouter()
router.register("regions", RegionViewSet, basename="region")
router.register("manufacturers", ManufacturerViewSet, basename="manufacturer")
router.register("brands", BrandViewSet, basename="brand")
router.register("products", ProductViewSet, basename="product")
urlpatterns = router.urls
