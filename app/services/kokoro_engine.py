import os
import sys
import json
import urllib.request
import numpy as np
from loguru import logger

# Import soundfile and kokoro_onnx safely
try:
    import soundfile as sf
    SOUNDFILE_AVAILABLE = True
except ImportError:
    SOUNDFILE_AVAILABLE = False

try:
    from kokoro_onnx import Kokoro
    KOKORO_AVAILABLE = True
except ImportError:
    KOKORO_AVAILABLE = False

KOKORO_MODEL_URL = "https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/kokoro-v1.0.onnx"
KOKORO_VOICES_URL = "https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/voices-v1.0.bin"

KOKORO_VOICES = [
    ("af_heart", "English Female - Heart (Premium)"),
    ("af_bella", "English Female - Bella"),
    ("af_nicole", "English Female - Nicole"),
    ("af_sarah", "English Female - Sarah"),
    ("af_sky", "English Female - Sky"),
    ("am_adam", "English Male - Adam"),
    ("am_michael", "English Male - Michael"),
    ("am_echo", "English Male - Echo"),
    ("am_eric", "English Male - Eric"),
    ("bm_george", "British Male - George"),
    ("bf_emma", "British Female - Emma"),
]

# Global cached Kokoro instance
_kokoro_instance = None


def get_kokoro_models_dir() -> str:
    """Get or create local storage path for Kokoro models."""
    root_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.realpath(__file__))))
    models_dir = os.path.join(root_dir, "storage", "models", "kokoro")
    os.makedirs(models_dir, exist_ok=True)
    return models_dir


def download_file_with_progress(url: str, dest_path: str, description: str):
    import requests
    logger.info(f"Downloading {description} to {dest_path}...")
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
    response = requests.get(url, headers=headers, stream=True)
    response.raise_for_status()
    with open(dest_path, "wb") as f:
        for chunk in response.iter_content(chunk_size=8192):
            if chunk:
                f.write(chunk)
    logger.success(f"Downloaded {description} successfully.")


def ensure_kokoro_files_downloaded() -> tuple[str, str]:
    """Download Kokoro ONNX model and voices file lazily if not present."""
    models_dir = get_kokoro_models_dir()
    model_path = os.path.join(models_dir, "kokoro-v1.0.onnx")
    voices_path = os.path.join(models_dir, "voices-v1.0.bin")

    if not os.path.exists(model_path):
        download_file_with_progress(KOKORO_MODEL_URL, model_path, "Kokoro-82M ONNX model")

    if not os.path.exists(voices_path):
        download_file_with_progress(KOKORO_VOICES_URL, voices_path, "Kokoro voices file")

    return model_path, voices_path


def get_kokoro_instance():
    """Lazy initialize global Kokoro TTS engine instance."""
    global _kokoro_instance
    if _kokoro_instance is None:
        if not KOKORO_AVAILABLE:
            raise RuntimeError("kokoro-onnx is not installed.")
        model_path, voices_path = ensure_kokoro_files_downloaded()
        logger.info("Loading Kokoro-82M ONNX engine into RAM...")
        _kokoro_instance = Kokoro(model_path, voices_path)
        logger.success("Kokoro-82M engine loaded.")
    return _kokoro_instance


def unload_kokoro_engine():
    """Free Kokoro instance from RAM to protect system memory."""
    global _kokoro_instance
    if _kokoro_instance is not None:
        _kokoro_instance = None
        import gc
        gc.collect()
        logger.info("Unloaded Kokoro engine from memory.")


def get_kokoro_voice_list() -> list[str]:
    """Return formatted voice IDs for Streamlit UI selectors."""
    return [f"kokoro:{v_id}:{name}" for v_id, name in KOKORO_VOICES]


def generate_kokoro_tts(
    text: str,
    voice_id: str,
    speed: float = 1.0,
    output_file: str = "output.mp3",
):
    """
    Generate audio using Kokoro-82M ONNX model and return SubMaker-compatible timing.
    """
    if not KOKORO_AVAILABLE or not SOUNDFILE_AVAILABLE:
        logger.error("Kokoro-ONNX or SoundFile is missing.")
        return None

    # Parse voice ID e.g. kokoro:af_heart:English Female - Heart
    if voice_id.startswith("kokoro:"):
        parts = voice_id.split(":")
        voice_key = parts[1] if len(parts) > 1 else "af_heart"
    else:
        voice_key = voice_id

    kokoro = get_kokoro_instance()
    
    logger.info(f"Generating Kokoro-82M TTS audio for voice: {voice_key}, text length: {len(text)} chars")
    
    # Chunk text to avoid 510 phoneme limit
    import re
    chunks = [c.strip() for c in re.split(r'(?<=[.!?\n])\s+', text) if c.strip()]
    if not chunks:
        chunks = [text]

    all_samples = []
    sample_rate = 24000

    for chunk in chunks:
        try:
            samples, sr = kokoro.create(chunk, voice=voice_key, speed=speed, lang="en-us")
            all_samples.append(samples)
            sample_rate = sr
        except Exception as e:
            logger.warning(f"Kokoro chunk synthesis skipped for '{chunk[:30]}...': {e}")

    if not all_samples:
        return None

    combined_samples = np.concatenate(all_samples)
    sf.write(output_file, combined_samples, sample_rate)
    duration_sec = len(combined_samples) / float(sample_rate)
    logger.success(f"Kokoro audio generated: {output_file} (duration: {duration_sec:.2f}s)")
    
    # Create SubMaker timestamp structure
    from app.services.voice import ensure_submaker_compatibility
    try:
        from edge_tts import SubMaker
        sub_maker = ensure_submaker_compatibility(SubMaker())
    except Exception:
        class SubMakerFallback:
            def __init__(self):
                self.subs = []
                self.offset = []
        sub_maker = SubMakerFallback()
    
    words = text.strip().split()
    if not words:
        return sub_maker
        
    total_100ns = int(duration_sec * 10_000_000)
    per_word_100ns = total_100ns // len(words)
    
    curr = 0
    for idx, w in enumerate(words):
        end = curr + per_word_100ns if idx < len(words) - 1 else total_100ns
        sub_maker.subs.append(w)
        sub_maker.offset.append((curr, end))
        curr = end
        
    return sub_maker
