from django.utils import timezone
from rest_framework import viewsets, mixins
from rest_framework.decorators import action
from rest_framework.response import Response
from apps.accounts.permissions import IsSupervisorOrAbove
from .models import Alert
from .serializers import AlertSerializer


class AlertViewSet(mixins.ListModelMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet):
    """Read-only + a `resolve` action — alerts are created by the
    detection job (check_alerts management command), never directly by the API."""
    serializer_class = AlertSerializer
    permission_classes = [IsSupervisorOrAbove]
    filterset_fields = ["kind", "ba"]

    def get_queryset(self):
        qs = Alert.objects.select_related("ba", "ba__region", "product").filter(resolved_at__isnull=True)
        user = self.request.user
        if user.role == "SUPERVISOR":
            qs = qs.filter(ba__supervisor=user)
        return qs

    @action(detail=True, methods=["post"])
    def resolve(self, request, pk=None):
        alert = self.get_object()
        alert.resolved_at = timezone.now()
        alert.save(update_fields=["resolved_at"])
        return Response(AlertSerializer(alert).data)
