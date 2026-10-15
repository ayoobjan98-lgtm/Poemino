import os
import json
import logging
from pathlib import Path

import cv2
import numpy as np

from django.conf import settings
from authentication.models import FaceReference

logger = logging.getLogger(__name__)

_recognizer = None


def _get_model_path():
    configured = getattr(settings, 'AUTH_FACE_RECOGNIZER_PATH', None)
    if configured:
        path = Path(configured)
        return str(path) if path.is_absolute() else str(Path(settings.BASE_DIR) / path)
    return str(Path(settings.BASE_DIR) / "models" / "face_recognition_sface_2021dec.onnx")


def get_face_recognizer():
    global _recognizer
    if _recognizer is None:
        model_path = _get_model_path()
        if not os.path.exists(model_path):
            raise FileNotFoundError(f"SFace model not found at {model_path}")
        _recognizer = cv2.FaceRecognizerSF.create(model_path, "")
    return _recognizer


def _normalize(feature):
    arr = np.asarray(feature).flatten().astype(np.float32)
    norm = np.linalg.norm(arr)
    return arr / norm if norm > 0 else arr


def extract_face_feature(image, face_bbox):
    recognizer = get_face_recognizer()
    x, y, w, h = face_bbox
    aligned = recognizer.alignCrop(image, (x, y, w, h))
    feat = recognizer.feature(aligned)
    return _normalize(feat)


def compare_features(feature1, feature2):
    return float(np.dot(_normalize(feature1), _normalize(feature2)))


def check_duplicate_face(user, feature):
    """
    Return True if `feature` matches any FaceReference belonging to another user.
    """
    threshold = getattr(settings, 'FACE_DUPLICATE_THRESHOLD', 0.85)
    target = _normalize(feature)

    other_refs = FaceReference.objects.exclude(user=user)

    for ref in other_refs:
        stored = embed_from_json(ref.embedding)
        stored = _normalize(stored)

        similarity = compare_features(target, stored)

        if similarity >= threshold:
            return True

    return False


def find_duplicate_face_for_new_user(feature):
    """
    Return a FaceReference that matches the given feature, or None.

    This is used during registration before a new FaceReference is created.
    It compares against ALL existing FaceReference records.
    """
    threshold = getattr(settings, 'FACE_DUPLICATE_THRESHOLD', 0.85)
    target = _normalize(feature)

    for ref in FaceReference.objects.all():
        stored = embed_from_json(ref.embedding)
        stored = _normalize(stored)

        similarity = compare_features(target, stored)

        if similarity >= threshold:
            return ref

    return None


def embed_to_json(feature):
    return json.dumps(_normalize(feature).tolist())


def embed_from_json(json_str):
    arr = np.array(json.loads(json_str), dtype=np.float32)
    return _normalize(arr)