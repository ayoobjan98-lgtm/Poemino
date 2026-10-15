
import logging

from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils.translation import gettext_lazy as _

logger = logging.getLogger(__name__)


def send_password_reset_email(user, token):
    site_url = getattr(settings, 'SITE_URL', 'http://localhost:8000').rstrip('/')
    link = f"{site_url}/accounts/reset/{token}/"
    context = {
        'user': user,
        'link': link,
    }

    subject = _("Password Reset Request")
    html_body = render_to_string('accounts/password_reset_email.html', context)
    text_body = render_to_string('accounts/password_reset_email.txt', context)

    msg = EmailMultiAlternatives(
        subject=subject,
        body=text_body,
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=[user.email],
    )
    msg.attach_alternative(html_body, "text/html")
    try:
        msg.send(fail_silently=False)
        logger.info("Password reset email sent to %s", user.email)
    except Exception:
        logger.exception("Failed to send password reset email to %s", user.email)