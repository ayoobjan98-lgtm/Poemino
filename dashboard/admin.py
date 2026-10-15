import logging

from django.contrib import admin
from django.contrib import messages
from django.shortcuts import redirect
from django.urls import path, reverse
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _


from config.admin_site import custom_admin_site
from dashboard.models import (
    ContentManageablePoem,
    ContentActivityLog,
    RegistrationRequest,
    ContentManagerRegistration,
    RegistrationLog,
    LoginAuditLog,
)
from dashboard.services import RegistrationService
from dashboard.email_service import (
    send_registration_link_email,
    send_request_rejected_email,
    send_account_approved_email,
    send_registration_rejected_email,
)

logger = logging.getLogger(__name__)


def _get_user_by_email(email):
    from django.contrib.auth import get_user_model
    User = get_user_model()
    return User.objects.filter(email=email).first()


class RegistrationLogInline(admin.TabularInline):
    model = RegistrationLog
    extra = 0
    readonly_fields = ('event', 'timestamp', 'detail', 'ip_address', 'user_agent')
    can_delete = False
    ordering = ('-timestamp',)
    max_num = 0


# ---------- Register all models with the custom admin site ----------

@admin.register(ContentManageablePoem, site=custom_admin_site)
class ContentManageablePoemAdmin(admin.ModelAdmin):
    list_display = ('name', 'author', 'status', 'created_at')
    list_filter = ('status',)
    search_fields = ('name', 'text', 'author__username')
    ordering = ('-created_at',)
    actions = ['approve_poems', 'reject_poems']

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.has_perm('dashboard.can_manage_content'):
            return qs
        return qs.none()

    @admin.action(description=_('Approve selected poems'))
    def approve_poems(self, request, queryset):
        from dashboard.services import PoemManagementService
        service = PoemManagementService()
        for poem in queryset:
            service.approve_poem(poem, request.user)
        self.message_user(request, _('Selected poems approved.'))

    @admin.action(description=_('Reject selected poems'))
    def reject_poems(self, request, queryset):
        from dashboard.services import PoemManagementService
        service = PoemManagementService()
        for poem in queryset:
            service.reject_poem(poem, request.user)
        self.message_user(request, _('Selected poems rejected.'))


@admin.register(ContentActivityLog, site=custom_admin_site)
class ContentActivityLogAdmin(admin.ModelAdmin):
    list_display = ('manager', 'poem', 'action', 'timestamp')
    list_filter = ('action', 'timestamp')
    search_fields = ('manager__username', 'poem__name')
    ordering = ('-timestamp',)
    readonly_fields = ('manager', 'poem', 'action', 'timestamp', 'description')


@admin.register(RegistrationLog, site=custom_admin_site)
class RegistrationLogAdmin(admin.ModelAdmin):
    list_display = ('event', 'registration', 'request', 'timestamp', 'detail')
    list_filter = ('event',)
    search_fields = ('registration__username', 'request__email', 'detail')
    ordering = ('-timestamp',)
    readonly_fields = ('event', 'registration', 'request', 'timestamp', 'detail', 'ip_address', 'user_agent')


@admin.register(LoginAuditLog, site=custom_admin_site)
class LoginAuditLogAdmin(admin.ModelAdmin):
    list_display = ('event', 'user', 'username_attempted', 'ip_address', 'timestamp')
    list_filter = ('event',)
    search_fields = ('user__username', 'username_attempted', 'ip_address')
    ordering = ('-timestamp',)
    readonly_fields = ('user', 'username_attempted', 'event', 'ip_address', 'user_agent', 'timestamp')


@admin.register(RegistrationRequest, site=custom_admin_site)
class RegistrationRequestAdmin(admin.ModelAdmin):
    list_display = ('full_name', 'email', 'status', 'created_at', 'is_used', 'actions_column')
    list_filter = ('status',)
    search_fields = ('full_name', 'email')
    readonly_fields = ('token', 'token_created_at', 'is_used', 'used_at')
    actions = ['approve_requests', 'reject_requests', 'reset_requests']
    inlines = [RegistrationLogInline]

    def actions_column(self, obj):
        if obj.status != 'pending':
            return ''
        approve_url = reverse('admin:dashboard_registrationrequest_approve', args=[obj.pk])
        reject_url  = reverse('admin:dashboard_registrationrequest_reject', args=[obj.pk])
        return format_html(
            '<a class="button" href="{}">✅ Approve</a>&nbsp;'
            '<a class="button" href="{}">❌ Reject</a>',
            approve_url, reject_url,
        )
    actions_column.short_description = _('Quick actions')

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path(
                '<int:request_id>/approve/',
                self.admin_site.admin_view(self.approve_view),
                name='dashboard_registrationrequest_approve',
            ),
            path(
                '<int:request_id>/reject/',
                self.admin_site.admin_view(self.reject_view),
                name='dashboard_registrationrequest_reject',
            ),
        ]
        return custom_urls + urls

    def approve_view(self, request, request_id):
        req = RegistrationRequest.objects.get(pk=request_id)
        if req.status != 'pending':
            self.message_user(request, _('Request is not pending.'), messages.WARNING)
            return redirect('..')
        service = RegistrationService()
        service.approve_request(req)
        send_registration_link_email(req)
        self._update_user_status(req, 'approved')
        self._log_dashboard_event(req, RegistrationLog.Event.DASHBOARD_REQUEST_APPROVED)
        self.message_user(request, _('Request approved and email sent to %s.') % req.email)
        return redirect('..')

    def reject_view(self, request, request_id):
        req = RegistrationRequest.objects.get(pk=request_id)
        if req.status != 'pending':
            self.message_user(request, _('Request is not pending.'), messages.WARNING)
            return redirect('..')
        service = RegistrationService()
        service.reject_request(req)
        send_request_rejected_email(req)
        self._update_user_status(req, 'rejected')
        self._log_dashboard_event(req, RegistrationLog.Event.DASHBOARD_REQUEST_REJECTED)
        self.message_user(request, _('Request rejected and email sent to %s.') % req.email)
        return redirect('..')

    def save_model(self, request, obj, form, change):
        if change:
            old_obj = RegistrationRequest.objects.get(pk=obj.pk)
            old_status = old_obj.status
            new_status = obj.status
            if old_status == 'pending' and new_status != 'pending':
                if new_status == 'approved':
                    service = RegistrationService()
                    service.approve_request(obj)
                    send_registration_link_email(obj)
                    self._update_user_status(obj, 'approved')
                    self._log_dashboard_event(obj, RegistrationLog.Event.DASHBOARD_REQUEST_APPROVED)
                    self.message_user(request, _('Request approved and email sent to %s.') % obj.email)
                elif new_status == 'rejected':
                    service = RegistrationService()
                    service.reject_request(obj)
                    send_request_rejected_email(obj)
                    self._update_user_status(obj, 'rejected')
                    self._log_dashboard_event(obj, RegistrationLog.Event.DASHBOARD_REQUEST_REJECTED)
                    self.message_user(request, _('Request rejected and email sent to %s.') % obj.email)
        super().save_model(request, obj, form, change)

    @admin.action(description=_('Approve selected requests (email will be sent)'))
    def approve_requests(self, request, queryset):
        service = RegistrationService()
        pending = queryset.filter(status='pending')
        if not pending:
            self.message_user(request, _('No pending requests selected.'), messages.WARNING)
            return
        success = 0
        errors = []
        for req in pending:
            try:
                service.approve_request(req)
                send_registration_link_email(req)
                self._update_user_status(req, 'approved')
                self._log_dashboard_event(req, RegistrationLog.Event.DASHBOARD_REQUEST_APPROVED)
                success += 1
            except Exception as e:
                errors.append(f"{req.email}: {e}")
        if success:
            self.message_user(request, _('%d request(s) approved and email sent.') % success)
        if errors:
            self.message_user(request, _('Email errors: %s') % '; '.join(errors), messages.ERROR)

    @admin.action(description=_('Reject selected requests (email will be sent)'))
    def reject_requests(self, request, queryset):
        service = RegistrationService()
        pending = queryset.filter(status='pending')
        if not pending:
            self.message_user(request, _('No pending requests selected.'), messages.WARNING)
            return
        success = 0
        errors = []
        for req in pending:
            try:
                service.reject_request(req)
                send_request_rejected_email(req)
                self._update_user_status(req, 'rejected')
                self._log_dashboard_event(req, RegistrationLog.Event.DASHBOARD_REQUEST_REJECTED)
                success += 1
            except Exception as e:
                errors.append(f"{req.email}: {e}")
        if success:
            self.message_user(request, _('%d request(s) rejected and email sent.') % success)
        if errors:
            self.message_user(request, _('Email errors: %s') % '; '.join(errors), messages.ERROR)

    @admin.action(description=_('Reset selected requests (allow re-request)'))
    def reset_requests(self, request, queryset):
        for req in queryset:
            user = _get_user_by_email(req.email)
            if user:
                user.dashboard_request_used = False
                user.dashboard_request_used_at = None
                user.dashboard_request_status = 'none'
                user.can_request_dashboard = True
                user.save()
                RegistrationLog.objects.create(
                    request=req,
                    event=RegistrationLog.Event.DASHBOARD_REQUEST_RESET,
                    detail=f"Request reset for user {user.username}",
                )
        self.message_user(request, _('Selected requests have been reset.'))

    def _update_user_status(self, registration_request, status):
        user = _get_user_by_email(registration_request.email)
        if user:
            user.dashboard_request_status = status
            user.save(update_fields=['dashboard_request_status'])

    def _log_dashboard_event(self, registration_request, event):
        user = _get_user_by_email(registration_request.email)
        RegistrationLog.objects.create(
            request=registration_request,
            event=event,
            detail=f"User: {user.username if user else 'unknown'}",
        )


@admin.register(ContentManagerRegistration, site=custom_admin_site)
class ContentManagerRegistrationAdmin(admin.ModelAdmin):
    list_display = ('username', 'request', 'phone', 'status', 'created_at', 'reg_actions_column')
    list_filter = ('status',)
    search_fields = ('username', 'request__full_name', 'phone')
    readonly_fields = ('photo_preview', 'video_preview')
    actions = ['approve_registrations', 'reject_registrations']
    inlines = [RegistrationLogInline]

    def photo_preview(self, obj):
        if obj.photo:
            return format_html('<img src="{}" style="max-height:150px;"/>', obj.photo.url)
        return '-'
    photo_preview.short_description = _('Photo')

    def video_preview(self, obj):
        if obj.video:
            return format_html(
                '<video controls style="max-height:150px;"><source src="{}" type="video/webm"></video>',
                obj.video.url,
            )
        return '-'
    video_preview.short_description = _('Video')

    def reg_actions_column(self, obj):
        if obj.status != 'pending_verification':
            return ''
        approve_url = reverse('admin:dashboard_contentmanagerregistration_approve', args=[obj.pk])
        reject_url  = reverse('admin:dashboard_contentmanagerregistration_reject', args=[obj.pk])
        return format_html(
            '<a class="button" href="{}">✅ Approve</a>&nbsp;'
            '<a class="button" href="{}">❌ Reject</a>',
            approve_url, reject_url,
        )
    reg_actions_column.short_description = _('Quick actions')

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path(
                '<int:reg_id>/approve/',
                self.admin_site.admin_view(self.approve_reg_view),
                name='dashboard_contentmanagerregistration_approve',
            ),
            path(
                '<int:reg_id>/reject/',
                self.admin_site.admin_view(self.reject_reg_view),
                name='dashboard_contentmanagerregistration_reject',
            ),
        ]
        return custom_urls + urls

    def approve_reg_view(self, request, reg_id):
        reg = ContentManagerRegistration.objects.get(pk=reg_id)
        if reg.status != 'pending_verification':
            self.message_user(request, _('Registration is not pending verification.'), messages.WARNING)
            return redirect('..')
        service = RegistrationService()
        service.approve_registration(reg)
        send_account_approved_email(reg)
        self.message_user(request, _('Registration approved and email sent to %s.') % reg.request.email)
        return redirect('..')

    def reject_reg_view(self, request, reg_id):
        reg = ContentManagerRegistration.objects.get(pk=reg_id)
        if reg.status != 'pending_verification':
            self.message_user(request, _('Registration is not pending verification.'), messages.WARNING)
            return redirect('..')
        service = RegistrationService()
        service.reject_registration(reg)
        send_registration_rejected_email(reg)
        self.message_user(request, _('Registration rejected and email sent to %s.') % reg.request.email)
        return redirect('..')

    def save_model(self, request, obj, form, change):
        if change:
            old_obj = ContentManagerRegistration.objects.get(pk=obj.pk)
            old_status = old_obj.status
            new_status = obj.status
            if old_status == 'pending_verification' and new_status != 'pending_verification':
                if new_status == 'approved':
                    service = RegistrationService()
                    service.approve_registration(obj)
                    send_account_approved_email(obj)
                    self.message_user(request, _('Registration approved and email sent to %s.') % obj.request.email)
                elif new_status == 'rejected':
                    service = RegistrationService()
                    service.reject_registration(obj)
                    send_registration_rejected_email(obj)
                    self.message_user(request, _('Registration rejected and email sent to %s.') % obj.request.email)
        super().save_model(request, obj, form, change)

    @admin.action(description=_('Approve registrations (email will be sent)'))
    def approve_registrations(self, request, queryset):
        service = RegistrationService()
        pending = queryset.filter(status='pending_verification')
        if not pending:
            self.message_user(request, _('No pending registrations selected.'), messages.WARNING)
            return
        success = 0
        errors = []
        for reg in pending:
            try:
                service.approve_registration(reg)
                send_account_approved_email(reg)
                success += 1
            except Exception as e:
                errors.append(f"{reg.username}: {e}")
        if success:
            self.message_user(request, _('%d registration(s) approved.') % success)
        if errors:
            self.message_user(request, _('Email errors: %s') % '; '.join(errors), messages.ERROR)

    @admin.action(description=_('Reject registrations (email will be sent)'))
    def reject_registrations(self, request, queryset):
        service = RegistrationService()
        pending = queryset.filter(status='pending_verification')
        if not pending:
            self.message_user(request, _('No pending registrations selected.'), messages.WARNING)
            return
        success = 0
        errors = []
        for reg in pending:
            try:
                service.reject_registration(reg)
                send_registration_rejected_email(reg)
                success += 1
            except Exception as e:
                errors.append(f"{reg.username}: {e}")
        if success:
            self.message_user(request, _('%d registration(s) rejected.') % success)
        if errors:
            self.message_user(request, _('Email errors: %s') % '; '.join(errors), messages.ERROR)