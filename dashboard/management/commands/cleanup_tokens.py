
from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta

from dashboard.models import RegistrationRequest


class Command(BaseCommand):
    help = 'Delete expired unused registration tokens (tokens older than 30 minutes and not used).'

    def handle(self, *args, **options):
        cutoff = timezone.now() - timedelta(minutes=30)
        expired = RegistrationRequest.objects.filter(
            token_created_at__lt=cutoff,
            is_used=False,
            status='approved',
        )
        count = expired.count()
        expired.delete()
        self.stdout.write(self.style.SUCCESS(f'Deleted {count} expired tokens.'))