from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from datetime import timedelta

from .managers import CustomUserManager


class CustomUser(AbstractBaseUser, PermissionsMixin):
    username = models.CharField(max_length=150, unique=True, verbose_name=_('Username'))
    email = models.EmailField(
        unique=True,
        blank=True, null=True,
        verbose_name=_('Email Address')
    )
    avatar = models.ImageField(
        upload_to='avatars/',
        blank=True, null=True,
        verbose_name=_('Profile Picture')
    )
    first_name = models.CharField(max_length=150, blank=True, verbose_name=_('First Name'))
    last_name = models.CharField(max_length=150, blank=True, verbose_name=_('Last Name'))
    bio = models.TextField(blank=True, verbose_name=_('About Me'))
    date_of_birth = models.DateField(null=True, blank=True, verbose_name=_('Date of Birth'))

    is_active = models.BooleanField(default=True, verbose_name=_('Active'))
    is_staff = models.BooleanField(default=False, verbose_name=_('Admin Access'))
    is_superuser = models.BooleanField(default=False, verbose_name=_('Superuser Status'))
    date_joined = models.DateTimeField(auto_now_add=True, verbose_name=_('Date Joined'))

    is_page_permitted = models.BooleanField(
        default=False,
        verbose_name=_('Dashboard Access'),
        help_text=_('Designates whether the user can access the content manager dashboard.')
    )

    can_request_dashboard = models.BooleanField(
        default=False,
        verbose_name=_("Can Request Dashboard"),
        help_text=_("Allow this user to access the dashboard access request page.")
    )
    dashboard_request_used = models.BooleanField(
        default=False,
        verbose_name=_("Dashboard Request Used"),
        help_text=_("Indicates whether the user has already used the dashboard access request page.")
    )
    dashboard_request_used_at = models.DateTimeField(
        null=True, blank=True,
        verbose_name=_("Dashboard Request Used At"),
        help_text=_("Date and time when the dashboard access request page was used.")
    )
    dashboard_request_status = models.CharField(
        max_length=20,
        choices=[
            ("none", _("No Request")),
            ("pending", _("Pending")),
            ("approved", _("Approved")),
            ("rejected", _("Rejected")),
        ],
        default="none",
        verbose_name=_("Dashboard Request Status"),
        help_text=_("Current status of the dashboard access request.")
    )

    can_view_pom = models.BooleanField(verbose_name=_("View Pom"), default=False)
    can_create_pom = models.BooleanField(verbose_name=_("Create Pom"), default=False)
    can_update_pom = models.BooleanField(verbose_name=_("Update Pom"), default=False)
    can_delete_pom = models.BooleanField(verbose_name=_("Delete Pom"), default=False)
    can_view_api = models.BooleanField(verbose_name=_("API View"), default=False)

    USERNAME_FIELD = 'username'
    REQUIRED_FIELDS = []

    
    objects = CustomUserManager()

    class Meta:
        verbose_name = _('User')
        verbose_name_plural = _('Users')

    def get_full_name(self):
        full = f"{self.first_name} {self.last_name}".strip()
        return full if full else self.username

    def __str__(self):
        return self.username


class PasswordResetToken(models.Model):
    user = models.ForeignKey(
        CustomUser,
        on_delete=models.CASCADE,
        related_name='password_reset_tokens',
        verbose_name=_('User'),
    )
    token = models.CharField(max_length=64, unique=True, verbose_name=_('Token'))
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_('Created At'))
    is_used = models.BooleanField(default=False, verbose_name=_('Is Used'))

    class Meta:
        verbose_name = _('Password Reset Token')
        verbose_name_plural = _('Password Reset Tokens')
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.user.username} – Token'

    def is_valid(self):
        if self.is_used:
            return False
        expiration = self.created_at + timedelta(minutes=30)
        return timezone.now() <= expiration


class LoginVerification(models.Model):
    """Stores face photo and video captured during dashboard login verification."""
    user = models.ForeignKey(
        CustomUser,
        on_delete=models.CASCADE,
        related_name='login_verifications',
        verbose_name=_('User'),
    )
    photo = models.ImageField(upload_to='login_verifications/photos/', verbose_name=_('Face Photo'))
    video = models.FileField(upload_to='login_verifications/videos/', verbose_name=_('Video Recording'))
    timestamp = models.DateTimeField(auto_now_add=True, verbose_name=_('Timestamp'))
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)

    class Meta:
        verbose_name = _('Login Verification')
        verbose_name_plural = _('Login Verifications')
        ordering = ['-timestamp']

    def __str__(self):
        return f'{self.user.username} – {self.timestamp}'
    

class Profile(models.Model):
    user = models.OneToOneField(to=CustomUser, on_delete=models.CASCADE, related_name="profile", primary_key=True)  

