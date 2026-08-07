import os
import glob
from typing import List, Optional
from PIL import Image
from loguru import logger
from app.utils import utils
from assets.schemas import AssetItem
from assets.database.db import register_asset


IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".webp", ".bmp"}
VIDEO_EXTS = {".mp4", ".mov", ".avi", ".mkv", ".webm"}
AUDIO_EXTS = {".mp3", ".wav", ".aac", ".flac", ".ogg", ".m4a"}


def get_asset_type(filepath: str) -> str:
    ext = os.path.splitext(filepath)[1].lower()
    if ext in IMAGE_EXTS:
        return "image"
    elif ext in VIDEO_EXTS:
        return "video"
    elif ext in AUDIO_EXTS:
        return "audio"
    return "unknown"


def extract_metadata(filepath: str) -> AssetItem:
    """Extracts width, height, duration, format metadata from media file."""
    filename = os.path.basename(filepath)
    ext = os.path.splitext(filename)[1].lower().replace(".", "")
    atype = get_asset_type(filepath)

    width, height, duration = 0, 0, 0.0

    if atype == "image":
        try:
            with Image.open(filepath) as img:
                width, height = img.size
        except Exception:
            pass
    elif atype == "video":
        try:
            # Quick OpenCV or PIL probe for video header
            import cv2
            cap = cv2.VideoCapture(filepath)
            if cap.isOpened():
                width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
                height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
                fps = cap.get(cv2.CAP_PROP_FPS)
                frame_count = cap.get(cv2.CAP_PROP_FRAME_COUNT)
                if fps > 0:
                    duration = round(frame_count / fps, 2)
                cap.release()
        except Exception:
            pass
    elif atype == "audio":
        try:
            import wave
            if ext == "wav":
                with wave.open(filepath, "rb") as wf:
                    frames = wf.getnframes()
                    rate = wf.getframerate()
                    duration = round(frames / float(rate), 2)
        except Exception:
            pass

    return AssetItem(
        filename=filename,
        path=filepath,
        type=atype if atype != "unknown" else "image",
        category="scanned",
        tags=[atype, ext],
        duration=duration,
        width=width,
        height=height,
        format=ext
    )


def scan_directory(dir_path: str) -> List[AssetItem]:
    """Scans directory for media assets and registers them into SQLite db."""
    registered = []
    if not os.path.exists(dir_path):
        return registered

    for root, _, files in os.walk(dir_path):
        for f in files:
            fpath = os.path.join(root, f)
            atype = get_asset_type(fpath)
            if atype != "unknown":
                try:
                    item = extract_metadata(fpath)
                    saved = register_asset(item)
                    registered.append(saved)
                except Exception as e:
                    logger.warning(f"Error registering scanned asset {fpath}: {e}")

    logger.info(f"Asset Library scan complete for {dir_path}: {len(registered)} assets registered.")
    return registered
