from django.contrib.auth.views import redirect_to_login
from django.shortcuts import redirect
from django.utils import timezone

from authentication.services.dashboard_access import has_valid_dashboard_access


class DashboardAccessMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        path = request.path

        if path.startswith('/dashboard/'):
            user = request.user

            if not user.is_authenticated:
                return redirect_to_login(path, '/accounts/login/')

            # Strict per-user 7-day access check
            if not has_valid_dashboard_access(user):
                return redirect('authentication:video_verify')

        return self.get_response(request)