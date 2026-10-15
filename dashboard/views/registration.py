import logging

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import render, redirect
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from django.views.generic import View

from dashboard.forms import ContentManagerRegistrationForm
from dashboard.models import (
    RegistrationRequest,
    RegistrationLog,
)
from dashboard.services import (
    RegistrationService,
    DuplicateFaceError,
)
from dashboard.mixins import DashboardRequestAccessMixin
from accounts.forms import DashboardRequestForm

logger = logging.getLogger(__name__)


class RequestAccessView(DashboardRequestAccessMixin, View):
    template_name = 'dashboard/request_access.html'

    def get(self, request):
        self.log_page_opened()

        form = DashboardRequestForm(
            initial={
                'full_name': (
                    request.user.get_full_name()
                    or request.user.username
                ),
                'email': request.user.email,
            }
        )

        return render(
            request,
            self.template_name,
            {'form': form},
        )

    def post(self, request):
        form = DashboardRequestForm(
            request.POST,
            user=request.user,
        )

        if form.is_valid():
            reg_request = RegistrationRequest.objects.create(
                full_name=form.cleaned_data['full_name'],
                email=form.cleaned_data['email'],
                message=form.cleaned_data.get(
                    'message',
                    '',
                ),
            )

            user = request.user

            user.dashboard_request_used = True
            user.dashboard_request_used_at = timezone.now()
            user.dashboard_request_status = 'pending'

            user.save(
                update_fields=[
                    'dashboard_request_used',
                    'dashboard_request_used_at',
                    'dashboard_request_status',
                ]
            )

            service = RegistrationService()

            service.log_access_request(
                reg_request
            )

            RegistrationLog.objects.create(
                request=reg_request,
                event=RegistrationLog.Event.DASHBOARD_REQUEST_SUBMITTED,
                detail=(
                    f"User {user.username} "
                    f"submitted dashboard request"
                ),
                ip_address=self._get_client_ip(),
                user_agent=request.META.get(
                    'HTTP_USER_AGENT',
                    '',
                )[:500],
            )

            messages.success(
                request,
                _(
                    'Your dashboard access request '
                    'has been submitted for review.'
                ),
            )

            return redirect(
                'dashboard:request_success'
            )

        return render(
            request,
            self.template_name,
            {'form': form},
        )

    def _get_client_ip(self):
        xff = self.request.META.get(
            'HTTP_X_FORWARDED_FOR'
        )

        if xff:
            return xff.split(',')[0].strip()

        return self.request.META.get(
            'REMOTE_ADDR',
            '0.0.0.0',
        )


class RequestSuccessView(View):
    template_name = 'dashboard/request_success.html'

    def get(self, request):
        return render(
            request,
            self.template_name,
        )


class HiddenRegisterView(LoginRequiredMixin, View):
    """
    Hidden dashboard registration.

    The username is always taken from the
    authenticated existing user.
    """

    template_name = 'dashboard/register.html'

    def _get_request_or_404(self, token):
        request_obj = (
            RegistrationRequest.objects
            .filter(token=token)
            .first()
        )

        if request_obj is None:
            RegistrationLog.objects.create(
                request=None,
                event=RegistrationLog.Event.TOKEN_INVALID,
                detail=f"Unknown token: {token}",
            )

            return None

        if not request_obj.is_token_valid():

            event = (
                RegistrationLog.Event.TOKEN_REUSED
                if request_obj.is_used
                else RegistrationLog.Event.TOKEN_EXPIRED
            )

            RegistrationLog.objects.create(
                request=request_obj,
                event=event,
            )

            return None

        return request_obj

    def get(self, request, token):
        request_obj = self._get_request_or_404(
            token
        )

        if not request_obj:
            return render(
                request,
                '404.html',
                status=404,
            )

        if request.user.email != request_obj.email:
            return render(
                request,
                '404.html',
                status=404,
            )

        RegistrationLog.objects.create(
            request=request_obj,
            event=RegistrationLog.Event.TOKEN_OPENED,
        )

        form = ContentManagerRegistrationForm(
            initial={
                'email': request_obj.email,
            }
        )

        return render(
            request,
            self.template_name,
            {
                'form': form,
                'token': token,
                'full_name': request_obj.full_name,
            },
        )

    def post(self, request, token):
        request_obj = self._get_request_or_404(
            token
        )

        if not request_obj:
            return render(
                request,
                '404.html',
                status=404,
            )

        if request.user.email != request_obj.email:
            return render(
                request,
                '404.html',
                status=404,
            )

        form = ContentManagerRegistrationForm(
            request.POST
        )

        if form.is_valid():

            # Existing authenticated account.
            username = request.user.username

            photo_data = request.POST.get(
                'photo_data'
            )

            video_data = request.POST.get(
                'video_data'
            )

            logger.info(
                "Photo data length: %s",
                len(photo_data)
                if photo_data
                else 0,
            )

            logger.info(
                "Video data length: %s",
                len(video_data)
                if video_data
                else 0,
            )

            if not photo_data or not video_data:
                form.add_error(
                    None,
                    _('Photo and video are required.'),
                )

                return render(
                    request,
                    self.template_name,
                    {
                        'form': form,
                        'token': token,
                        'full_name': request_obj.full_name,
                    },
                )

            max_video_size = (
                50 * 1024 * 1024
            )

            if len(video_data) > max_video_size:
                form.add_error(
                    None,
                    _('Video file is too large.'),
                )

                return render(
                    request,
                    self.template_name,
                    {
                        'form': form,
                        'token': token,
                        'full_name': request_obj.full_name,
                    },
                )

            service = RegistrationService()

            try:
                registration = (
                    service.create_registration(
                        request_obj=request_obj,
                        username=username,
                        password=form.cleaned_data[
                            'password1'
                        ],
                        phone=form.cleaned_data[
                            'phone'
                        ],
                        photo_data=photo_data,
                        video_data=video_data,
                    )
                )

                messages.success(
                    request,
                    _(
                        'Registration submitted '
                        'for verification.'
                    ),
                )

                return redirect(
                    'dashboard:register_success'
                )

            except DuplicateFaceError:
                # The submitted face belongs to
                # another existing account.
                return render(
                    request,
                    '404.html',
                    status=404,
                )

            except Exception as e:
                logger.exception(
                    "Registration creation failed."
                )

                form.add_error(
                    None,
                    str(e),
                )

        return render(
            request,
            self.template_name,
            {
                'form': form,
                'token': token,
                'full_name': request_obj.full_name,
            },
        )


class RegisterSuccessView(View):
    template_name = 'dashboard/register_success.html'

    def get(self, request):
        return render(
            request,
            self.template_name,
        )