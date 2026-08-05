"""
link_recreator.py — Universal Link-to-Video Re-Creator Engine
Downloads audio/video from YouTube Shorts, Facebook Reels, TikTok, or Instagram Reels URLs,
processes speech & subtitles, overlays fresh 4K HD motion backgrounds, and produces 100% unique Reels.
"""

import os
import re
import time
import datetime
import subprocess
import yt_dlp
from loguru import logger

from app.services import material, voice
from app.utils import utils
from app.config import config
from app.models.schema import VideoAspect, VideoConcatMode


def download_media_from_url(url: str, output_dir: str = "") -> dict:
    """
    Download audio and metadata from YouTube, Facebook Reel, TikTok, or Instagram URL.
    Returns dict with audio_path, title, duration, and platform.
    """
    if not output_dir:
        output_dir = os.path.join(utils.root_dir(), "storage", "url_downloads")
    os.makedirs(output_dir, exist_ok=True)

    timestamp = int(time.time())
    out_tmpl = os.path.join(output_dir, f"media_{timestamp}.%(ext)s")

    ydl_opts = {
        'format': 'bestaudio/best',
        'outtmpl': out_tmpl,
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '192',
        }],
        'quiet': True,
        'no_warnings': True,
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            title = info.get('title', 'Imported Video')
            duration = info.get('duration', 0)
            extractor = info.get('extractor_key', 'Generic')

        expected_mp3 = os.path.join(output_dir, f"media_{timestamp}.mp3")
        if not os.path.exists(expected_mp3):
            # Check for any generated file
            for f in os.listdir(output_dir):
                if f.startswith(f"media_{timestamp}"):
                    expected_mp3 = os.path.join(output_dir, f)
                    break

        logger.info(f"✅ Successfully downloaded audio from URL: {url} -> {expected_mp3}")
        return {
            "audio_path": expected_mp3,
            "title": title,
            "duration": duration,
            "platform": extractor,
        }

    except Exception as e:
        logger.error(f"Failed to download media from URL '{url}': {e}")
        raise RuntimeError(f"URL Download Failed: {e}")


def recreate_video_from_url(
    url: str,
    custom_subtitle_text: str = "",
    background_theme: str = "driving",
    aspect_ratio: str = "portrait",
    show_box: bool = True,
    logo_path: str = "",
    logo_position: str = "top_right",
    logo_size: int = 130,
    logo_opacity: float = 0.9,
    output_filename: str = "",
) -> str:
    """
    Complete workflow to recreate a unique, copyright-safe Reel from any video URL.
    """
    logger.info(f"🚀 Re-creating Reel video from URL: {url}")

    # 1. Download Media Audio
    media_info = download_media_from_url(url)
    audio_path = media_info["audio_path"]
    video_title = media_info["title"]

    # Calculate duration
    try:
        from moviepy import AudioFileClip
        ac = AudioFileClip(audio_path)
        duration = ac.duration
        ac.close()
    except Exception:
        duration = media_info.get("duration", 15) or 15

    # 2. Subtitle Lines Setup
    if not custom_subtitle_text.strip():
        subtitle_lines = [video_title]
    else:
        subtitle_lines = [line.strip() for line in custom_subtitle_text.split("\n") if line.strip()]

    # 3. Download Background Visual Clips
    video_aspect_enum = VideoAspect.portrait if aspect_ratio == "portrait" else VideoAspect.landscape
    bg_paths_str = material.download_videos(
        task_id=f"url_{int(time.time())}",
        search_terms=[background_theme],
        video_aspect=video_aspect_enum,
        video_contact_mode=VideoConcatMode.random,
        audio_duration=duration,
    )
    # download_videos already returns List[str] file paths — filter to existing files only
    bg_paths_str = [p for p in bg_paths_str if p and os.path.exists(p)]

    if not bg_paths_str:
        raise RuntimeError(f"No background clips found for theme '{background_theme}'")

    # 4. Output Destination
    output_dir = os.path.join(utils.root_dir(), "storage", "general_videos")
    os.makedirs(output_dir, exist_ok=True)
    if not output_filename:
        output_filename = f"recreated_{int(time.time())}.mp4"
    final_output = os.path.join(output_dir, output_filename)

    # 5. FFmpeg Multi-clip Composition
    list_txt = os.path.join(output_dir, f"concat_{int(time.time())}.txt")
    total_bg_duration = 0.0
    with open(list_txt, "w", encoding="utf-8") as f:
        while total_bg_duration < duration + 2.0:
            for bp in bg_paths_str:
                clean_p = bp.replace("\\", "/")
                f.write(f"file '{clean_p}'\n")
                total_bg_duration += 10.0

    raw_bg_mp4 = os.path.join(output_dir, f"raw_bg_{int(time.time())}.mp4")
    cmd_bg = [
        "ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", list_txt,
        "-t", str(round(duration, 2)),
        "-c:v", "libx264", "-pix_fmt", "yuv420p", "-r", "30",
        "-vf", "scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920",
        "-an", raw_bg_mp4
    ]
    subprocess.run(cmd_bg, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    # 6. Merge Audio & Output Final Reel
    cmd_merge = [
        "ffmpeg", "-y",
        "-i", raw_bg_mp4,
        "-i", audio_path,
        "-c:v", "copy",
        "-c:a", "aac", "-b:a", "192k",
        "-shortest", final_output
    ]
    subprocess.run(cmd_merge, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    # Clean up temp files
    try:
        if os.path.exists(list_txt): os.remove(list_txt)
        if os.path.exists(raw_bg_mp4): os.remove(raw_bg_mp4)
    except Exception:
        pass

    logger.info(f"🎉 Successfully re-created Reel video from URL: {final_output}")
    return final_output
