# authentication/admin.py

from django.contrib import admin
from django.utils.translation import gettext_lazy as _

from config.admin_site import custom_admin_site
from .models import (
    FaceReference,
    VerificationSession,
    OTPToken,
    DashboardAccessRecord,
)


@admin.register(FaceReference, site=custom_admin_site)
class FaceReferenceAdmin(admin.ModelAdmin):
    list_display = ('user', 'created_at', 'updated_at')
    search_fields = ('user__username', 'user__email', 'user__first_name', 'user__last_name')
    # Only timestamps are read-only. User, image, and embedding remain editable.
    readonly_fields = ('created_at', 'updated_at')
    ordering = ('-created_at',)


@admin.register(VerificationSession, site=custom_admin_site)
class VerificationSessionAdmin(admin.ModelAdmin):
    list_display = ('user', 'status', 'created_at', 'expires_at')
    list_filter = ('status',)
    search_fields = ('user__username', 'user__email')
    readonly_fields = ('created_at',)
    ordering = ('-created_at',)


@admin.register(OTPToken, site=custom_admin_site)
class OTPTokenAdmin(admin.ModelAdmin):
    list_display = ('user', 'created_at', 'expires_at', 'attempts', 'is_used')
    list_filter = ('is_used',)
    search_fields = ('user__username', 'user__email')
    # otp_hash is sensitive; keep it read-only but allow other fields to be edited.
    readonly_fields = ('created_at', 'otp_hash')
    ordering = ('-created_at',)


@admin.register(DashboardAccessRecord, site=custom_admin_site)
class DashboardAccessRecordAdmin(admin.ModelAdmin):
    list_display = ('user', 'verified_at', 'expires_at', 'ip_address')
    list_filter = ('verified_at',)
    search_fields = ('user__username', 'user__email', 'ip_address')
    readonly_fields = ('verified_at',)
    ordering = ('-verified_at',)
# END