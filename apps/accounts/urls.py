from rest_framework.routers import DefaultRouter
from .views import UserViewSet, DeviceTokenViewSet

router = DefaultRouter()
router.register("users", UserViewSet, basename="user")
router.register("device-tokens", DeviceTokenViewSet, basename="device-token")

urlpatterns = router.urls