from rest_framework import viewsets
from apps.accounts.permissions import RoleScopedQuerysetMixin
from .models import CheckIn
from .serializers import CheckInSerializer


class CheckInViewSet(RoleScopedQuerysetMixin, viewsets.ModelViewSet):
    queryset = CheckIn.objects.select_related("ba", "region").all()
    serializer_class = CheckInSerializer
    filterset_fields = ["ba", "region", "source"]
