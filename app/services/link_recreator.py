"""
link_recreator.py — Universal Link-to-Video Re-Creator Engine
Downloads audio/video from YouTube Shorts, Facebook Reels, TikTok, or Instagram Reels URLs,
processes speech & subtitles, overlays fresh 4K HD motion backgrounds, and produces 100% unique Reels.
"""

import os
import re
import time
import textwrap
import subprocess
import yt_dlp
from loguru import logger

from app.services import material
from app.utils import utils
from app.config import config
from app.models.schema import VideoAspect, VideoConcatMode


# ── Helper: FFmpeg path / text escaping ─────────────────────────────────────

def _ffmpeg_font_path(path: str) -> str:
    """Convert absolute Windows path to FFmpeg drawtext-compatible path."""
    path = path.replace("\\", "/")
    # Escape the drive-letter colon:  C:/path  →  C\:/path
    if len(path) > 1 and path[1] == ":":
        path = path[0] + "\\:" + path[2:]
    return path


def _escape_drawtext(text: str) -> str:
    """Escape special characters for FFmpeg drawtext value."""
    text = text.replace("\\", "\\\\")
    text = text.replace("'",  "\\'")
    text = text.replace(":",  "\\:")
    text = text.replace("%",  "\\%")
    return text


def _wrap_text(text: str, max_chars: int = 28) -> list:
    """Split long subtitle line into multiple wrapped lines."""
    words = text.split()
    lines, current = [], ""
    for word in words:
        if len(current) + len(word) + (1 if current else 0) <= max_chars:
            current = (current + " " + word).strip()
        else:
            if current:
                lines.append(current)
            current = word
    if current:
        lines.append(current)
    return lines or [text]


# ── Step 1: Download audio + metadata (+ optional captions) ─────────────────

def download_media_from_url(url: str, output_dir: str = "") -> dict:
    """
    Download audio and metadata from YouTube, Facebook Reel, TikTok, or Instagram URL.
    Returns dict with audio_path, title, duration, platform, and captions (if available).
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
        # Try to fetch auto-generated subtitles/captions
        'writeautomaticsub': True,
        'subtitlesformat': 'vtt',
        'subtitleslangs': ['en', 'ur', 'ar'],
        'quiet': True,
        'no_warnings': True,
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            title    = info.get('title', 'Imported Video')
            duration = info.get('duration', 0)
            extractor = info.get('extractor_key', 'Generic')
            description = info.get('description', '')

        # Locate downloaded mp3
        expected_mp3 = os.path.join(output_dir, f"media_{timestamp}.mp3")
        if not os.path.exists(expected_mp3):
            for f in os.listdir(output_dir):
                if f.startswith(f"media_{timestamp}") and f.endswith(".mp3"):
                    expected_mp3 = os.path.join(output_dir, f)
                    break

        # Try to find VTT caption file
        caption_text = ""
        for f in os.listdir(output_dir):
            if f.startswith(f"media_{timestamp}") and f.endswith(".vtt"):
                vtt_path = os.path.join(output_dir, f)
                caption_text = _parse_vtt_to_plain(vtt_path)
                logger.info(f"📝 Captions extracted from VTT: {vtt_path}")
                break

        logger.info(f"✅ Downloaded audio from URL: {url} → {expected_mp3}")
        return {
            "audio_path":   expected_mp3,
            "title":        title,
            "duration":     duration,
            "platform":     extractor,
            "caption_text": caption_text,
            "description":  description,
        }

    except Exception as e:
        logger.error(f"Failed to download media from URL '{url}': {e}")
        raise RuntimeError(f"URL Download Failed: {e}")


def _parse_vtt_to_plain(vtt_path: str) -> str:
    """Extract plain subtitle text from a WebVTT file."""
    try:
        with open(vtt_path, encoding="utf-8", errors="ignore") as f:
            content = f.read()
        # Remove WEBVTT header, timestamps, tags
        content = re.sub(r"WEBVTT.*?\n\n", "", content, flags=re.DOTALL)
        content = re.sub(r"\d+:\d+:\d+\.\d+\s*-->\s*\d+:\d+:\d+\.\d+[^\n]*\n", "", content)
        content = re.sub(r"<[^>]+>", "", content)          # HTML tags
        content = re.sub(r"\d+\n", "", content)             # cue numbers
        lines = [l.strip() for l in content.splitlines() if l.strip()]
        # De-duplicate adjacent identical lines
        deduped = []
        for l in lines:
            if not deduped or l != deduped[-1]:
                deduped.append(l)
        return " ".join(deduped)
    except Exception as ex:
        logger.warning(f"VTT parse failed: {ex}")
        return ""


# ── Step 2: Build timed subtitle segments ────────────────────────────────────

def _build_subtitle_segments(subtitle_lines: list, duration: float) -> list:
    """
    Given a list of subtitle lines and total video duration,
    return list of (start_sec, end_sec, text) tuples with even timing.
    """
    if not subtitle_lines:
        return []
    n = len(subtitle_lines)
    per_seg = duration / n
    segments = []
    for i, line in enumerate(subtitle_lines):
        t_start = i * per_seg
        t_end   = min((i + 1) * per_seg, duration - 0.05)
        segments.append((t_start, t_end, line.strip()))
    return segments


# ── Step 3: Burn subtitles via FFmpeg drawtext ───────────────────────────────

def _burn_subtitles(
    input_video: str,
    output_video: str,
    segments: list,
    font_path: str,
    font_size: int = 56,
    vid_height: int = 1920,
    subtitle_position: float = 0.72,   # 0.0=top … 1.0=bottom
) -> bool:
    """
    Burn timed subtitle segments into the video using FFmpeg drawtext.
    Returns True on success, False on failure.
    """
    if not segments:
        return False

    ffmpeg_font = _ffmpeg_font_path(font_path)
    line_height = font_size + 16
    drawtext_parts = []

    for (t_start, t_end, text) in segments:
        wrapped = _wrap_text(text, max_chars=26)
        total_text_h = len(wrapped) * line_height
        base_y = int(vid_height * subtitle_position) - total_text_h // 2

        for j, wline in enumerate(wrapped):
            escaped = _escape_drawtext(wline)
            y_px    = base_y + j * line_height

            dt = (
                f"drawtext="
                f"fontfile='{ffmpeg_font}'"
                f":text='{escaped}'"
                f":fontcolor=white"
                f":fontsize={font_size}"
                f":borderw=3"
                f":bordercolor=black@0.9"
                f":box=1"
                f":boxcolor=black@0.50"
                f":boxborderw=14"
                f":x=(w-text_w)/2"
                f":y={y_px}"
                f":enable='between(t\\,{t_start:.3f}\\,{t_end:.3f})'"
            )
            drawtext_parts.append(dt)

    vf_chain = ",".join(drawtext_parts)

    cmd = [
        "ffmpeg", "-y",
        "-i", input_video,
        "-vf", vf_chain,
        "-c:v", "libx264", "-crf", "18", "-preset", "fast",
        "-pix_fmt", "yuv420p",
        "-c:a", "copy",
        output_video,
    ]
    logger.info(f"🔤 Burning {len(segments)} subtitle segment(s) into video…")
    result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if result.returncode != 0:
        err = result.stderr.decode(errors="ignore")[-600:]
        logger.error(f"Subtitle burn FFmpeg error:\n{err}")
        return False
    logger.success(f"✅ Subtitles burned successfully → {output_video}")
    return True


# ── Main workflow ─────────────────────────────────────────────────────────────

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

    # 1. Download Media Audio + metadata
    media_info    = download_media_from_url(url)
    audio_path    = media_info["audio_path"]
    video_title   = media_info["title"]
    caption_text  = media_info.get("caption_text", "")

    # 2. Measure audio duration precisely
    try:
        from moviepy import AudioFileClip
        ac = AudioFileClip(audio_path)
        duration = ac.duration
        ac.close()
    except Exception:
        duration = media_info.get("duration", 15) or 15

    # 3. Build subtitle lines
    #    Priority: custom text > extracted captions > video title
    if custom_subtitle_text.strip():
        raw_lines = [l.strip() for l in custom_subtitle_text.split("\n") if l.strip()]
    elif caption_text.strip():
        # Split caption into ~5-word chunks for readable subtitle segments
        words = caption_text.split()
        chunk_size = 5
        raw_lines = [
            " ".join(words[i:i+chunk_size])
            for i in range(0, len(words), chunk_size)
        ]
        # Cap at ~60 segments to avoid too-short flashes
        if len(raw_lines) > 60:
            raw_lines = raw_lines[:60]
    else:
        raw_lines = [video_title]

    subtitle_segments = _build_subtitle_segments(raw_lines, duration)
    logger.info(f"📝 {len(subtitle_segments)} subtitle segment(s) prepared")

    # 4. Download Background Visual Clips
    video_aspect_enum = VideoAspect.portrait if aspect_ratio == "portrait" else VideoAspect.landscape
    bg_paths = material.download_videos(
        task_id=f"url_{int(time.time())}",
        search_terms=[background_theme],
        video_aspect=video_aspect_enum,
        video_contact_mode=VideoConcatMode.random,
        audio_duration=duration,
    )
    bg_paths = [p for p in bg_paths if p and os.path.exists(p)]

    if not bg_paths:
        raise RuntimeError(f"No background clips found for theme '{background_theme}'")

    # 5. Output paths
    output_dir = os.path.join(utils.root_dir(), "storage", "general_videos")
    os.makedirs(output_dir, exist_ok=True)
    if not output_filename:
        output_filename = f"recreated_{int(time.time())}.mp4"
    final_output = os.path.join(output_dir, output_filename)

    # 6. Concat background clips into raw BG video
    list_txt = os.path.join(output_dir, f"concat_{int(time.time())}.txt")
    total_bg_dur = 0.0
    with open(list_txt, "w", encoding="utf-8") as f:
        while total_bg_dur < duration + 2.0:
            for bp in bg_paths:
                clean_p = bp.replace("\\", "/")
                f.write(f"file '{clean_p}'\n")
                total_bg_dur += 10.0

    vid_w, vid_h = (1080, 1920) if aspect_ratio == "portrait" else (1920, 1080)
    scale_vf     = f"scale={vid_w}:{vid_h}:force_original_aspect_ratio=increase,crop={vid_w}:{vid_h}"

    raw_bg_mp4 = os.path.join(output_dir, f"raw_bg_{int(time.time())}.mp4")
    cmd_bg = [
        "ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", list_txt,
        "-t", str(round(duration, 2)),
        "-c:v", "libx264", "-pix_fmt", "yuv420p", "-r", "30",
        "-vf", scale_vf,
        "-an", raw_bg_mp4,
    ]
    subprocess.run(cmd_bg, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    # 7. Merge Audio → no-subtitle intermediate
    no_sub_mp4 = os.path.join(output_dir, f"nosub_{int(time.time())}.mp4")
    cmd_merge = [
        "ffmpeg", "-y",
        "-i", raw_bg_mp4,
        "-i", audio_path,
        "-c:v", "copy",
        "-c:a", "aac", "-b:a", "192k",
        "-shortest", no_sub_mp4,
    ]
    subprocess.run(cmd_merge, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    # 8. Burn subtitles onto video
    font_path = os.path.join(utils.root_dir(), "resource", "fonts", "MicrosoftYaHeiBold.ttc")
    if not os.path.exists(font_path):
        # Fallback to Charm-Bold if available
        font_path = os.path.join(utils.root_dir(), "resource", "fonts", "Charm-Bold.ttf")

    subtitle_ok = False
    if subtitle_segments and os.path.exists(font_path):
        subtitle_ok = _burn_subtitles(
            input_video=no_sub_mp4,
            output_video=final_output,
            segments=subtitle_segments,
            font_path=font_path,
            font_size=56,
            vid_height=vid_h,
            subtitle_position=0.72,   # 72% from top (center-lower area)
        )

    # If subtitle burn failed or skipped → just copy no_sub as final
    if not subtitle_ok:
        logger.warning("Subtitle burn skipped/failed — outputting video without subtitles")
        import shutil
        shutil.copy2(no_sub_mp4, final_output)

    # 9. Cleanup temp files
    for tmp in [list_txt, raw_bg_mp4, no_sub_mp4]:
        try:
            if tmp and os.path.exists(tmp):
                os.remove(tmp)
        except Exception:
            pass

    logger.success(f"🎉 Reel re-created → {final_output}")
    return final_output
