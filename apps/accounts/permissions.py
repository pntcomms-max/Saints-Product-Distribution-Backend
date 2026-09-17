from rest_framework.permissions import BasePermission


class IsManager(BasePermission):
    def has_permission(self, request, view):
        return bool(request.user and request.user.role in ("MANAGER", "ADMIN"))


class IsSupervisorOrAbove(BasePermission):
    def has_permission(self, request, view):
        return bool(request.user and request.user.role in ("SUPERVISOR", "MANAGER", "ADMIN"))


class RoleScopedQuerysetMixin:
    """
    Mixin for ViewSets whose queryset has a `.ba` (or direct owner) field
    that should be scoped by who's asking:
      - BA: only their own rows
      - Supervisor: rows for BAs on their team
      - Manager/Admin: everything
    Set `ba_field` on the view if the FK isn't literally called `ba`.
    """
    ba_field = "ba"

    def get_queryset(self):
        qs = super().get_queryset()
        user = self.request.user
        if user.role == "BA":
            return qs.filter(**{self.ba_field: user})
        if user.role == "SUPERVISOR":
            return qs.filter(**{f"{self.ba_field}__supervisor": user})
        return qs  # MANAGER / ADMIN see everything
