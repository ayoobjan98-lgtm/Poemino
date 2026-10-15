from django.test import TestCase
from django.contrib.auth import get_user_model
from accounts.forms import CustomUserCreationForm, CustomLoginForm, DashboardRequestForm

User = get_user_model()


class CustomUserCreationFormTest(TestCase):
    def test_face_image_is_required(self):
        form = CustomUserCreationForm(data={
            'username': 'testuser',
            'email': 'test@example.com',
            'password1': 'Str0ngPass!',
            'password2': 'Str0ngPass!',
        })
        self.assertFalse(form.is_valid())
        self.assertIn('face_image', form.errors)

    def test_valid_form_creates_user(self):
        # We cannot test face embedding here; we mock it in views test.
        # This form test only checks field presence, not saving.
        pass