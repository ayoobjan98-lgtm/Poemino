from django.test import TestCase, Client, override_settings
from django.urls import reverse
from django.contrib.auth import get_user_model
from unittest.mock import patch
from django.core.files.uploadedfile import SimpleUploadedFile
import numpy as np

from authentication.models import FaceReference, DashboardAccessRecord

User = get_user_model()


class CompleteVerificationFlowTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='approved', email='approved@example.com', password='password'
        )
        self.user.is_page_permitted = True
        self.user.save()
        FaceReference.objects.create(
            user=self.user, image='ref.jpg', embedding='[0.1,0.2,0.3]'
        )

    @override_settings(FACE_MATCH_THRESHOLD=0.5)
    @patch('cv2.imread')
    @patch('authentication.views.extract_frames')
    @patch('authentication.views.extract_face_feature')
    @patch('authentication.views.detect_faces')
    @patch('authentication.views.compare_features', return_value=0.99)
    @patch('authentication.views.detect_liveness')
    @patch('authentication.views.create_otp_for_user')
    @patch('authentication.views.send_otp_email')
    def test_full_flow_grants_access_after_otp(
        self, mock_send, mock_create_otp, mock_liveness, mock_compare,
        mock_extract_face, mock_detect, mock_extract_frames, mock_imread
    ):
        mock_extract_frames.return_value = (['f1.jpg', 'f2.jpg'], '/tmp/frames')
        mock_imread.return_value = np.zeros((100, 100, 3), dtype=np.uint8)
        mock_detect.return_value = [{'bbox': (10, 10, 50, 50), 'score': 0.9}]
        mock_extract_face.return_value = [0.1, 0.2, 0.3]
        mock_liveness.return_value = (True, 2.5)
        mock_create_otp.return_value = '123456'

        self.client.login(username='approved', password='password')

        # 1. Dashboard redirects to verification
        response = self.client.get(reverse('dashboard:index'))
        self.assertRedirects(response, reverse('authentication:video_verify'))

        # 2. POST video -> success -> redirect to OTP
        video = SimpleUploadedFile("video.webm", b"fake", content_type="video/webm")
        response = self.client.post(reverse('authentication:video_verify'), {'video': video})
        self.assertRedirects(response, reverse('authentication:otp'))

        # 3. POST correct OTP -> redirect to dashboard
        response = self.client.post(reverse('authentication:otp'), {'otp': '123456'})
        self.assertRedirects(response, reverse('dashboard:index'))

        # 4. Dashboard now accessible
        response = self.client.get(reverse('dashboard:index'))
        self.assertEqual(response.status_code, 200)

        # 5. DashboardAccessRecord created
        self.assertTrue(DashboardAccessRecord.objects.filter(user=self.user).exists())