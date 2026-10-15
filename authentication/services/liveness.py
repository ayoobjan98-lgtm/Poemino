import cv2
import numpy as np
import logging

logger = logging.getLogger(__name__)


def detect_liveness(frames, threshold=1.5):
    """
    Lightweight liveness detection based on inter‑frame movement.
    `frames` is a list of image file paths.
    Returns (bool, avg_diff). If avg_diff <= threshold, likely a static
    photograph or replay, not a live person.
    """
    if len(frames) < 2:
        return False, 0.0

    diffs = []
    for i in range(1, len(frames)):
        img1 = cv2.imread(frames[i-1], cv2.IMREAD_GRAYSCALE)
        img2 = cv2.imread(frames[i], cv2.IMREAD_GRAYSCALE)
        if img1 is None or img2 is None:
            continue
        diff = cv2.absdiff(img1, img2)
        diffs.append(float(np.mean(diff)))

    if not diffs:
        return False, 0.0

    avg_diff = sum(diffs) / len(diffs)
    logger.info("Liveness avg diff: %.2f", avg_diff)
    return avg_diff > threshold, avg_diff