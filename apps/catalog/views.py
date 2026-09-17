from rest_framework import viewsets, permissions
from .models import Region, Manufacturer, Brand, Product
from .serializers import RegionSerializer, ManufacturerSerializer, BrandSerializer, ProductSerializer
from apps.accounts.permissions import IsSupervisorOrAbove


class ReadForAllWriteForSupervisorsMixin:
    def get_permissions(self):
        if self.action in ("create", "update", "partial_update", "destroy"):
            return [IsSupervisorOrAbove()]
        return [permissions.IsAuthenticated()]


class RegionViewSet(ReadForAllWriteForSupervisorsMixin, viewsets.ModelViewSet):
    queryset = Region.objects.all()
    serializer_class = RegionSerializer


class ManufacturerViewSet(ReadForAllWriteForSupervisorsMixin, viewsets.ModelViewSet):
    queryset = Manufacturer.objects.all()
    serializer_class = ManufacturerSerializer


class BrandViewSet(ReadForAllWriteForSupervisorsMixin, viewsets.ModelViewSet):
    queryset = Brand.objects.select_related("manufacturer").all()
    serializer_class = BrandSerializer
    filterset_fields = ["manufacturer"]


class ProductViewSet(ReadForAllWriteForSupervisorsMixin, viewsets.ModelViewSet):
    queryset = Product.objects.select_related("brand", "brand__manufacturer").filter(is_active=True)
    serializer_class = ProductSerializer
    filterset_fields = ["brand", "brand__manufacturer"]
