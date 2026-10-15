from django.conf import settings
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from MakerPom.models import CreatPom


class ContentManageablePoem(CreatPom):
    """Proxy model to attach custom content‑management permissions."""

    class Meta:
        proxy = True
        verbose_name = _('Manageable Poem')
        verbose_name_plural = _('Manageable Poems')
        permissions = [
            ('can_manage_content', _('Can manage poems and audio content')),
        ]


class ContentActivityLog(models.Model):
    """Stores content‑related actions performed by content managers."""

    class Action(models.TextChoices):
        APPROVED = 'approved', _('Approved')
        REJECTED = 'rejected', _('Rejected')
        EDITED = 'edited', _('Edited')
        AUDIO_REPLACED = 'audio_replaced', _('Audio replaced')
        AUDIO_DELETED = 'audio_deleted', _('Audio deleted')
        RETURNED_TO_REVIEW = 'returned_to_review', _('Returned to review')
    manager = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='content_actions',
        verbose_name=_('Manager'),
    )
    poem = models.ForeignKey(
        CreatPom,
        on_delete=models.CASCADE,
        related_name='activity_logs',
        verbose_name=_('Poem'),
    )
    action = models.CharField(
        max_length=20,
        choices=Action.choices,
        verbose_name=_('Action'),
    )
    timestamp = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_('Timestamp'),
    )
    description = models.TextField(
        blank=True,
        verbose_name=_('Description'),
    )

    class Meta:
        verbose_name = _('Activity log')
        verbose_name_plural = _('Activity logs')
        ordering = ['-timestamp']

    def __str__(self):
        return f'{self.manager} – {self.get_action_display()} – {self.poem}'


class RegistrationRequest(models.Model):
    """A visitor's request to become a content manager."""

    full_name = models.CharField(max_length=200, verbose_name=_('Full Name'))
    email = models.EmailField(verbose_name=_('Email Address'))
    message = models.TextField(blank=True, verbose_name=_('Message'))
    status = models.CharField(
        max_length=10,
        choices=[
            ('pending', _('Pending')),
            ('approved', _('Approved')),
            ('rejected', _('Rejected')),
        ],
        default='pending',
        verbose_name=_('Status'),
    )
    token = models.CharField(max_length=64, unique=True, null=True, blank=True)
    token_created_at = models.DateTimeField(null=True, blank=True)
    is_used = models.BooleanField(default=False)
    used_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = _('Registration Request')
        verbose_name_plural = _('Registration Requests')
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.full_name} ({self.email})'

    def generate_token(self):
        import secrets
        self.token = secrets.token_urlsafe(48)
        self.token_created_at = timezone.now()
        self.is_used = False
        self.used_at = None
        self.save(update_fields=['token', 'token_created_at', 'is_used', 'used_at'])

    def is_token_valid(self):
        from datetime import timedelta
        if not self.token or self.is_used:
            return False
        if self.token_created_at is None:
            return False
        expiration_time = self.token_created_at + timedelta(minutes=30)
        return timezone.now() <= expiration_time

    def invalidate_token(self):
        self.is_used = True
        self.used_at = timezone.now()
        self.token = None
        self.token_created_at = None
        self.save(update_fields=['is_used', 'used_at', 'token', 'token_created_at'])


class ContentManagerRegistration(models.Model):
    """Stores the registration data submitted via the hidden link."""

    request = models.OneToOneField(
        RegistrationRequest,
        on_delete=models.CASCADE,
        related_name='registration',
        verbose_name=_('Initial Request'),
    )
    username = models.CharField(max_length=150, verbose_name=_('Username'))
    password = models.CharField(max_length=128, verbose_name=_('Password'))
    phone = models.CharField(max_length=20, verbose_name=_('Phone Number'))
    photo = models.ImageField(upload_to='verification/photos/', verbose_name=_('Live Photo'))
    video = models.FileField(upload_to='verification/videos/', verbose_name=_('Video Recording'))
    status = models.CharField(
        max_length=20,
        choices=[
            ('pending_verification', _('Pending Verification')),
            ('approved', _('Approved')),
            ('rejected', _('Rejected')),
        ],
        default='pending_verification',
        verbose_name=_('Status'),
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = _('Content Manager Registration')
        verbose_name_plural = _('Content Manager Registrations')
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.username} – {self.get_status_display()}'


class RegistrationLog(models.Model):
    """Logs every step of the registration workflow."""

    class Event(models.TextChoices):
        ACCESS_REQUEST_CREATED = 'access_request_created', _('Access Request Created')
        REGISTRATION_STARTED = 'registration_started', _('Registration Started')
        BASIC_INFO_SUBMITTED = 'basic_info_submitted', _('Basic Info Submitted')
        PHOTO_CAPTURED = 'photo_captured', _('Photo Captured')
        VIDEO_RECORDED = 'video_recorded', _('Video Recorded')
        REGISTRATION_COMPLETED = 'registration_completed', _('Registration Completed')
        ADMIN_NOTIFICATION_SENT = 'admin_notification_sent', _('Admin Notification Sent')
        APPROVAL = 'approval', _('Approval')
        REJECTION = 'rejection', _('Rejection')
        TOKEN_CREATED = 'token_created', _('Token Created')
        TOKEN_OPENED = 'token_opened', _('Token Opened')
        TOKEN_EXPIRED = 'token_expired', _('Token Expired')
        TOKEN_INVALID = 'token_invalid', _('Invalid Token')
        TOKEN_REUSED = 'token_reused', _('Reused Token')
        DASHBOARD_REQUEST_OPENED = 'dashboard_request_opened', _('Dashboard Request Opened')
        DASHBOARD_REQUEST_SUBMITTED = 'dashboard_request_submitted', _('Dashboard Request Submitted')
        DASHBOARD_REQUEST_BLOCKED = 'dashboard_request_blocked', _('Dashboard Request Blocked')
        DASHBOARD_REQUEST_APPROVED = 'dashboard_request_approved', _('Dashboard Request Approved')
        DASHBOARD_REQUEST_REJECTED = 'dashboard_request_rejected', _('Dashboard Request Rejected')
        DASHBOARD_REQUEST_RESET = 'dashboard_request_reset', _('Dashboard Request Reset')
        EMAIL_CHANGED = 'email_changed', _('Email Changed')

    registration = models.ForeignKey(
        ContentManagerRegistration,
        on_delete=models.CASCADE,
        related_name='logs',
        null=True,
        blank=True,
        verbose_name=_('Registration'),
    )
    request = models.ForeignKey(
        RegistrationRequest,
        on_delete=models.CASCADE,
        related_name='logs',
        null=True,
        blank=True,
        verbose_name=_('Request'),
    )
    event = models.CharField(
        max_length=35,
        choices=Event.choices,
        verbose_name=_('Event'),
    )
    timestamp = models.DateTimeField(auto_now_add=True, verbose_name=_('Timestamp'))
    detail = models.TextField(blank=True, verbose_name=_('Detail'))
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)

    class Meta:
        verbose_name = _('Registration Log')
        verbose_name_plural = _('Registration Logs')
        ordering = ['-timestamp']

    def __str__(self):
        return f'{self.get_event_display()} @ {self.timestamp}'


class LoginAuditLog(models.Model):
    class Event(models.TextChoices):
        LOGIN_SUCCESS = 'login_success', _('Login Success')
        LOGIN_FAILED = 'login_failed', _('Login Failed')
        LOGOUT = 'logout', _('Logout')

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='login_audit_logs',
    )
    username_attempted = models.CharField(max_length=150, blank=True)
    event = models.CharField(max_length=15, choices=Event.choices)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = _('Login Audit Log')
        verbose_name_plural = _('Login Audit Logs')
        ordering = ['-timestamp']

    def __str__(self):
        return f'{self.event} – {self.username_attempted or self.user} @ {self.timestamp}'


class LoginAttempt(models.Model):
    username = models.CharField(max_length=150)
    ip_address = models.GenericIPAddressField()
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = _('Login Attempt')
        verbose_name_plural = _('Login Attempts')
        ordering = ['-timestamp']

    @classmethod
    def is_blocked(cls, username, ip_address):
        from datetime import timedelta
        cutoff = timezone.now() - timedelta(minutes=15)
        return cls.objects.filter(
            username=username,
            ip_address=ip_address,
            timestamp__gte=cutoff,
        ).count() >= 5