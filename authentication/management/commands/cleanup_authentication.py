from django.core.management.base import BaseCommand
from django.utils import timezone

from authentication.models import VerificationSession, OTPToken


class Command(BaseCommand):
    help = 'Delete expired verification sessions and OTP tokens.'

    def handle(self, *args, **options):
        now = timezone.now()

        expired_sessions = VerificationSession.objects.filter(expires_at__lt=now)
        count_sessions = expired_sessions.count()
        for session in expired_sessions:
            session.delete_media()   # deletes video file and record

        expired_otps = OTPToken.objects.filter(expires_at__lt=now)
        count_otps = expired_otps.count()
        expired_otps.delete()

        self.stdout.write(self.style.SUCCESS(
            f'Deleted {count_sessions} expired verification sessions and {count_otps} expired OTP tokens.'
        ))