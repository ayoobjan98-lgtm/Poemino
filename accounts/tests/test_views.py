from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from unittest.mock import patch
from django.core.files.uploadedfile import SimpleUploadedFile
import numpy as np

User = get_user_model()


class SignUpViewTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.url = reverse('signup')

    @patch('cv2.imdecode')  # ← mock the function the view actually calls
    @patch('accounts.views.detect_faces')
    @patch('accounts.views.extract_face_feature')
    @patch('accounts.views.embed_to_json')
    def test_registration_creates_user_and_face_reference(
        self, mock_embed, mock_extract, mock_detect, mock_imdecode
    ):
        # Return a dummy image instead of trying to decode a real file.
        dummy_img = np.zeros((100, 100, 3), dtype=np.uint8)
        mock_imdecode.return_value = dummy_img

        mock_detect.return_value = [{'bbox': (0, 0, 100, 100), 'score': 0.9}]
        mock_extract.return_value = [0.1, 0.2, 0.3]
        mock_embed.return_value = '[0.1, 0.2, 0.3]'

        image = SimpleUploadedFile("face.jpg", b"dummy", content_type="image/jpeg")
        response = self.client.post(self.url, {
            'username': 'newuser',
            'email': 'new@example.com',
            'password1': 'Str0ngPass!',
            'password2': 'Str0ngPass!',
            'face_image': image,
        })

        self.assertEqual(response.status_code, 302)
        user = User.objects.get(username='newuser')
        from authentication.models import FaceReference
        self.assertTrue(FaceReference.objects.filter(user=user).exists())

    @patch('cv2.imdecode')
    @patch('accounts.views.detect_faces')
    def test_registration_with_no_face_rolls_back_user(self, mock_detect, mock_imdecode):
        dummy_img = np.zeros((100, 100, 3), dtype=np.uint8)
        mock_imdecode.return_value = dummy_img
        mock_detect.return_value = []  # no face

        image = SimpleUploadedFile("face.jpg", b"dummy", content_type="image/jpeg")
        response = self.client.post(self.url, {
            'username': 'baduser',
            'email': 'bad@example.com',
            'password1': 'Str0ngPass!',
            'password2': 'Str0ngPass!',
            'face_image': image,
        })
        self.assertEqual(response.status_code, 200)
        self.assertFalse(User.objects.filter(username='baduser').exists())


class LoginViewTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='approveduser', email='approved@example.com', password='Str0ngPass!'
        )
        self.user.is_page_permitted = True
        self.user.save()

    def test_approved_user_redirects_to_verification(self):
        response = self.client.post(reverse('login'), {
            'username': 'approveduser',
            'password': 'Str0ngPass!',
        })
        self.assertRedirects(response, reverse('authentication:video_verify'))

    def test_normal_user_redirects_to_home(self):
        User.objects.create_user(
            username='normaluser', email='normal@example.com', password='Str0ngPass!'
        )
        response = self.client.post(reverse('login'), {
            'username': 'normaluser',
            'password': 'Str0ngPass!',
        })
        self.assertRedirects(response, reverse('MakePoem:home'))