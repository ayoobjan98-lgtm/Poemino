# accounts/views.py

import secrets
import base64
import uuid
import logging
import cv2
import numpy as np

from django.http import JsonResponse
from django.contrib import messages
from django.contrib.auth import login, update_session_auth_hash
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.views import LoginView as AuthLoginView, LogoutView as AuthLogoutView
from django.core.files.base import ContentFile
from django.db import transaction
from django.shortcuts import redirect, render
from django.urls import reverse_lazy
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from django.views.generic import CreateView, TemplateView, UpdateView, View
from django.contrib.auth.mixins import LoginRequiredMixin

from api.serializers import APITokenSerializer
from api.services.token_service import create_api_token


from authentication.models import FaceReference
from authentication.services.face_detection import detect_faces
from authentication.services.face_verification import extract_face_feature, embed_to_json
from authentication.services.dashboard_access import has_valid_dashboard_access

from .forms import (
    CustomLoginForm,
    CustomUserCreationForm,
    UserProfileForm,
    DashboardRequestForm,
    PasswordResetRequestForm,
    SetNewPasswordForm,
)
from .models import CustomUser, PasswordResetToken
from dashboard.models import RegistrationRequest, RegistrationLog
from dashboard.services import RegistrationService
from dashboard.mixins import DashboardRequestAccessMixin

logger = logging.getLogger(__name__)


class LoginView(AuthLoginView):
    authentication_form = CustomLoginForm
    template_name = "accounts/login.html"

    def form_valid(self, form):
        user = form.get_user()
        login(self.request, user)

        # If the user does NOT have dashboard permission, go to normal home.
        if not getattr(user, 'is_page_permitted', False):
            return redirect(self.get_success_url())

        # User HAS dashboard permission. Check the DashboardAccessRecord FIRST.
        if has_valid_dashboard_access(user):
            return redirect('dashboard:index')

        # No valid 7-day access record → start identity verification.
        return redirect('authentication:video_verify')

    def get_success_url(self):
        return reverse_lazy('MakePoem:home')


class SignUpView(CreateView):
    form_class = CustomUserCreationForm
    template_name = 'accounts/signup.html'
    success_url = reverse_lazy('MakePoem:home')

    @transaction.atomic
    def form_valid(self, form):
        user = form.save(commit=False)
        user.save()
        

        login(self.request, user)
        return redirect(self.success_url)


class LogoutView(LoginRequiredMixin, AuthLogoutView):
    template_name = "accounts/logout.html"
    next_page = reverse_lazy('MakePoem:home')
    http_method_names = ["get", "post", "options"]

    def get(self, request, *args, **kwargs):
        context = self.get_context_data(**kwargs)
        return self.render_to_response(context)


class ProfileView(LoginRequiredMixin, UpdateView):
    model = CustomUser
    form_class = UserProfileForm
    template_name = 'accounts/profile.html'
    success_url = reverse_lazy('profile')

    def get_object(self, queryset=None):
        return self.request.user


class DashboardRequestView(DashboardRequestAccessMixin, View):
    template_name = 'accounts/dashboard_request.html'

    def get(self, request):
        self.log_page_opened()
        form = DashboardRequestForm(
            initial={
                'full_name': request.user.get_full_name() or request.user.username,
                'email': request.user.email,
            }
        )
        return render(request, self.template_name, {'form': form})

    def post(self, request):
        form = DashboardRequestForm(request.POST, user=request.user)
        if form.is_valid():
            reg_request = RegistrationRequest.objects.create(
                full_name=form.cleaned_data['full_name'],
                email=form.cleaned_data['email'],
                message=form.cleaned_data.get('message', ''),
            )
            user = request.user
            user.dashboard_request_used = True
            user.dashboard_request_used_at = timezone.now()
            user.dashboard_request_status = 'pending'
            user.save(update_fields=[
                'dashboard_request_used',
                'dashboard_request_used_at',
                'dashboard_request_status',
            ])
            service = RegistrationService()
            service.log_access_request(reg_request)
            RegistrationLog.objects.create(
                request=reg_request,
                event=RegistrationLog.Event.DASHBOARD_REQUEST_SUBMITTED,
                detail=f"User {user.username} submitted dashboard request",
                ip_address=self._get_client_ip(),
                user_agent=request.META.get('HTTP_USER_AGENT', '')[:500],
            )
            messages.success(request, _('Your dashboard access request has been submitted for review.'))
            return redirect('dashboard:request_success')
        return render(request, self.template_name, {'form': form})

    def _get_client_ip(self):
        xff = self.request.META.get('HTTP_X_FORWARDED_FOR')
        if xff:
            return xff.split(',')[0].strip()
        return self.request.META.get('REMOTE_ADDR', '0.0.0.0')


class ForgotPasswordView(View):
    template_name = 'accounts/forgot_password.html'

    def get(self, request):
        form = PasswordResetRequestForm()
        return render(request, self.template_name, {'form': form})

    def post(self, request):
        form = PasswordResetRequestForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data['email']
            user = CustomUser.objects.get(email=email)
            PasswordResetToken.objects.filter(user=user, is_used=False).update(is_used=True)
            token = secrets.token_urlsafe(32)
            PasswordResetToken.objects.create(user=user, token=token)
            from .email_service import send_password_reset_email
            send_password_reset_email(user, token)
            messages.success(request, _('Password reset instructions have been sent to your email.'))
            return redirect('password_reset_sent')
        return render(request, self.template_name, {'form': form})


class PasswordResetSentView(TemplateView):
    template_name = 'accounts/password_reset_sent.html'


class ResetPasswordView(View):
    template_name = 'accounts/reset_password.html'

    def get(self, request, token):
        reset_token = PasswordResetToken.objects.filter(token=token, is_used=False).first()
        if not reset_token or not reset_token.is_valid():
            messages.error(request, _('Invalid or expired token.'))
            return render(request, '404.html', status=404)
        form = SetNewPasswordForm()
        return render(request, self.template_name, {'form': form, 'token': token})

    def post(self, request, token):
        reset_token = PasswordResetToken.objects.filter(token=token, is_used=False).first()
        if not reset_token or not reset_token.is_valid():
            messages.error(request, _('Invalid or expired token.'))
            return render(request, '404.html', status=404)
        form = SetNewPasswordForm(request.POST)
        if form.is_valid():
            user = reset_token.user
            user.set_password(form.cleaned_data['new_password1'])
            user.save()
            reset_token.is_used = True
            reset_token.save()
            update_session_auth_hash(request, user)
            messages.success(request, _('Your password has been reset successfully.'))
            return redirect('password_reset_complete')
        return render(request, self.template_name, {'form': form, 'token': token})


class PasswordResetCompleteView(TemplateView):
    template_name = 'accounts/password_reset_complete.html'


# Old LoginVerificationView kept as a redirect to the new flow for compatibility
class LoginVerificationView(LoginRequiredMixin, View):
    def get(self, request):
        return redirect('authentication:video_verify')
