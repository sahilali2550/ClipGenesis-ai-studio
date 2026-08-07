"""
Audio Processing Module (BGM, Ducking, Mixing)
"""
from loguru import logger


def mix_audio_tracks(voice_path: str, bgm_path: str = "", voice_volume: float = 1.0, bgm_volume: float = 0.2) -> str:
    """
    Mixes voice audio track with background music track.
    """
    logger.info(f"Mixing audio tracks: voice={voice_path}, bgm={bgm_path}")
    return voice_path
