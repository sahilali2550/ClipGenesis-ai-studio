"""
Video Pipeline High-Level Orchestrator
"""
from typing import List, Tuple
from loguru import logger
from app.engine.video.composer import combine_video_clips
from app.engine.video.renderer import render_final_video


class VideoPipeline:
    """
    Production-grade video generation pipeline.
    """

    def __init__(self, task_id: str, params=None):
        self.task_id = task_id
        self.params = params

    def combine_and_render(
        self,
        downloaded_videos: List[str],
        audio_file: str,
        subtitle_path: str,
        video_script: str = "",
    ) -> Tuple[List[str], List[str]]:
        """
        Executes combination and final rendering stages.
        """
        from app.services import task as tm
        logger.info(f"VideoPipeline executing for task {self.task_id}")
        return tm.generate_final_videos(
            task_id=self.task_id,
            params=self.params,
            downloaded_videos=downloaded_videos,
            audio_file=audio_file,
            subtitle_path=subtitle_path,
            video_script=video_script,
        )
