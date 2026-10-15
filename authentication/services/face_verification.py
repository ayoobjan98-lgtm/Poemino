import os
import json
import logging
from pathlib import Path

import cv2
import numpy as np

from django.conf import settings
from django.core.exceptions import ObjectDoesNotExist

from authentication.models import FaceReference

logger = logging.getLogger(__name__)

_recognizer = None


# ---------------------------------------------------------------------------
# Model path resolution
# ---------------------------------------------------------------------------

def _get_model_path():
    """
    Return the absolute path to the SFace model.

    1. If settings.AUTH_FACE_RECOGNIZER_PATH is set, use it.
       - Absolute path is used as-is.
       - Relative path is resolved from settings.BASE_DIR.
    2. Otherwise use the project default:
       <BASE_DIR>/models/face_recognition_sface_2021dec.onnx
    """
    configured = getattr(settings, 'AUTH_FACE_RECOGNIZER_PATH', None)

    if configured:
        path = Path(configured)
        if path.is_absolute():
            return str(path)
        return str(Path(settings.BASE_DIR) / path)

    return str(
        Path(settings.BASE_DIR)
        / "models"
        / "face_recognition_sface_2021dec.onnx"
    )


# ---------------------------------------------------------------------------
# SFace recognizer (loaded once, cached)
# ---------------------------------------------------------------------------

def get_face_recognizer():
    """
    Load and cache the SFace recognizer.
    """
    global _recognizer

    if _recognizer is None:
        model_path = _get_model_path()

        if not os.path.exists(model_path):
            logger.error("SFace model not found at %s", model_path)
            raise FileNotFoundError(f"SFace model not found at {model_path}")

        _recognizer = cv2.FaceRecognizerSF.create(model_path, "")
        logger.info("Loaded SFace recognizer from %s", model_path)

    return _recognizer


# ---------------------------------------------------------------------------
# Vector normalization
# ---------------------------------------------------------------------------

def _normalize(feature):
    """
    Flatten and L2-normalize a feature vector.

    Prevents shape mismatches (e.g. (1, 128) vs (128,)). Returns the
    original array unchanged if the L2 norm is zero.
    """
    arr = np.asarray(feature).flatten().astype(np.float32)
    norm = np.linalg.norm(arr)
    if norm > 0:
        return arr / norm
    return arr


# ---------------------------------------------------------------------------
# Detection coercion
# ---------------------------------------------------------------------------

def _coerce_detection(face_detection):
    """
    Return a (1, N) float32 ndarray suitable for
    cv2.FaceRecognizerSF.alignCrop.

    Accepts:
      * the dict returned by detect_faces() — the full YuNet row is
        looked up under any of the keys 'yunet_detection', 'raw',
        'detection'
      * the raw YuNet row (np.ndarray or list of >= 15 floats)
      * a plain (x, y, w, h) tuple — rejected, because SFace needs the
        facial landmark points for alignment

    Raises ValueError with a clear message when a bbox-only tuple is
    passed in.
    """
    if isinstance(face_detection, dict):
        full_row = None
        for key in ('yunet_detection', 'raw', 'detection'):
            if key in face_detection and face_detection[key] is not None:
                full_row = face_detection[key]
                break
        if full_row is None:
            # Fall through to bbox; the length check will reject it and
            # produce a helpful message.
            full_row = face_detection.get('bbox')
        face_detection = full_row

    arr = np.asarray(face_detection, dtype=np.float32).flatten()

    if arr.size < 15:
        raise ValueError(
            "alignCrop requires the full YuNet detection row "
            "(>=15 values); received "
            f"{arr.size} value(s). Pass the dict returned by "
            "detect_faces(), or its 'yunet_detection' / 'raw' / "
            "'detection' field."
        )

    return arr.reshape(1, -1)


# ---------------------------------------------------------------------------
# Feature extraction
# ---------------------------------------------------------------------------

def extract_face_feature(image, face_detection):
    """
    Extract a normalized SFace feature for the given face.

    `face_detection` must be the full detection — either the dict from
    detect_faces() or the raw 15-value YuNet row. Passing only (x, y,
    w, h) raises ValueError because SFace alignment requires the
    landmark row.
    """
    recognizer = get_face_recognizer()
    detection = _coerce_detection(face_detection)
    aligned = recognizer.alignCrop(image, detection)
    feat = recognizer.feature(aligned)
    return _normalize(feat)


# ---------------------------------------------------------------------------
# Similarity
# ---------------------------------------------------------------------------

def compare_features(feature1, feature2):
    """
    Cosine similarity between two normalized feature vectors.
    """
    return float(np.dot(_normalize(feature1), _normalize(feature2)))


# ---------------------------------------------------------------------------
# FaceReference validity
# ---------------------------------------------------------------------------

def is_face_reference_valid(reference):
    """
    Return True only if the given FaceReference's owner account still
    exists in the database.

    A reference whose owner was deleted must never be treated as a valid
    identity. It must be skipped by every duplicate-detection and
    identity-verification path.

    Behaviour in the current project:
      * `user` is a non-nullable OneToOneField.
      * `select_related('user')` therefore emits an INNER JOIN, and
        orphaned rows are filtered out at the SQL level. In that case
        this helper is a no-op safeguard: every row we see already has
        a valid owner.
      * If the query strategy ever changes (no select_related, values()
        queries, deferred loads, or a future nullable FK), accessing
        `.user` on an orphaned row raises `ObjectDoesNotExist`. We catch
        that and correctly report the reference as invalid.

    The helper never mutates the reference and never issues an extra
    query for `select_related`-backed rows.
    """
    if reference is None:
        return False

    if reference.user_id is None:
        return False

    try:
        owner = reference.user
    except ObjectDoesNotExist:
        return False

    return owner is not None


# ---------------------------------------------------------------------------
# Duplicate detection
# ---------------------------------------------------------------------------

def check_duplicate_face(user, feature):
    """
    Return True if `feature` matches a FaceReference belonging to another
    existing user.

    - The current user's own reference is excluded (self-match preserved).
    - References whose owner account no longer exists are ignored.
    - Threshold comes from settings.FACE_DUPLICATE_THRESHOLD (default 0.6).
    """
    threshold = getattr(settings, 'FACE_DUPLICATE_THRESHOLD', 0.6)
    target = _normalize(feature)

    references = FaceReference.objects.select_related('user').all()

    for ref in references:
        # Skip the current user's own reference.
        if ref.user_id is None or ref.user_id == user.pk:
            continue

        # Skip stale references whose owner account no longer exists.
        if not is_face_reference_valid(ref):
            logger.info(
                "Ignoring stale FaceReference id=%s (user_id=%s missing).",
                ref.pk, ref.user_id,
            )
            continue

        try:
            stored = embed_from_json(ref.embedding)
        except (ValueError, TypeError, json.JSONDecodeError) as exc:
            logger.warning(
                "Skipping FaceReference id=%s — invalid embedding (%s).",
                ref.pk, exc,
            )
            continue

        similarity = compare_features(target, stored)

        logger.info(
            "[DUP] user=%s ref_id=%s owner=%s similarity=%.4f threshold=%.4f",
            user.username, ref.pk, ref.user.username, similarity, threshold,
        )

        if similarity >= threshold:
            return True

    return False


def find_duplicate_face_for_new_user(feature):
    """
    Return the first FaceReference whose owner still exists and whose
    embedding matches `feature` at or above the duplicate threshold.
    Return None otherwise.

    Stale references whose owner account no longer exists are ignored,
    so a deleted user's old face cannot block a new user's registration.
    """
    threshold = getattr(settings, 'FACE_DUPLICATE_THRESHOLD', 0.6)
    target = _normalize(feature)

    references = FaceReference.objects.select_related('user').all()

    for ref in references:
        if ref.user_id is None:
            continue

        if not is_face_reference_valid(ref):
            logger.info(
                "Ignoring stale FaceReference id=%s (user_id=%s missing).",
                ref.pk, ref.user_id,
            )
            continue

        try:
            stored = embed_from_json(ref.embedding)
        except (ValueError, TypeError, json.JSONDecodeError) as exc:
            logger.warning(
                "Skipping FaceReference id=%s — invalid embedding (%s).",
                ref.pk, exc,
            )
            continue

        similarity = compare_features(target, stored)

        logger.info(
            "[NEW-USER DUP] ref_id=%s owner=%s similarity=%.4f threshold=%.4f",
            ref.pk, ref.user.username, similarity, threshold,
        )

        if similarity >= threshold:
            return ref

    return None


# ---------------------------------------------------------------------------
# Embedding serialization
# ---------------------------------------------------------------------------

def embed_to_json(feature):
    """
    Serialize a normalized embedding as JSON for storage.
    """
    return json.dumps(_normalize(feature).tolist())


def embed_from_json(json_str):
    """
    Deserialize a stored embedding and normalize it.
    """
    arr = np.array(json.loads(json_str), dtype=np.float32)
    return _normalize(arr)