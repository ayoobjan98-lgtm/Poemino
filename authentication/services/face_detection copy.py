import os
import logging
from pathlib import Path

import cv2

from django.conf import settings

logger = logging.getLogger(__name__)

_detector = None


def _get_model_path():
    """
    Return the absolute path to the YuNet face detector model.

    1. If settings.AUTH_FACE_DETECTOR_PATH is set, use it.
       - If absolute, return as-is.
       - If relative, resolve from BASE_DIR.
    2. Otherwise use the project default:
       <BASE_DIR>/models/face_detection_yunet_2026may.onnx
    """
    configured = getattr(settings, 'AUTH_FACE_DETECTOR_PATH', None)

    if configured:
        path = Path(configured)
        if path.is_absolute():
            return str(path)
        return str(Path(settings.BASE_DIR) / path)

    return str(Path(settings.BASE_DIR) / "models" / "face_detection_yunet_2026may.onnx")


def get_face_detector():
    """
    Load and cache the YuNet face detector.
    """
    global _detector

    if _detector is None:
        model_path = _get_model_path()

        if not os.path.exists(model_path):
            logger.error("YuNet model not found at %s", model_path)
            raise FileNotFoundError(f"YuNet model not found at {model_path}")

        _detector = cv2.FaceDetectorYN.create(
            model_path,
            "",
            (320, 320),
            score_threshold=0.6,
            nms_threshold=0.3,
        )
        logger.info("Loaded YuNet face detector from %s", model_path)

    return _detector


def detect_faces(image):
    detector = get_face_detector()

    h, w = image.shape[:2]
    detector.setInputSize((w, h))

    result = detector.detect(image)

    print("=== YuNet DEBUG ===")
    print("type:", type(result))
    print("len:", len(result) if hasattr(result, "__len__") else "N/A")
    print("result:", result)
    print("===================")

    _, faces = result

    results = []

    if faces is not None:
        for face in faces:
            x, y, w, h = face[:4]
            score = face[-1]

            results.append({
                'bbox': (int(x), int(y), int(w), int(h)),
                'score': float(score),
            })

    return results