import numpy as np
from django.test import TestCase, override_settings
from django.contrib.auth import get_user_model
from authentication.models import FaceReference
from authentication.services.face_verification import (
    find_duplicate_face_for_new_user,
    embed_to_json,
    _normalize,
)

User = get_user_model()


class FindDuplicateFaceForNewUserTest(TestCase):
    def setUp(self):
        self.user_a = User.objects.create_user(username='user_a')
        self.user_b = User.objects.create_user(username='user_b')

        # Create two distinct face embeddings (normalized 3D vectors)
        self.embedding_a = np.array([1.0, 0.0, 0.0])
        self.embedding_b = np.array([0.0, 1.0, 0.0])

        FaceReference.objects.create(
            user=self.user_a,
            image='face_a.jpg',
            embedding=embed_to_json(self.embedding_a),
        )
        FaceReference.objects.create(
            user=self.user_b,
            image='face_b.jpg',
            embedding=embed_to_json(self.embedding_b),
        )

    @override_settings(FACE_DUPLICATE_THRESHOLD=0.85)
    def test_duplicate_face_found_for_user_a(self):
        # Feature very close to user_a's embedding
        feature = self.embedding_a + np.array([0.01, 0.0, 0.0])
        duplicate_ref = find_duplicate_face_for_new_user(feature)
        self.assertIsNotNone(duplicate_ref)
        self.assertEqual(duplicate_ref.user, self.user_a)

    @override_settings(FACE_DUPLICATE_THRESHOLD=0.85)
    def test_duplicate_face_found_for_user_b(self):
        feature = self.embedding_b + np.array([0.0, 0.01, 0.0])
        duplicate_ref = find_duplicate_face_for_new_user(feature)
        self.assertIsNotNone(duplicate_ref)
        self.assertEqual(duplicate_ref.user, self.user_b)

    @override_settings(FACE_DUPLICATE_THRESHOLD=0.85)
    def test_no_duplicate_for_different_face(self):
        # Feature far from both existing embeddings
        feature = np.array([0.0, 0.0, 1.0])
        duplicate_ref = find_duplicate_face_for_new_user(feature)
        self.assertIsNone(duplicate_ref)