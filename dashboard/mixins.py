from django.contrib.auth.mixins import UserPassesTestMixin
from django.contrib.auth.views import redirect_to_login
from django.shortcuts import render, redirect
from django.utils.translation import gettext_lazy as _

from authentication.services.dashboard_access import has_valid_dashboard_access
from dashboard.models import RegistrationLog


class ContentManagerAccessMixin(UserPassesTestMixin):
    """
    Dashboard access is granted only when the current user has a valid
    DashboardAccessRecord. Strictly per `request.user`.
    """
    raise_exception = False

    def test_func(self):
        # The actual access check happens in dispatch. This just ensures
        # that the user is authenticated before continuing.
        return self.request.user.is_authenticated

    def handle_no_permission(self):
        return render(self.request, '404.html', status=404)

    def dispatch(self, request, *args, **kwargs):
        user = request.user
        print("DASHBOARD DISPATCH user=", user.username,
            "authenticated=", user.is_authenticated,
            "is_page_permitted=", getattr(user, 'is_page_permitted', None))

        if not user.is_authenticated:
            print("  → redirecting to login")
            return redirect_to_login(
                request.get_full_path(),
                self.get_login_url(),
                self.get_redirect_field_name(),
            )

        valid = has_valid_dashboard_access(user)
        print("  → has_valid_dashboard_access =", valid)
        if not valid:
            print("  → redirecting to authentication:video_verify")
            return redirect('authentication:video_verify')

        return super().dispatch(request, *args, **kwargs)

class DashboardRequestAccessMixin(UserPassesTestMixin):
    """
    Controls access to the one-time dashboard request page.

    The administrator grants `can_request_dashboard` and the page is one-time
    (`dashboard_request_used` must be False).
    """
    raise_exception = False

    def test_func(self):
        user = self.request.user
        return (
            user.is_authenticated
            and user.is_active
            and getattr(user, 'can_request_dashboard', False)
            and not getattr(user, 'dashboard_request_used', False)
        )

    def handle_no_permission(self):
        user = self.request.user
        RegistrationLog.objects.create(
            request=None,
            event=RegistrationLog.Event.DASHBOARD_REQUEST_BLOCKED,
            detail=f"User {user.username} blocked from dashboard request page",
            ip_address=self._get_client_ip(),
            user_agent=self.request.META.get('HTTP_USER_AGENT', '')[:500],
        )
        return render(self.request, '404.html', status=404)

    def log_page_opened(self):
        user = self.request.user
        RegistrationLog.objects.create(
            request=None,
            event=RegistrationLog.Event.DASHBOARD_REQUEST_OPENED,
            detail=f"User {user.username} opened dashboard request page",
            ip_address=self._get_client_ip(),
            user_agent=self.request.META.get('HTTP_USER_AGENT', '')[:500],
        )

    def _get_client_ip(self):
        xff = self.request.META.get('HTTP_X_FORWARDED_FOR')
        if xff:
            return xff.split(',')[0].strip()
        return self.request.META.get('REMOTE_ADDR', '0.0.0.0')


class DashboardSuccessMessageMixin:
    """Attaches a success message to the request so templates can display it."""
    success_message = ''

    def form_valid(self, form):
        response = super().form_valid(form)
        if self.success_message:
            from django.contrib import messages
            messages.success(self.request, self.success_message)
        return response


class DashboardPaginationMixin:
    """Standard pagination for dashboard list views."""
    paginate_by = 20
    paginate_orphans = 2