# api/permissions.py

from rest_framework.permissions import BasePermission


class DjangoModelPermissions(BasePermission):
    """
    استفاده از Permissionهای داخلی Django برای API.
    """

    perms_map = {
        "GET": ["view"],
        "POST": ["add"],
        "PUT": ["change"],
        "PATCH": ["change"],
        "DELETE": ["delete"],
    }

    def has_permission(self, request, view):
        user = request.user

        if not user or not user.is_authenticated:
            return False

        model = view.get_queryset().model

        app_label = model._meta.app_label
        model_name = model._meta.model_name

        required_perms = self.perms_map.get(request.method, [])

        return all(
            user.has_perm(
                f"{app_label}.{perm}_{model_name}"
            )
            for perm in required_perms
        )

class IsStaffToken(BasePermission):

    def has_permission(self, request, view):

        if not request.user.is_authenticated:
            return False

        return (
            request.auth
            and request.auth.get("api_role") == "staff"
            and request.user.is_staff
        )

    