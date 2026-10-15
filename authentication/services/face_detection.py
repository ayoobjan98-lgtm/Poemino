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

    return str(
        Path(settings.BASE_DIR)
        / "models"
        / "face_detection_yunet_2026may.onnx"
    )


def get_face_detector():
    """
    Load and cache the YuNet face detector.
    """
    global _detector

    if _detector is None:
        model_path = _get_model_path()

        if not os.path.exists(model_path):
            logger.error("YuNet model not found at %s", model_path)
            raise FileNotFoundError(
                f"YuNet model not found at {model_path}"
            )

        _detector = cv2.FaceDetectorYN.create(
            model_path,
            "",
            (320, 320),
            score_threshold=0.6,
            nms_threshold=0.3,
        )

        logger.info(
            "Loaded YuNet face detector from %s",
            model_path,
        )

    return _detector


def detect_faces(image):
    """
    Detect faces with YuNet.

    Returns a list of dictionaries containing:
    - bbox
    - landmarks
    - score
    """

    if image is None:
        return []

    detector = get_face_detector()

    height, width = image.shape[:2]

    detector.setInputSize((width, height))

    result = detector.detect(image)

    # YuNet/OpenCV returns:
    # (num_faces, detections)
    _, faces = result

    results = []

    if faces is None:
        return results

    for face in faces:
        if len(face) < 15:
            continue

        x, y, box_width, box_height = face[:4]

        # YuNet landmark order:
        # right eye
        # left eye
        # nose
        # right mouth corner
        # left mouth corner
        landmarks = face[4:14].reshape(5, 2)

        score = float(face[14])

        results.append({
            'bbox': (
                int(x),
                int(y),
                int(box_width),
                int(box_height),
            ),
            'landmarks': landmarks.astype(float).tolist(),
            'score': score,
            # Keep the original YuNet detection available for SFace.
            'yunet_detection': face.astype(float).tolist(),
        })

    return results