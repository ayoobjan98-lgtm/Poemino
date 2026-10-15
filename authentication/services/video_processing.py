import os
import tempfile
import logging

import cv2

logger = logging.getLogger(__name__)


def extract_frames(video_path, num_frames=5):
    """
    Extract evenly spaced frames from video.
    Returns (frames list of image paths, temp_dir).
    Caller must delete temp_dir after use.
    """
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        raise ValueError("Cannot open video file.")

    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    if total_frames == 0:
        cap.release()
        raise ValueError("Video has no frames.")

    indices = [int(i * total_frames / (num_frames + 1)) for i in range(1, num_frames + 1)]
    temp_dir = tempfile.mkdtemp()
    frames = []
    for i, idx in enumerate(indices):
        cap.set(cv2.CAP_PROP_POS_FRAMES, idx)
        ret, frame = cap.read()
        if ret:
            path = os.path.join(temp_dir, f'frame_{i}.jpg')
            cv2.imwrite(path, frame)
            frames.append(path)
    cap.release()
    return frames, temp_dir


def delete_temp_dir(temp_dir):
    import shutil
    if os.path.exists(temp_dir):
        shutil.rmtree(temp_dir, ignore_errors=True)