from rest_framework.permissions import BasePermission

class RoleScopedQuerysetMixin:
    """
    Mixin to filter querysets based on user roles:
    - Field Reps/Sales Reps see only their assigned records.
    - Supervisors see records within their assigned region/territory.
    - Managers/Admins see all records nationwide.
    """
    def get_queryset(self):
        queryset = super().get_queryset()
        user = self.request.user

        if not user or not user.is_authenticated:
            return queryset.none()

        # Admins and Managers see everything
        if user.role in ["ADMIN", "SUPERADMIN", "MANAGER"]:
            return queryset

        # Supervisors see everything in their region
        if user.role == "SUPERVISOR":
            if hasattr(queryset.model, "region"):
                return queryset.filter(region=user.region)
            return queryset

        # Field/Sales Reps see only their assigned items/sales
        if hasattr(queryset.model, "sales_rep"):
            return queryset.filter(sales_rep=user)
        if hasattr(queryset.model, "assigned_to"):
            return queryset.filter(assigned_to=user)
        if hasattr(queryset.model, "user"):
            return queryset.filter(user=user)

        return queryset


class IsManager(BasePermission):
    def has_permission(self, request, view):
        return (
            request.user 
            and request.user.is_authenticated 
            and getattr(request.user, "role", None) in ["MANAGER", "ADMIN", "SUPERADMIN"]
        )


class IsSupervisorOrAbove(BasePermission):
    def has_permission(self, request, view):
        return (
            request.user 
            and request.user.is_authenticated 
            and getattr(request.user, "role", None) in ["SUPERVISOR", "MANAGER", "ADMIN", "SUPERADMIN"]
        )