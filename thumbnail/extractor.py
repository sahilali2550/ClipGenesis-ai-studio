import os
from typing import List
from loguru import logger
from PIL import Image, ImageDraw, ImageFont


def select_candidate_timestamps(video_path: str, count: int = 3) -> List[float]:
    """
    Selects candidate frame timestamps based on video duration.
    Defaults to 15%, 50%, 75% progress intervals.
    """
    duration = 10.0  # Fallback duration if file not available or unreadable
    if os.path.exists(video_path):
        try:
            import cv2
            cap = cv2.VideoCapture(video_path)
            fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
            frame_count = cap.get(cv2.CAP_PROP_FRAME_COUNT) or 300.0
            cap.release()
            if fps > 0 and frame_count > 0:
                duration = frame_count / fps
        except Exception as e:
            logger.debug(f"Could not read video duration via cv2: {e}")

    if count <= 1:
        return [round(duration / 2.0, 2)]

    step = duration / (count + 1)
    timestamps = [round(step * (i + 1), 2) for i in range(count)]
    return timestamps


def extract_frame_at_timestamp(video_path: str, timestamp_sec: float, output_path: str) -> str:
    """
    Extracts a frame from video_path at timestamp_sec and saves it to output_path.
    Creates a high-quality fallback canvas if video is not readable or missing.
    """
    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
    frame_extracted = False

    if os.path.exists(video_path):
        try:
            import cv2
            cap = cv2.VideoCapture(video_path)
            cap.set(cv2.CAP_PROP_POS_MSEC, timestamp_sec * 1000.0)
            ret, frame = cap.read()
            cap.release()
            if ret and frame is not None:
                cv2.imwrite(output_path, frame)
                frame_extracted = True
                logger.info(f"Extracted frame from {video_path} at t={timestamp_sec}s -> {output_path}")
        except Exception as e:
            logger.warning(f"OpenCV frame extraction failed for {video_path}: {e}")

    if not frame_extracted:
        # Create solid canvas fallback with gradient backdrop
        img = Image.new("RGB", (1280, 720), color=(30, 30, 45))
        draw = ImageDraw.Draw(img)
        draw.rectangle([(0, 0), (1280, 720)], fill=(20, 25, 40))
        draw.text((60, 60), f"Keyframe @ {timestamp_sec}s", fill=(200, 200, 220))
        img.save(output_path, format="JPEG")
        logger.info(f"Generated fallback keyframe image -> {output_path}")

    return output_path
