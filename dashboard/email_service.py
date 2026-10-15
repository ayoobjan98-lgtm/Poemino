
import logging
import sys
from typing import Optional

from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.urls import reverse
from django.utils.translation import gettext_lazy as _

from dashboard.models import RegistrationRequest, ContentManagerRegistration

logger = logging.getLogger(__name__)


def _log_email_settings() -> None:
    DEBUG_EMAIL = getattr(settings, 'DEBUG_EMAIL', True)
    if DEBUG_EMAIL:
        lines = [
            "────────── EMAIL SETTINGS ──────────",
            f"BACKEND:  {getattr(settings, 'EMAIL_BACKEND', 'NOT SET')}",
            f"HOST:     {getattr(settings, 'EMAIL_HOST', 'NOT SET')}",
            f"PORT:     {getattr(settings, 'EMAIL_PORT', 'NOT SET')}",
            f"USE_TLS:  {getattr(settings, 'EMAIL_USE_TLS', 'NOT SET')}",
            f"USE_SSL:  {getattr(settings, 'EMAIL_USE_SSL', 'NOT SET')}",
            f"HOST_USER:{getattr(settings, 'EMAIL_HOST_USER', 'NOT SET')}",
            f"HOST_PASS:{'***' if getattr(settings, 'EMAIL_HOST_PASSWORD', None) else 'NOT SET'}",
            f"DEFAULT_FROM: {getattr(settings, 'DEFAULT_FROM_EMAIL', 'NOT SET')}",
            f"SITE_URL: {getattr(settings, 'SITE_URL', 'NOT SET')}",
            "────────────────────────────────────",
        ]
        for line in lines:
            logger.info(line)
            print(line, file=sys.stderr)


def _build_absolute_url(path: str) -> str:
    site_url = getattr(settings, 'SITE_URL', 'http://localhost:8000').rstrip('/')
    return f"{site_url}{path}"


def send_registration_link_email(request_obj: RegistrationRequest) -> None:
    """
    Send an email containing the one‑time registration link.
    """
    _log_email_settings()
    logger.info("▶ send_registration_link_email for request id=%s, email='%s'.", request_obj.pk, request_obj.email)
    print(f"DEBUG: Sending registration link email to {request_obj.email}", file=sys.stderr)

    if not request_obj.email:
        raise ValueError("Recipient email is empty.")
    if not request_obj.token or not request_obj.is_token_valid():
        raise ValueError("Token invalid or expired.")

    link = _build_absolute_url(f"/dashboard/hidden/register/{request_obj.token}/")
    logger.debug("Registration link: %s", link)

    context = {'full_name': request_obj.full_name, 'link': link}
    html_body = render_to_string('dashboard/emails/registration_link_email.html', context)
    text_body = render_to_string('dashboard/emails/registration_link_email.txt', context)

    subject = _("Complete Your Content Manager Registration")
    msg = EmailMultiAlternatives(
        subject=subject,
        body=text_body,
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=[request_obj.email],
    )
    msg.attach_alternative(html_body, "text/html")
    msg.send(fail_silently=False)
    logger.info("Registration link email sent to '%s'.", request_obj.email)
    print(f"DEBUG: Email sent to {request_obj.email}", file=sys.stderr)


def send_request_rejected_email(request_obj: RegistrationRequest) -> None:
    _log_email_settings()
    logger.info("▶ send_request_rejected_email for request id=%s, email='%s'.", request_obj.pk, request_obj.email)
    print(f"DEBUG: Sending rejection email to {request_obj.email}", file=sys.stderr)

    context = {'full_name': request_obj.full_name}
    html_body = render_to_string('dashboard/emails/request_rejected_email.html', context)
    text_body = render_to_string('dashboard/emails/request_rejected_email.txt', context)

    subject = _("Your Access Request Has Been Declined")
    msg = EmailMultiAlternatives(
        subject=subject,
        body=text_body,
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=[request_obj.email],
    )
    msg.attach_alternative(html_body, "text/html")
    msg.send(fail_silently=False)
    logger.info("Request rejected email sent to '%s'.", request_obj.email)
    print(f"DEBUG: Email sent to {request_obj.email}", file=sys.stderr)


def send_account_approved_email(registration: ContentManagerRegistration) -> None:
    _log_email_settings()
    logger.info("▶ send_account_approved_email for username='%s', email='%s'.",
                registration.username, registration.request.email)
    print(f"DEBUG: Sending account approved email to {registration.request.email}", file=sys.stderr)

    dashboard_url = _build_absolute_url("/dashboard/")
    context = {
        'username': registration.username,
        'full_name': registration.request.full_name,
        'dashboard_url': dashboard_url,
    }
    html_body = render_to_string('dashboard/emails/account_approved_email.html', context)
    text_body = render_to_string('dashboard/emails/account_approved_email.txt', context)

    subject = _("Your Content Manager Account Is Now Active")
    msg = EmailMultiAlternatives(
        subject=subject,
        body=text_body,
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=[registration.request.email],
    )
    msg.attach_alternative(html_body, "text/html")
    msg.send(fail_silently=False)
    logger.info("Account approved email sent to '%s'.", registration.request.email)
    print(f"DEBUG: Email sent to {registration.request.email}", file=sys.stderr)


def send_registration_rejected_email(registration: ContentManagerRegistration) -> None:
    _log_email_settings()
    logger.info("▶ send_registration_rejected_email for username='%s', email='%s'.",
                registration.username, registration.request.email)
    print(f"DEBUG: Sending registration rejected email to {registration.request.email}", file=sys.stderr)

    context = {
        'username': registration.username,
        'full_name': registration.request.full_name,
    }
    html_body = render_to_string('dashboard/emails/registration_rejected_email.html', context)
    text_body = render_to_string('dashboard/emails/registration_rejected_email.txt', context)

    subject = _("Your Registration Has Been Declined")
    msg = EmailMultiAlternatives(
        subject=subject,
        body=text_body,
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=[registration.request.email],
    )
    msg.attach_alternative(html_body, "text/html")
    msg.send(fail_silently=False)
    logger.info("Registration rejected email sent to '%s'.", registration.request.email)
    print(f"DEBUG: Email sent to {registration.request.email}", file=sys.stderr)


def send_admin_notification_email(registration: ContentManagerRegistration) -> None:
    """Notify the site administrator that a new registration is pending review."""
    _log_email_settings()
    admin_email = getattr(settings, 'ADMIN_EMAIL', settings.DEFAULT_FROM_EMAIL)
    logger.info("▶ send_admin_notification_email for username='%s', admin email='%s'.",
                registration.username, admin_email)
    print(f"DEBUG: Sending admin notification to {admin_email}", file=sys.stderr)

    site_url = getattr(settings, 'SITE_URL', 'http://localhost:8000').rstrip('/')
    # Use the admin link to the ContentManagerRegistration change page
    review_link = f"{site_url}/admin/dashboard/contentmanagerregistration/{registration.pk}/change/"

    context = {
        'username': registration.username,
        'full_name': registration.request.full_name,
        'phone': registration.phone,
        'email': registration.request.email,
        'status': registration.get_status_display(),
        'created_at': registration.created_at,
        'review_link': review_link,
    }
    html_body = render_to_string('dashboard/emails/admin_notification_email.html', context)
    text_body = render_to_string('dashboard/emails/admin_notification_email.txt', context)

    subject = _("New Content Manager Registration Pending Review")
    msg = EmailMultiAlternatives(
        subject=subject,
        body=text_body,
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=[admin_email],
    )
    msg.attach_alternative(html_body, "text/html")
    try:
        msg.send(fail_silently=False)
        logger.info("Admin notification email sent to '%s'.", admin_email)
        print(f"DEBUG: Admin notification sent to {admin_email}", file=sys.stderr)
    except Exception:
        logger.exception("Failed to send admin notification email to '%s'.", admin_email)
        raise