from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.exceptions import ValidationError
from rest_framework.parsers import MultiPartParser
from .models import User, DeviceToken
from .serializers import UserSerializer, UserCreateSerializer, SetPasswordSerializer, DeviceTokenSerializer
from .permissions import IsSupervisorOrAbove
from .bulk_import import import_users_from_csv


class UserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.select_related("region", "supervisor").all()
    filterset_fields = ["role", "region", "supervisor"]

    def get_serializer_class(self):
        return UserCreateSerializer if self.action == "create" else UserSerializer

    def get_permissions(self):
        # This is the single source of truth for permissions on this
        # ViewSet — permission_classes set on an individual @action
        # decorator below does NOT take effect, because overriding
        # get_permissions() like this bypasses that mechanism entirely.
        # (This is exactly the bug that let a BA call bulk_import/ once —
        # keep every action's rule listed here, not on the decorator.)
        if self.action in ("create", "update", "partial_update", "destroy", "bulk_import"):
            return [IsSupervisorOrAbove()]
        return [permissions.IsAuthenticated()]

    def get_queryset(self):
        qs = super().get_queryset()
        user = self.request.user
        if user.role == "SUPERVISOR":
            # a supervisor manages their own team + sees their own record
            return qs.filter(models_q_supervisor_or_self(user))
        if user.role == "BA":
            # a BA should never enumerate the org's user list — only themselves
            return qs.filter(id=user.id)
        return qs  # MANAGER / ADMIN see everyone

    @action(detail=False, methods=["get"])
    def me(self, request):
        return Response(UserSerializer(request.user).data)

    @action(detail=False, methods=["post"])
    def set_password(self, request):
        """
        Any logged-in user changes their own password with this — used
        both for a normal "change my password" screen and for clearing
        must_change_password after a bulk-import temp password.
        """
        serializer = SetPasswordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        request.user.set_password(serializer.validated_data["new_password"])
        request.user.must_change_password = False
        request.user.save(update_fields=["password", "must_change_password"])
        return Response({"detail": "Password updated."})

    @action(detail=False, methods=["post"], parser_classes=[MultiPartParser])
    def bulk_import(self, request):
        """
        POST a multipart form with a `file` field (CSV). See
        apps/accounts/bulk_import.py for the expected columns.
        Returns temp passwords for each created user — display/export
        these immediately, they are never stored or retrievable again.
        """
        upload = request.FILES.get("file")
        if not upload:
            raise ValidationError({"file": "A CSV file is required (multipart field name: 'file')."})
        result = import_users_from_csv(upload)
        code = status.HTTP_201_CREATED if result.created else status.HTTP_400_BAD_REQUEST
        return Response(result.summary, status=code)


def models_q_supervisor_or_self(user):
    from django.db.models import Q
    return Q(supervisor=user) | Q(id=user.id)


class DeviceTokenViewSet(viewsets.ModelViewSet):
    """
    Register/unregister the current device's FCM token. Every user
    (any role) can register their own device — supervisors and managers
    are the ones who'll actually receive alert pushes, but registering
    is universal so the same code path works if BAs ever get push too.
    """
    serializer_class = DeviceTokenSerializer

    def get_queryset(self):
        return DeviceToken.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)
