from datetime import timedelta

from django.utils import timezone

from authentication.models import DashboardAccessRecord


def has_valid_dashboard_access(user):
    """
    Return True only if the current user has at least one valid, non-expired
    DashboardAccessRecord. Strictly scoped to `user`.
    """
    if not user.is_authenticated:
        return False

    return DashboardAccessRecord.objects.filter(
        user=user,
        expires_at__gt=timezone.now(),
    ).exists()


def grant_dashboard_access(user, request=None):
    """
    Create a new 7-day dashboard access record for the current user only.

    This always creates a fresh record and never deletes, updates, or
    overwrites any other user's records. Multiple records per user are
    allowed by the model.
    """
    record = DashboardAccessRecord.objects.create(
        user=user,
        expires_at=timezone.now() + timedelta(days=7),
        ip_address=request.META.get('REMOTE_ADDR') if request else None,
        user_agent=request.META.get('HTTP_USER_AGENT', '')[:500] if request else '',
    )
    return record