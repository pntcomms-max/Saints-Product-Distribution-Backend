from django.db.models import Q
from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.exceptions import ValidationError
from rest_framework.parsers import MultiPartParser
from rest_framework.permissions import IsAuthenticated

from .models import User, DeviceToken
from .serializers import (
    UserSerializer,
    UserCreateSerializer,
    SetPasswordSerializer,
    DeviceTokenSerializer,
)
from .permissions import IsManager, IsSupervisorOrAbove
from .bulk_import import import_users_from_csv


def models_q_supervisor_or_self(user):
    """Helper to retrieve team members managed by a supervisor or the supervisor's own record."""
    return Q(supervisor=user) | Q(id=user.id)


class UserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.select_related("region", "supervisor").all()
    filterset_fields = ["role", "region", "supervisor"]

    def get_serializer_class(self):
        if self.action == "create":
            return UserCreateSerializer
        return UserSerializer

    def get_permissions(self):
        # Single source of truth for viewset permissions
        if self.action in ("create", "update", "partial_update", "destroy", "bulk_import"):
            return [IsSupervisorOrAbove()]
        return [IsAuthenticated()]

    def get_queryset(self):
        qs = super().get_queryset()
        user = self.request.user

        if not user or not user.is_authenticated:
            return qs.none()

        if user.role == "SUPERVISOR":
            return qs.filter(models_q_supervisor_or_self(user))
        
        if user.role in ("BA", "SALES_REP"):
            return qs.filter(id=user.id)

        return qs  # MANAGER / ADMIN see all users

    @action(detail=False, methods=["get"])
    def me(self, request):
        return Response(UserSerializer(request.user).data)

    @action(detail=False, methods=["post"])
    def set_password(self, request):
        """
        Allows authenticated users to update their own password.
        Used for regular password resets and initial bulk-import temporary password updates.
        """
        serializer = SetPasswordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        request.user.set_password(serializer.validated_data["new_password"])
        request.user.must_change_password = False
        request.user.save(update_fields=["password", "must_change_password"])
        return Response({"detail": "Password updated successfully."})

    @action(detail=False, methods=["post"], parser_classes=[MultiPartParser])
    def bulk_import(self, request):
        """
        Accepts multipart form CSV uploads to provision users in bulk.
        """
        upload = request.FILES.get("file")
        if not upload:
            raise ValidationError({"file": "A CSV file is required (multipart field name: 'file')."})
        
        result = import_users_from_csv(upload)
        code = status.HTTP_201_CREATED if result.created else status.HTTP_400_BAD_REQUEST
        return Response(result.summary, status=code)


class DeviceTokenViewSet(viewsets.ModelViewSet):
    """
    Registers and unregisters push notification FCM tokens for the current user.
    """
    serializer_class = DeviceTokenSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return DeviceToken.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)
