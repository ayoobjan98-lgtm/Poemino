import secrets
from datetime import timedelta

from django.conf import settings
from django.contrib.auth.hashers import make_password, check_password
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _


def default_verification_expiry():
    """Return default expiration for verification sessions."""
    return timezone.now() + timedelta(hours=24)


# Compatibility alias for old migrations that reference authentication.models.verification_expiry
verification_expiry = default_verification_expiry


class FaceReference(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='face_reference',
        verbose_name=_('User'),
    )
    image = models.ImageField(upload_to='face_references/', verbose_name=_('Reference Face Image'))
    embedding = models.TextField(verbose_name=_('Face Embedding'))
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _('Face Reference')
        verbose_name_plural = _('Face References')


class VerificationSession(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='verification_sessions',
        verbose_name=_('User'),
    )
    video = models.FileField(upload_to='verification_videos/', verbose_name=_('Verification Video'))
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField(default=default_verification_expiry)
    status = models.CharField(
        max_length=20,
        choices=[
            ('pending', _('Pending')),
            ('face_verified', _('Face Verified')),
            ('liveness_passed', _('Liveness Passed')),
            ('failed', _('Failed')),
            ('completed', _('Completed')),
        ],
        default='pending',
        verbose_name=_('Status'),
    )

    class Meta:
        verbose_name = _('Verification Session')
        verbose_name_plural = _('Verification Sessions')
        ordering = ['-created_at']

    def is_expired(self):
        return timezone.now() > self.expires_at


class OTPToken(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='otp_tokens',
        verbose_name=_('User'),
    )
    session = models.ForeignKey(
        VerificationSession,
        on_delete=models.CASCADE,
        related_name='otp_tokens',
        null=True,
        blank=True,
        verbose_name=_('Verification Session'),
    )
    otp_hash = models.CharField(max_length=128, verbose_name=_('OTP Hash'))
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField(verbose_name=_('Expires At'))
    attempts = models.PositiveIntegerField(default=0)
    is_used = models.BooleanField(default=False)

    class Meta:
        verbose_name = _('OTP Token')
        verbose_name_plural = _('OTP Tokens')

    def is_expired(self):
        return timezone.now() > self.expires_at

    def verify_otp(self, raw_otp):
        if self.is_used or self.is_expired() or self.attempts >= 5:
            return False
        if not check_password(raw_otp, self.otp_hash):
            self.attempts += 1
            self.save(update_fields=['attempts'])
            return False
        self.is_used = True
        self.save(update_fields=['is_used'])
        return True


class DashboardAccessRecord(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='dashboard_access_records',
        verbose_name=_('User'),
    )
    verified_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField(verbose_name=_('Expires At'))
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)

    class Meta:
        verbose_name = _('Dashboard Access Record')
        verbose_name_plural = _('Dashboard Access Records')
        ordering = ['-verified_at']

    def is_valid(self):
        return timezone.now() <= self.expires_at