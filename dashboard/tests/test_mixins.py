from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import timedelta

from authentication.models import DashboardAccessRecord

User = get_user_model()


class DashboardEntryFlowTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='approved', email='approved@example.com', password='password'
        )
        self.user.is_page_permitted = True
        self.user.save()

    def test_anonymous_redirects_to_login(self):
        response = self.client.get(reverse('dashboard:index'))
        self.assertRedirects(response, f"{reverse('login')}?next={reverse('dashboard:index')}")

    def test_authorized_user_without_access_record_redirects_to_verification(self):
        self.client.login(username='approved', password='password')
        response = self.client.get(reverse('dashboard:index'))
        self.assertRedirects(response, reverse('authentication:video_verify'))

    def test_authorized_user_with_valid_access_record_gets_dashboard(self):
        DashboardAccessRecord.create_for_user(self.user)
        self.client.login(username='approved', password='password')
        response = self.client.get(reverse('dashboard:index'))
        self.assertEqual(response.status_code, 200)
        # Optionally assert template used

    def test_authorized_user_with_expired_record_redirects_to_verification(self):
        record = DashboardAccessRecord.create_for_user(self.user)
        record.expires_at = timezone.now() - timedelta(days=1)
        record.save()
        self.client.login(username='approved', password='password')
        response = self.client.get(reverse('dashboard:index'))
        self.assertRedirects(response, reverse('authentication:video_verify'))

    def test_user_b_does_not_inherit_user_a_access(self):
        user_a = self.user
        DashboardAccessRecord.create_for_user(user_a)
        user_b = User.objects.create_user(username='user_b', password='password')
        user_b.is_page_permitted = True
        user_b.save()
        self.client.login(username='user_b', password='password')
        response = self.client.get(reverse('dashboard:index'))
        self.assertRedirects(response, reverse('authentication:video_verify'))