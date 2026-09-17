from rest_framework import viewsets
from apps.accounts.permissions import RoleScopedQuerysetMixin
from .models import InventoryItem
from .serializers import InventoryItemSerializer


class InventoryItemViewSet(RoleScopedQuerysetMixin, viewsets.ModelViewSet):
    queryset = InventoryItem.objects.select_related("ba", "ba__region", "product").all()
    serializer_class = InventoryItemSerializer
    filterset_fields = ["ba", "product", "ba__region"]
