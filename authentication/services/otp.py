import secrets
import logging
from datetime import timedelta

from django.conf import settings
from django.contrib.auth.hashers import make_password
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from authentication.models import OTPToken, VerificationSession

logger = logging.getLogger(__name__)


def generate_otp():
    """Return a 6-digit cryptographically secure OTP."""
    return str(secrets.randbelow(1000000)).zfill(6)


def create_otp_for_session(session: VerificationSession) -> str:
    """
    Create a new OTP linked to the given completed VerificationSession.

    All previous unused OTPs for the same user are invalidated first.
    Returns the plain OTP string.
    """
    user = session.user

    # Invalidate all previous unused OTPs for this user.
    OTPToken.objects.filter(user=user, is_used=False).delete()

    otp = generate_otp()
    OTPToken.objects.create(
        user=user,
        session=session,
        otp_hash=make_password(otp),
        expires_at=timezone.now() + timedelta(minutes=2),
    )
    return otp


def create_otp_for_user(user) -> str:
    """
    Backward-compatible wrapper.

    Finds the user's latest completed, non-expired VerificationSession and
    creates a new OTP linked to that session.
    """
    session = VerificationSession.objects.filter(
        user=user,
        status='completed',
        expires_at__gt=timezone.now(),
    ).order_by('-created_at').first()

    if not session:
        raise ValueError(_("No completed verification session found."))

    return create_otp_for_session(session)


def send_otp_email(user, otp: str) -> None:
    """Send the OTP to the user's registered email address."""
    context = {'user': user, 'otp': otp}
    subject = _("Your Dashboard OTP")
    html_body = render_to_string('authentication/emails/otp_email.html', context)
    text_body = render_to_string('authentication/emails/otp_email.txt', context)

    msg = EmailMultiAlternatives(
        subject=subject,
        body=text_body,
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=[user.email],
    )
    msg.attach_alternative(html_body, "text/html")
    try:
        msg.send(fail_silently=False)
        logger.info("OTP sent to %s", user.email)
    except Exception:
        logger.exception("Failed to send OTP email to %s", user.email)


def verify_otp(user, raw_otp: str):
    """
    Verify an OTP for the given user.

    Only the newest unused, non-expired OTPToken is considered.
    Returns (success: bool, message: str).
    """
    token = OTPToken.objects.filter(
        user=user,
        is_used=False,
        expires_at__gt=timezone.now(),
    ).order_by('-created_at').first()

    if not token:
        return False, _('No active OTP. Please request a new one.')

    if token.verify_otp(raw_otp):
        return True, _('OTP verified.')
    return False, _('Invalid OTP or expired.')