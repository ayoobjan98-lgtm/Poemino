from django.contrib.admin import AdminSite
from django.shortcuts import render
from django.utils.translation import gettext_lazy as _


class CustomAdminSite(AdminSite):
    """
    An AdminSite that returns a 404 page for every request—including
    /admin/login/—unless the user is authenticated, staff, and superuser.
    """

    def admin_view(self, view, cacheable=False):
        inner = super().admin_view(view, cacheable=cacheable)

        def wrapper(request, *args, **kwargs):
            # Must be logged‑in staff + superuser
            if not (
                request.user.is_authenticated
                and request.user.is_staff
                and request.user.is_superuser
            ):
                return render(request, '404.html', status=404)
            return inner(request, *args, **kwargs)

        return wrapper


# Instantiate the custom admin site – this is what urlpatterns must use
custom_admin_site = CustomAdminSite(name='custom_admin')