
import logging

from django.contrib.auth.signals import user_logged_in, user_logged_out, user_login_failed
from django.dispatch import receiver
from django.utils import timezone

from dashboard.models import LoginAuditLog, LoginAttempt

logger = logging.getLogger(__name__)


def get_client_ip(request):
    xff = request.META.get('HTTP_X_FORWARDED_FOR')
    if xff:
        ip = xff.split(',')[0].strip()
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip


@receiver(user_login_failed)
def handle_failed_login(sender, credentials, request, **kwargs):
    username = credentials.get('username', '')
    ip = get_client_ip(request) if request else '0.0.0.0'
    user_agent = request.META.get('HTTP_USER_AGENT', '')[:500] if request else ''

    # Log the attempt for rate limiting
    LoginAttempt.objects.create(username=username, ip_address=ip)

    # Log audit event
    LoginAuditLog.objects.create(
        username_attempted=username,
        event=LoginAuditLog.Event.LOGIN_FAILED,
        ip_address=ip,
        user_agent=user_agent,
    )
    logger.info("Failed login attempt for username '%s' from IP %s.", username, ip)


@receiver(user_logged_in)
def handle_successful_login(sender, request, user, **kwargs):
    ip = get_client_ip(request) if request else '0.0.0.0'
    user_agent = request.META.get('HTTP_USER_AGENT', '')[:500] if request else ''

    LoginAuditLog.objects.create(
        user=user,
        username_attempted=user.get_username(),
        event=LoginAuditLog.Event.LOGIN_SUCCESS,
        ip_address=ip,
        user_agent=user_agent,
    )
    logger.info("Successful login for user '%s' from IP %s.", user, ip)


@receiver(user_logged_out)
def handle_logout(sender, request, user, **kwargs):
    if user is None:
        return
    ip = get_client_ip(request) if request else '0.0.0.0'
    user_agent = request.META.get('HTTP_USER_AGENT', '')[:500] if request else ''

    LoginAuditLog.objects.create(
        user=user,
        username_attempted=user.get_username(),
        event=LoginAuditLog.Event.LOGOUT,
        ip_address=ip,
        user_agent=user_agent,
    )
    logger.info("User '%s' logged out from IP %s.", user, ip)