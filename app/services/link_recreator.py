"""
link_recreator.py — Universal Link-to-Video Re-Creator Engine
Downloads full audio from YouTube Shorts, Facebook Reels, TikTok, or Instagram Reels,
burns proper Arabic/Urdu/English subtitles via PIL, overlays Islamic-safe backgrounds.
"""

import os
import re
import time
import shutil
import subprocess
import numpy as np
import yt_dlp
from loguru import logger
from PIL import Image, ImageDraw, ImageFont

from app.services import material
from app.utils import utils
from app.config import config
from app.models.schema import VideoAspect, VideoConcatMode

# ── Islamic-safe Pexels search terms (no people, architecture only) ───────────
THEME_SEARCH_MAP = {
    "islamic":  ["kaaba mecca aerial",   "mosque interior marble"],
    "kaaba":    ["kaaba mecca aerial",   "grand mosque mecca"],
    "mosque":   ["mosque interior dome", "masjid architecture interior"],
    "quran":    ["mosque interior",      "islamic calligraphy architecture"],
    "rain":     ["rain drops window",    "rain storm nature"],
    "nature":   ["mountain landscape aerial", "forest aerial nature"],
    "galaxy":   ["galaxy stars timelapse",   "nebula space stars"],
    "driving":  ["road driving timelapse",   "highway aerial view"],
}

# ── Fonts ──────────────────────────────────────────────────────────────────────
_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.realpath(__file__))))
_FONTS_DIR = os.path.join(_ROOT, "resource", "fonts")

_ARABIC_FONT  = os.path.join(_FONTS_DIR, "UthmanicHafs.ttf")
_NASTALEEQ    = os.path.join(_FONTS_DIR, "JameelNooriNastaleeq.ttf")
_BOLD_LATIN   = os.path.join(_FONTS_DIR, "MicrosoftYaHeiBold.ttc")

try:
    import arabic_reshaper
    from bidi.algorithm import get_display
    _ARABIC_SUPPORT = True
except ImportError:
    _ARABIC_SUPPORT = False


# ── Helpers ────────────────────────────────────────────────────────────────────

def _is_arabic(text: str) -> bool:
    return bool(re.search(r'[\u0600-\u06FF]', text))


def _reshape(text: str) -> str:
    """Apply Arabic reshaping + BiDi reordering for PIL rendering."""
    if not _ARABIC_SUPPORT or not text:
        return text
    try:
        return get_display(arabic_reshaper.reshape(text))
    except Exception:
        return text


def _clean_title(title: str) -> str:
    """Strip view counts, reaction counts, hashtags, and pipe separators from a title."""
    # Remove view / reaction / like / comment counts  e.g. "29K views •"
    title = re.sub(
        r'\d+[\.,]?\d*\s*[KMBkmb]?\s*(views?|reactions?|likes?|comments?|shares?)\s*[•·|]?\s*',
        '', title, flags=re.IGNORECASE
    )
    # Remove all hashtags
    title = re.sub(r'#\w+', '', title)
    # Remove pipe / bullet separators
    title = re.sub(r'\s*[|•·]\s*', ' ', title)
    # Collapse whitespace
    title = re.sub(r'\s+', ' ', title).strip()
    return title


def _best_font(is_arabic_text: bool) -> str:
    """Return best available font path for the text language."""
    candidates = [_ARABIC_FONT, _NASTALEEQ, _BOLD_LATIN] if is_arabic_text else [_BOLD_LATIN, _NASTALEEQ]
    for p in candidates:
        if os.path.exists(p):
            return p
    return _BOLD_LATIN


def _wrap_text(text: str, max_chars: int = 24) -> list:
    """Word-wrap text into lines of at most max_chars characters."""
    words, lines, cur = text.split(), [], ""
    for w in words:
        if len(cur) + len(w) + (1 if cur else 0) <= max_chars:
            cur = (cur + " " + w).strip()
        else:
            if cur:
                lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return lines or [text]


# ── Step 1: Download full audio from URL ─────────────────────────────────────

def download_media_from_url(url: str, output_dir: str = "") -> dict:
    """
    Download FULL audio + metadata from a social media URL.
    Downloads the full video first (to avoid Facebook/TikTok audio truncation),
    then extracts audio via FFmpeg.
    Returns dict: audio_path, title, duration, platform, caption_text.
    """
    if not output_dir:
        output_dir = os.path.join(utils.root_dir(), "storage", "url_downloads")
    os.makedirs(output_dir, exist_ok=True)

    timestamp = int(time.time())
    # Download best video+audio combined (avoids truncated audio-only streams)
    out_tmpl = os.path.join(output_dir, f"media_{timestamp}.%(ext)s")

    ydl_opts = {
        'format': 'best/bestvideo+bestaudio',
        'outtmpl': out_tmpl,
        'merge_output_format': 'mp4',
        'writeautomaticsub': True,
        'subtitlesformat': 'vtt',
        'subtitleslangs': ['ar', 'en', 'ur'],
        'quiet': True,
        'no_warnings': True,
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            raw_title   = info.get('title', '')
            duration_yt = info.get('duration', 0)
            extractor   = info.get('extractor_key', 'Generic')
            description = info.get('description', '')

        # Find the downloaded video file
        video_file = None
        for ext in ['mp4', 'webm', 'mkv', 'mov', 'avi']:
            candidate = os.path.join(output_dir, f"media_{timestamp}.{ext}")
            if os.path.exists(candidate):
                video_file = candidate
                break
        if not video_file:
            for f in os.listdir(output_dir):
                if f.startswith(f"media_{timestamp}") and not f.endswith('.vtt'):
                    video_file = os.path.join(output_dir, f)
                    break

        if not video_file:
            raise RuntimeError("yt-dlp did not produce a video/audio file.")

        # Extract full audio as MP3 via FFmpeg (guarantees no truncation)
        audio_mp3 = os.path.join(output_dir, f"audio_{timestamp}.mp3")
        cmd_audio = [
            "ffmpeg", "-y", "-i", video_file,
            "-vn", "-c:a", "libmp3lame", "-b:a", "192k",
            "-q:a", "2", audio_mp3,
        ]
        res = subprocess.run(cmd_audio, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        if res.returncode != 0 or not os.path.exists(audio_mp3):
            raise RuntimeError(f"FFmpeg audio extraction failed: {res.stderr.decode()[-300:]}")

        # Get precise duration from FFmpeg probe
        probe = subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries", "format=duration",
             "-of", "csv=p=0", audio_mp3],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE
        )
        try:
            duration = float(probe.stdout.decode().strip())
        except Exception:
            duration = duration_yt or 30

        # Try to find VTT captions (Arabic preferred)
        caption_text = ""
        for lang in ['ar', 'en', 'ur', '']:
            for f in os.listdir(output_dir):
                if f.startswith(f"media_{timestamp}") and f.endswith('.vtt'):
                    if not lang or f".{lang}." in f or f"-{lang}." in f:
                        vtt_path = os.path.join(output_dir, f)
                        caption_text = _parse_vtt(vtt_path)
                        if caption_text.strip():
                            logger.info(f"📝 Captions loaded ({lang}): {vtt_path}")
                            break
            if caption_text.strip():
                break

        clean_title = _clean_title(raw_title)
        logger.info(f"✅ Audio ready ({duration:.1f}s): {audio_mp3}")
        return {
            "audio_path":   audio_mp3,
            "video_file":   video_file,
            "title":        clean_title,
            "raw_title":    raw_title,
            "duration":     duration,
            "platform":     extractor,
            "caption_text": caption_text,
        }

    except Exception as e:
        logger.error(f"URL download failed '{url}': {e}")
        raise RuntimeError(f"URL Download Failed: {e}")


def _parse_vtt(vtt_path: str) -> str:
    """Parse WebVTT → plain text, dedup adjacent identical lines."""
    try:
        content = open(vtt_path, encoding="utf-8", errors="ignore").read()
        content = re.sub(r"WEBVTT.*?\n\n", "", content, flags=re.DOTALL)
        content = re.sub(r"\d+:\d+:\d+[\.,]\d+\s*-->\s*\d+:\d+:\d+[\.,]\d+[^\n]*\n", "", content)
        content = re.sub(r"<[^>]+>", "", content)
        content = re.sub(r"^\d+\s*$", "", content, flags=re.MULTILINE)
        lines = [l.strip() for l in content.splitlines() if l.strip()]
        deduped = []
        for l in lines:
            if not deduped or l != deduped[-1]:
                deduped.append(l)
        return " ".join(deduped)
    except Exception as ex:
        logger.warning(f"VTT parse error: {ex}")
        return ""


# ── Step 2: Subtitle segment builder ─────────────────────────────────────────

def _build_segments(lines: list, duration: float) -> list:
    """Return [(start, end, text), ...] with even time distribution."""
    if not lines:
        return []
    n = len(lines)
    per = duration / n
    return [(i * per, min((i+1) * per, duration - 0.05), l.strip()) for i, l in enumerate(lines)]


# ── Step 3: PIL subtitle frame renderer ──────────────────────────────────────

def _render_subtitle_frame(
    text: str,
    vid_w: int,
    vid_h: int,
    font_size: int = 58,
    y_frac: float = 0.72,
) -> np.ndarray:
    """
    Render a subtitle onto a transparent RGBA canvas (vid_w × vid_h).
    Handles Arabic RTL reshaping + multi-line word wrap.
    Returns RGBA uint8 numpy array.
    """
    arabic = _is_arabic(text)
    display_text = _reshape(text) if arabic else text
    font_path    = _best_font(arabic)
    max_chars    = 18 if arabic else 24

    try:
        font = ImageFont.truetype(font_path, font_size)
    except Exception:
        font = ImageFont.load_default()

    wrapped = _wrap_text(display_text, max_chars=max_chars)
    line_h  = font_size + 12

    # Measure each line width
    tmp_img  = Image.new("RGBA", (vid_w, vid_h), (0, 0, 0, 0))
    tmp_draw = ImageDraw.Draw(tmp_img)

    line_widths = []
    for ln in wrapped:
        bb = tmp_draw.textbbox((0, 0), ln, font=font)
        line_widths.append(bb[2] - bb[0])
    max_w = max(line_widths) if line_widths else 1

    total_h   = len(wrapped) * line_h
    pad_x, pad_y = 20, 12
    box_w = max_w + pad_x * 2
    box_h = total_h + pad_y * 2
    box_x = (vid_w - box_w) // 2
    box_y = int(vid_h * y_frac) - box_h // 2

    # Draw semi-transparent background box
    canvas = Image.new("RGBA", (vid_w, vid_h), (0, 0, 0, 0))
    draw   = ImageDraw.Draw(canvas)
    draw.rounded_rectangle(
        [box_x, box_y, box_x + box_w, box_y + box_h],
        radius=14,
        fill=(0, 0, 0, 165),
    )

    # Draw each text line
    for j, ln in enumerate(wrapped):
        bb     = draw.textbbox((0, 0), ln, font=font)
        lw     = bb[2] - bb[0]
        tx     = box_x + (box_w - lw) // 2   # centered
        ty     = box_y + pad_y + j * line_h
        # Stroke (black)
        for dx, dy in [(-2,0),(2,0),(0,-2),(0,2),(-2,-2),(2,2),(-2,2),(2,-2)]:
            draw.text((tx+dx, ty+dy), ln, font=font, fill=(0, 0, 0, 220))
        # Main text (white)
        draw.text((tx, ty), ln, font=font, fill=(255, 255, 255, 255))

    return np.array(canvas)


# ── Step 4: Burn subtitle frames via MoviePy ─────────────────────────────────

def _burn_subtitles_pil(
    input_video: str,
    output_video: str,
    segments: list,
    vid_w: int,
    vid_h: int,
    font_size: int = 58,
    y_frac: float = 0.72,
) -> bool:
    """
    Burn timed subtitle segments into video using MoviePy + PIL.
    Supports Arabic RTL, Urdu Nastaleeq, and Latin text.
    Returns True on success.
    """
    try:
        from moviepy import VideoFileClip, ImageClip, CompositeVideoClip

        main_clip = VideoFileClip(input_video)
        overlay_clips = [main_clip]

        for (t_start, t_end, text) in segments:
            if not text.strip():
                continue
            frame = _render_subtitle_frame(text, vid_w, vid_h, font_size=font_size, y_frac=y_frac)
            # Convert RGBA → RGB+mask
            rgba    = Image.fromarray(frame, 'RGBA')
            rgb_arr = np.array(rgba.convert('RGB'))
            msk_arr = np.array(rgba.split()[3])   # alpha channel

            sub_clip = (
                ImageClip(rgb_arr, duration=t_end - t_start)
                .with_mask(ImageClip(msk_arr, is_mask=True, duration=t_end - t_start))
                .with_start(t_start)
            )
            overlay_clips.append(sub_clip)

        final = CompositeVideoClip(overlay_clips, size=(vid_w, vid_h))
        final.write_videofile(
            output_video,
            fps=30,
            codec="libx264",
            audio_codec="aac",
            audio_bitrate="192k",
            preset="fast",
            logger=None,
        )
        main_clip.close()
        final.close()
        logger.success(f"✅ PIL subtitles burned → {output_video}")
        return True

    except Exception as ex:
        logger.error(f"PIL subtitle burn failed: {ex}")
        return False


# ── Main workflow ─────────────────────────────────────────────────────────────

def recreate_video_from_url(
    url: str,
    custom_subtitle_text: str = "",
    background_theme: str = "islamic",
    aspect_ratio: str = "portrait",
    show_box: bool = True,
    logo_path: str = "",
    logo_position: str = "top_right",
    logo_size: int = 130,
    logo_opacity: float = 0.9,
    output_filename: str = "",
) -> str:
    """
    Full workflow: download complete audio → get subtitles → safe background → burn subs → output.
    """
    logger.info(f"🚀 Re-creating Reel from URL: {url}")

    # 1. Download complete audio + metadata
    media_info   = download_media_from_url(url)
    audio_path   = media_info["audio_path"]
    clean_title  = media_info["title"]
    caption_text = media_info.get("caption_text", "")
    duration     = media_info["duration"]

    logger.info(f"🎵 Audio duration: {duration:.1f}s  |  Title: {clean_title}")

    # 2. Build subtitle lines
    #    Priority: custom text > Arabic captions > cleaned title
    if custom_subtitle_text.strip():
        raw_lines = [l.strip() for l in custom_subtitle_text.split("\n") if l.strip()]
    elif caption_text.strip():
        # Chunk captions into ~4-word groups for readable subtitle pace
        words = caption_text.split()
        chunk = 4
        raw_lines = [" ".join(words[i:i+chunk]) for i in range(0, len(words), chunk)]
        if len(raw_lines) > 80:
            raw_lines = raw_lines[:80]
    else:
        # Fallback: use clean title only (no hashtags, no stats)
        raw_lines = [clean_title] if clean_title else ["Recitation"]

    subtitle_segments = _build_segments(raw_lines, duration)
    logger.info(f"📝 {len(subtitle_segments)} subtitle segment(s) prepared")

    # 3. Islamic-safe background search terms
    search_terms = THEME_SEARCH_MAP.get(background_theme, [background_theme])

    # 4. Download background clips
    vid_w, vid_h       = (1080, 1920) if aspect_ratio == "portrait" else (1920, 1080)
    video_aspect_enum  = VideoAspect.portrait if aspect_ratio == "portrait" else VideoAspect.landscape

    bg_paths = material.download_videos(
        task_id=f"url_{int(time.time())}",
        search_terms=search_terms,
        video_aspect=video_aspect_enum,
        video_contact_mode=VideoConcatMode.random,
        audio_duration=duration,
    )
    bg_paths = [p for p in bg_paths if p and os.path.exists(p)]

    if not bg_paths:
        raise RuntimeError(f"No background clips found for theme '{background_theme}'")

    # 5. Concat background clips → raw BG video
    output_dir = os.path.join(utils.root_dir(), "storage", "general_videos")
    os.makedirs(output_dir, exist_ok=True)
    ts = int(time.time())

    list_txt = os.path.join(output_dir, f"concat_{ts}.txt")
    total_bg_dur = 0.0
    with open(list_txt, "w", encoding="utf-8") as f:
        while total_bg_dur < duration + 2.0:
            for bp in bg_paths:
                f.write(f"file '{bp.replace(chr(92), '/')}'\n")
                total_bg_dur += 10.0

    scale_vf = f"scale={vid_w}:{vid_h}:force_original_aspect_ratio=increase,crop={vid_w}:{vid_h}"
    raw_bg   = os.path.join(output_dir, f"raw_bg_{ts}.mp4")
    subprocess.run([
        "ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", list_txt,
        "-t", str(round(duration, 2)),
        "-c:v", "libx264", "-pix_fmt", "yuv420p", "-r", "30",
        "-vf", scale_vf, "-an", raw_bg,
    ], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    # 6. Merge audio → intermediate (no-subtitle) MP4
    no_sub = os.path.join(output_dir, f"nosub_{ts}.mp4")
    subprocess.run([
        "ffmpeg", "-y",
        "-i", raw_bg, "-i", audio_path,
        "-c:v", "copy", "-c:a", "aac", "-b:a", "192k",
        "-shortest", no_sub,
    ], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    # 7. Burn subtitles via PIL (Arabic/Urdu/English aware)
    if not output_filename:
        output_filename = f"recreated_{ts}.mp4"
    final_output = os.path.join(output_dir, output_filename)

    sub_ok = False
    if subtitle_segments:
        sub_ok = _burn_subtitles_pil(
            input_video=no_sub,
            output_video=final_output,
            segments=subtitle_segments,
            vid_w=vid_w,
            vid_h=vid_h,
            font_size=60,
            y_frac=0.72,
        )

    if not sub_ok:
        logger.warning("Subtitle burn skipped/failed → saving video without subtitles")
        shutil.copy2(no_sub, final_output)

    # 8. Cleanup temp files
    for tmp in [list_txt, raw_bg, no_sub]:
        try:
            if tmp and os.path.exists(tmp):
                os.remove(tmp)
        except Exception:
            pass

    logger.success(f"🎉 Re-created Reel → {final_output}  ({duration:.1f}s)")
    return final_output
