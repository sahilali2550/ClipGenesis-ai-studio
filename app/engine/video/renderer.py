"""
Renderer Module (Native FFmpeg / MoviePy Export)
"""
from loguru import logger
from app.services import video as legacy_video


def render_final_video(
    video_path: str,
    audio_path: str,
    subtitle_path: str,
    output_file: str,
    params=None,
    video_script: str = "",
) -> str:
    """
    Renders final video output using MoviePy/FFmpeg pipeline.
    """
    logger.info(f"Rendering final output video to {output_file}")
    return legacy_video.generate_video(
        video_path=video_path,
        audio_path=audio_path,
        subtitle_path=subtitle_path,
        output_file=output_file,
        params=params,
        video_script=video_script,
    )
