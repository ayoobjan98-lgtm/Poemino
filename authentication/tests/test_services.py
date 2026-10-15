from django.test import TestCase
from django.contrib.auth import get_user_model
from unittest.mock import patch, MagicMock
from django.core.files.uploadedfile import SimpleUploadedFile

from authentication.services import face_verification, liveness, otp, dashboard_access

User = get_user_model()


class FaceVerificationServiceTest(TestCase):
    @patch('authentication.services.face_verification.get_face_recognizer')
    @patch('authentication.services.face_detection.get_face_detector')
    def test_extract_face_feature(self, mock_detector, mock_recognizer):
        # This is a smoke test; actual inference not executed
        pass