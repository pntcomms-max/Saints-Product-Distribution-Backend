from rest_framework.routers import DefaultRouter
from .views import CheckInViewSet

router = DefaultRouter()
router.register("checkins", CheckInViewSet, basename="checkin")
urlpatterns = router.urls
