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
from typing import Dict, Any, List
import numpy as np
import yt_dlp
from loguru import logger
from PIL import Image, ImageDraw, ImageFont

from app.services import material
from app.utils import utils
from app.config import config
from app.models.schema import VideoAspect, VideoConcatMode

# ── 15 Master Theme Categories ─────────────────────────────────────────
THEME_SEARCH_MAP = {
    "smart_auto_match": ["smart_auto_match"],
    "kaaba":          ["kaaba mecca aerial", "grand mosque mecca tawaf"],
    "madinah":        ["green dome madinah", "al masjid an nabawi aerial"],
    "mosque":         ["mosque interior dome", "masjid architecture interior"],
    "quran":          ["islamic calligraphy architecture", "mosque lighting quran"],
    "rain":           ["rain drops window", "rain storm nature peaceful"],
    "ocean":          ["ocean waves beach aerial", "sea sunset shoreline"],
    "nature":         ["mountain landscape aerial", "forest aerial nature green"],
    "dark_aesthetic": ["dark gold glow aesthetic", "cinematic dark lighting"],
    "autumn":         ["autumn woods falling leaves", "yellow forest foliage"],
    "snow":           ["winter snowfall frozen mountains", "snowy forest landscape"],
    "space":          ["galaxy stars aurora borealis", "nebula space starry night"],
    "candle":         ["candle light vintage ambiance", "warm candle glow dark"],
    "driving":        ["highway driving rain pov", "road trip scenic timelapse"],
    "city":           ["city lights night timelapse", "metropolis skyline night"],
    "islamic":        ["kaaba mecca aerial", "mosque interior marble"],
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

    # Clean and extract pure HTTP/HTTPS URL from any markdown/text format
    url_match = re.search(r'https?://[^\s<">]+', url)
    if url_match:
        url = url_match.group(0)
    url = url.strip().rstrip(')]>"\'')

    timestamp = int(time.time())
    out_tmpl = os.path.join(output_dir, f"media_{timestamp}.%(ext)s")

    ydl_opts = {
        'format': 'bestaudio/best',
        'outtmpl': out_tmpl,
        'quiet': True,
        'no_warnings': True,
        'nocheckcertificate': True,
        'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'extractor_args': {'youtube': {'player_client': ['android', 'web', 'mweb', 'ios']}},
        'retries': 10,
        'fragment_retries': 10,
        'skip_unavailable_fragments': True,
        'socket_timeout': 30,
        'file_access_retries': 5,
        'geo_bypass': True,
    }

    info = None
    last_err = None
    for attempt in range(1, 4):
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)
                if info:
                    break
        except Exception as ex:
            last_err = ex
            logger.warning(f"URL download attempt {attempt}/3 failed ({ex}). Retrying in 2s...")
            time.sleep(2)

    if not info:
        raise RuntimeError(f"URL Download Failed: {last_err or 'Could not fetch video. Please check internet connection or URL.'}")


    raw_title   = info.get('title', '') if isinstance(info, dict) else ''
    duration_yt = info.get('duration', 0) if isinstance(info, dict) else 0
    extractor   = info.get('extractor_key', 'Generic') if isinstance(info, dict) else 'Generic'
    description = info.get('description', '') if isinstance(info, dict) else ''

    # Find the downloaded video file
    video_file = None
    for ext in ['mp4', 'webm', 'mkv', 'mov', 'avi', 'mp3', 'm4a']:
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

    title = raw_title.strip() or description[:80].strip() or f"Video {timestamp}"
    logger.info(f"✅ Audio ready ({duration:.1f}s): {audio_mp3}")
    return {
        "audio_path": audio_mp3,
        "video_file": video_file,
        "title": title,
        "raw_title": raw_title,
        "duration": duration,
        "platform": extractor,
        "caption_text": caption_text,
    }


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

    canvas = Image.new("RGBA", (vid_w, vid_h), (0, 0, 0, 0))
    draw   = ImageDraw.Draw(canvas)


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


def apply_anticopyright_audio_shield(audio_path: str, asmrsound_enabled: bool = True) -> str:
    """
    🛡️ Maximum Anti-Copyright Shield:
    1. Frequency Pitch Modulation (asetrate=44100*0.985,atempo=1.015) to alter audio hash footprint.
    2. ASMR Ambient Rain Layering (-22dB) to evade Content ID matches on YouTube/Facebook/Instagram.
    """
    if not audio_path or not os.path.exists(audio_path):
        return audio_path

    output_dir = os.path.dirname(audio_path)
    ts = int(time.time() * 1000)
    shifted_audio = os.path.join(output_dir, f"audio_pitch_{ts}.mp3")

    try:
        # Step 1: Frequency pitch shift (modifies audio hash without altering human clarity)
        cmd_pitch = [
            "ffmpeg", "-y", "-i", audio_path,
            "-af", "asetrate=44100*0.985,atempo=1.015,highpass=f=80,lowpass=f=12000",
            "-ac", "2", "-ar", "44100", "-c:a", "libmp3lame", "-b:a", "192k",
            shifted_audio
        ]
        res = subprocess.run(cmd_pitch, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        if res.returncode == 0 and os.path.exists(shifted_audio) and os.path.getsize(shifted_audio) > 1000:
            audio_to_use = shifted_audio
            logger.info("🛡️ Applied frequency pitch modulation for Content ID hash evasion!")
        else:
            audio_to_use = audio_path
    except Exception as p_err:
        logger.warning(f"Pitch shift warning: {p_err}")
        audio_to_use = audio_path

    # Step 2: Layer ASMR Ambient Rain Sound (if enabled)
    asmr_path = os.path.join(utils.root_dir(), "resource", "audio", "rain_asmr.wav")
    if asmrsound_enabled and os.path.exists(asmr_path):
        try:
            mixed_audio = os.path.join(output_dir, f"audio_shield_{ts}.mp3")
            cmd_mix = [
                "ffmpeg", "-y",
                "-i", audio_to_use,
                "-stream_loop", "-1", "-i", asmr_path,
                "-filter_complex", "[1:a]volume=0.08[rain];[0:a][rain]amix=inputs=2:duration=first:dropout_transition=2[out]",
                "-map", "[out]", "-c:a", "libmp3lame", "-b:a", "192k",
                mixed_audio
            ]
            res_mix = subprocess.run(cmd_mix, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            if res_mix.returncode == 0 and os.path.exists(mixed_audio) and os.path.getsize(mixed_audio) > 1000:
                logger.info("🛡️ Applied ASMR Rain Ambient Layering for 100% Anti-Copyright Protection!")
                return mixed_audio
        except Exception as mix_err:
            logger.warning(f"ASMR rain mix warning: {mix_err}")

    return audio_to_use


# ── Main workflow ─────────────────────────────────────────────────────────────

def recreate_video_from_url(
    url: str,
    background_theme: str = "islamic",
    aspect_ratio: str = "portrait",
    video_source: str = "pexels",   # "pexels" | "pixabay" | "9router"
    enable_copyright_shield: bool = True,
    enable_subtitles: bool = False,
    subtitle_style: str = "gold",
    selected_voice: str = "",
    image_style: str = "photorealistic",
    bgm_mood: str = "none",
    logo_path: str = "",
    logo_position: str = "top_right",
    logo_size: int = 130,
    logo_opacity: float = 0.9,
    output_filename: str = "",
) -> Dict[str, Any]:
    """
    Full workflow: download complete audio → Anti-Copyright Shield → background (Pexels/Pixabay/9Router AI) → merge.
    Returns dictionary with final_output video path, thumbnails, and viral SEO hashtags!
    """
    logger.info(f"🚀 Re-creating Reel from URL: {url}  |  source={video_source}")

    # 1. Download complete audio + metadata
    media_info   = download_media_from_url(url)
    raw_audio    = media_info["audio_path"]
    clean_title  = media_info["title"]
    caption_text = media_info.get("caption_text", "")
    duration     = media_info["duration"]

    # Apply AI Voice Dubbing OR 100% Anti-Copyright Protection Shield
    if selected_voice:
        logger.info(f"🎙️ Dubbing video with AI Voice / Cloned Voice: {selected_voice}")
        try:
            from app.services import subtitle, voice
            srt_tmp = os.path.join(output_dir, f"trans_{int(time.time())}.srt")
            subtitle.create(audio_file=raw_audio, subtitle_file=srt_tmp)
            
            # Extract transcript text
            full_text = clean_title
            if os.path.exists(srt_tmp):
                with open(srt_tmp, "r", encoding="utf-8") as sf:
                    lines = [l.strip() for l in sf.readlines() if l.strip() and not l.strip().isdigit() and "-->" not in l]
                    if lines:
                        full_text = " ".join(lines)
            
            dub_audio = os.path.join(output_dir, f"dub_{int(time.time())}.mp3")
            voice.tts(text=full_text, voice_name=selected_voice, voice_rate=1.0, voice_file=dub_audio)
            if os.path.exists(dub_audio) and os.path.getsize(dub_audio) > 1000:
                audio_path = dub_audio
                logger.success(f"🎙️ AI Dubbing generated successfully: {dub_audio}")
            elif enable_copyright_shield:
                audio_path = apply_anticopyright_audio_shield(raw_audio, asmrsound_enabled=True)
            else:
                audio_path = raw_audio
        except Exception as dub_err:
            logger.warning(f"AI Dubbing error: {dub_err}. Falling back to original audio.")
            audio_path = apply_anticopyright_audio_shield(raw_audio, asmrsound_enabled=True) if enable_copyright_shield else raw_audio
    elif enable_copyright_shield:
        audio_path = apply_anticopyright_audio_shield(raw_audio, asmrsound_enabled=True)
    else:
        audio_path = raw_audio

    logger.info(f"🎵 Audio duration: {duration:.1f}s  |  Title: {clean_title}")

    # 2. Build search terms from theme map
    if background_theme == "smart_auto_match":
        search_terms = [clean_title]
        if caption_text:
            search_terms.extend([line.strip() for line in caption_text.split("\n") if line.strip()][:3])
        logger.info(f"✨ Smart Auto-Match derived search terms: {search_terms}")
    else:
        search_terms = THEME_SEARCH_MAP.get(background_theme, [background_theme])

    # 3. Resolve dimensions
    vid_w, vid_h       = (1080, 1920) if aspect_ratio == "portrait" else (1920, 1080)
    video_aspect_enum  = VideoAspect.portrait if aspect_ratio == "portrait" else VideoAspect.landscape

    bg_paths = []
    task_ts  = f"url_{int(time.time())}"

    # ── 9Router AI Images + Motion branch ──────────────────────────────────
    if video_source == "9router":
        logger.info("🤖 Using 9Router AI Images + Motion for background")
        try:
            from app.services.ninerouter_image import generate_9router_videos
            output_dir_9r = os.path.join(utils.root_dir(), "storage", "general_videos")
            os.makedirs(output_dir_9r, exist_ok=True)

            # Build AI-tailored prompts: theme keyword + video title context
            theme_label = background_theme.replace("_", " ").title()
            enriched_terms = [
                f"{clean_title}, {t}, cinematic 4K, peaceful" for t in search_terms
            ]
            nine_paths = generate_9router_videos(
                task_id=task_ts,
                search_terms=enriched_terms,
                video_aspect=video_aspect_enum,
                audio_duration=duration,
                max_clip_duration=3.5,
                task_dir=output_dir_9r,
                image_style=image_style,
            )
            bg_paths = [p for p in nine_paths if p and os.path.exists(p)]
            if bg_paths:
                logger.success(f"🤖 9Router produced {len(bg_paths)} background clip(s)")
            else:
                logger.warning("🤖 9Router returned no clips — generating 100% pure AI image clips (Strict AI Mode)")
        except Exception as nine_err:
            logger.warning(f"🤖 9Router error: {nine_err} — generating 100% pure AI image clips")

    # ── Standard stock footage (Pexels / Pixabay) ──────────
    if not bg_paths:
        if video_source == "9router":
            logger.info("🎨 Generating 100% Pure Script-Tailored AI Images (No Pexels Stock Videos Allowed)")
            from app.services.material import download_videos
            # Pass source="9router" to ensure fallback AI images are generated without stock footage
            bg_paths = download_videos(
                task_id=task_ts,
                search_terms=search_terms,
                video_aspect=video_aspect_enum,
                video_contact_mode=VideoConcatMode.random,
                audio_duration=duration,
                source="9router",
            )
        else:
            _src = "pexels" if video_source not in ("pixabay",) else video_source
            logger.info(f"Fetching stock background via source='{_src}' | terms={search_terms}")
            bg_paths = material.download_videos(
                task_id=task_ts,
                search_terms=search_terms,
                video_aspect=video_aspect_enum,
                video_contact_mode=VideoConcatMode.random,
                audio_duration=duration,
                source=_src,
            )
        bg_paths = [p for p in bg_paths if p and os.path.exists(p)]

    if not bg_paths:
        raise RuntimeError(f"No background clips found for theme '{background_theme}' / source '{video_source}'")

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
        "-c:v", "libx264", "-preset", "ultrafast", "-pix_fmt", "yuv420p", "-r", "30",
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

    # 7. Output — clean video or subtitle overlay
    if not output_filename:
        output_filename = f"recreated_{ts}.mp4"
    final_output = os.path.join(output_dir, output_filename)

    if enable_subtitles:
        logger.info("🔤 Generating Dynamic Subtitles Overlay...")
        try:
            srt_path = os.path.join(output_dir, f"sub_{ts}.srt")
            # Generate SRT subtitle from audio transcript using Whisper
            from app.services import subtitle
            subtitle.create(
                audio_file=audio_path,
                subtitle_file=srt_path
            )
            if os.path.exists(srt_path):
                # Burn SRT into video using FFmpeg vf filter with selected subtitle_style
                srt_escaped = srt_path.replace("\\", "/").replace(":", "\\:")
                
                # Primary Colour in ASS format: &H00BBGGRR
                color_map = {
                    "gold":  "&H0000FFFF",  # Bright Yellow (RGB: 255, 255, 0)
                    "cyan":  "&H00FFFF00",  # Neon Cyan (RGB: 0, 255, 255)
                    "white": "&H00FFFFFF",  # Pure White (RGB: 255, 255, 255)
                    "green": "&H0000FF00",  # Emerald Green (RGB: 0, 255, 0)
                }
                primary_color = color_map.get(subtitle_style, "&H0000FFFF")

                sub_vf = f"subtitles='{srt_escaped}':force_style='FontSize=22,PrimaryColour={primary_color},OutlineColour=&H00000000,BorderStyle=1,Outline=2,Alignment=2'"
                subprocess.run([
                    "ffmpeg", "-y",
                    "-i", no_sub,
                    "-vf", sub_vf,
                    "-c:a", "copy",
                    final_output
                ], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                logger.success(f"🔤 Subtitles ({subtitle_style}) burned into recreated video!")
            else:
                shutil.copy2(no_sub, final_output)
        except Exception as sub_err:
            logger.warning(f"Subtitle overlay warning: {sub_err}. Saving clean video.")
            shutil.copy2(no_sub, final_output)
    else:
        shutil.copy2(no_sub, final_output)

    # 8. Auto-Generate 3 High-CTR Thumbnails & Viral SEO Hashtags
    thumbnails = generate_auto_thumbnails(video_path=final_output, title=clean_title, output_dir=output_dir)
    seo_data = generate_viral_seo_hashtags(title=clean_title)

    # 9. Cleanup temp files
    for tmp in [list_txt, raw_bg, no_sub]:
        try:
            if tmp and os.path.exists(tmp):
                os.remove(tmp)
        except Exception:
            pass

    logger.success(f"🎉 Re-created Reel → {final_output}  ({duration:.1f}s)")
    return {
        "video_path": final_output,
        "thumbnails": thumbnails,
        "hashtags": seo_data["hashtags"],
        "seo_description": seo_data["seo_description"],
        "title": clean_title,
    }


def generate_viral_seo_hashtags(title: str) -> dict:
    cleaned = re.sub(r'[^\w\s]', '', title).strip()
    words = [w for w in cleaned.split() if len(w) > 2]
    base_tags = ["#Shorts", "#Reels", "#Viral", "#Trending", "#FYP", "#AIContent"]
    topic_tags = [f"#{w.capitalize()}" for w in words[:5]]
    all_tags = list(dict.fromkeys(base_tags + topic_tags))
    seo_desc = (
        f"🔥 {title}\n\n"
        f"Watch this viral video about {title}! High quality 4K documentary AI short.\n\n"
        f"Subscribe for more daily AI reels and stories!\n\n"
        f"{' '.join(all_tags)}"
    )
    return {
        "title": title,
        "hashtags": " ".join(all_tags),
        "seo_description": seo_desc,
    }


def generate_auto_thumbnails(video_path: str, title: str, output_dir: str) -> List[str]:
    thumbnails = []
    if not os.path.exists(video_path):
        return thumbnails

    ts = int(time.time())
    timestamps = ["00:00:02", "00:00:05", "00:00:08"]
    
    for i, t in enumerate(timestamps, start=1):
        thumb_file = os.path.join(output_dir, f"thumbnail_{i}_{ts}.jpg")
        clean_t = re.sub(r'[^a-zA-Z0-9 ]', '', title)[:25] or "VIRAL VIDEO"
        vf_filter = (
            f"drawtext=text='{clean_t}':"
            f"fontcolor=yellow:fontsize=36:x=(w-text_w)/2:y=h-140:"
            f"box=1:boxcolor=black@0.7:boxborderw=10"
        )
        cmd = [
            "ffmpeg", "-y", "-ss", t, "-i", video_path,
            "-vframes", "1", "-vf", vf_filter,
            thumb_file
        ]
        res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        if res.returncode == 0 and os.path.exists(thumb_file):
            thumbnails.append(thumb_file)
            
    return thumbnails
