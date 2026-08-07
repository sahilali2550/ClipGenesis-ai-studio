"""
Video Composer Module (Concatenation & Timeline Assembly)
"""
from typing import List
from loguru import logger
from app.services import video as legacy_video


def combine_video_clips(
    combined_video_path: str,
    video_paths: List[str],
    audio_file: str,
    video_aspect,
    video_concat_mode,
    video_transition_mode,
    max_clip_duration: int = 5,
    threads: int = 2,
    script: str = "",
    params=None,
) -> str:
    """
    Combines video clips into a single continuous background video track.
    Delegates cleanly to underlying legacy video service to preserve 100% behavior.
    """
    logger.info(f"Combining {len(video_paths)} clips into {combined_video_path}")
    return legacy_video.combine_videos(
        combined_video_path=combined_video_path,
        video_paths=video_paths,
        audio_file=audio_file,
        video_aspect=video_aspect,
        video_concat_mode=video_concat_mode,
        video_transition_mode=video_transition_mode,
        max_clip_duration=max_clip_duration,
        threads=threads,
        script=script,
        params=params,
    )
