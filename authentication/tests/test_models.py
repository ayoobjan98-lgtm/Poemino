from django.test import TestCase
from django.utils import timezone
from datetime import timedelta
from django.contrib.auth import get_user_model
from django.contrib.auth.hashers import make_password, check_password

from authentication.models import (
    FaceReference, VerificationSession, OTPToken, DashboardAccessRecord
)

User = get_user_model()


class FaceReferenceTest(TestCase):
    def test_face_reference_unique_per_user(self):
        user = User.objects.create_user(username='user1')
        FaceReference.objects.create(user=user, image='img.jpg', embedding='[0.1]')
        with self.assertRaises(Exception):
            FaceReference.objects.create(user=user, image='img2.jpg', embedding='[0.2]')


class OTPTokenTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='otpuser', password='password')

    def test_otp_hash_not_plaintext(self):
        from authentication.services.otp import create_otp_for_user
        plain = create_otp_for_user(self.user)
        token = OTPToken.objects.get(user=self.user, is_used=False)
        self.assertNotEqual(token.otp_hash, plain)
        self.assertTrue(check_password(plain, token.otp_hash))

    def test_otp_single_use(self):
        from authentication.services.otp import create_otp_for_user, verify_otp
        plain = create_otp_for_user(self.user)
        self.assertTrue(verify_otp(self.user, plain)[0])
        self.assertFalse(verify_otp(self.user, plain)[0])  # reused

    def test_otp_expiration(self):
        token = OTPToken.objects.create(
            user=self.user, otp_hash='dummy', expires_at=timezone.now() - timedelta(minutes=1)
        )
        self.assertTrue(token.is_expired())

    def test_otp_attempt_limit(self):
        token = OTPToken.objects.create(
            user=self.user,
            otp_hash=make_password('123456'),
            expires_at=timezone.now() + timedelta(minutes=5)
        )
        for _ in range(5):
            token.verify_otp('000000')
        self.assertFalse(token.verify_otp('123456'))


class DashboardAccessRecordTest(TestCase):
    def setUp(self):
        self.user_a = User.objects.create_user(username='user_a')
        self.user_b = User.objects.create_user(username='user_b')

    def test_access_record_belongs_to_user_a(self):
        record = DashboardAccessRecord.create_for_user(self.user_a)
        self.assertEqual(record.user, self.user_a)
        self.assertTrue(record.expires_at > timezone.now())

    def test_user_b_has_no_access(self):
        DashboardAccessRecord.create_for_user(self.user_a)
        from authentication.services.dashboard_access import has_valid_dashboard_access
        self.assertFalse(has_valid_dashboard_access(self.user_b))

    def test_expired_record_not_valid(self):
        record = DashboardAccessRecord.create_for_user(self.user_a)
        record.expires_at = timezone.now() - timedelta(days=1)
        record.save()
        self.assertFalse(record.is_valid())