"""
quran_task.py — Full Quran video generation pipeline.
Steps: fetch text → download audio → merge audio → apply echo →
       fetch backgrounds → render subtitle frames → compose final video.
"""

import os
import subprocess
import tempfile
from typing import Optional, Callable
from uuid import uuid4
from loguru import logger

from app.utils import utils
from app.services import quran_api, quran_renderer, material


# ── Echo / Reverb presets (FFmpeg aecho filter) ───────────────────────────────
ECHO_PRESETS = {
    "None":   None,
    "Light":  "aecho=0.6:0.4:500:0.2",
    "Medium": "aecho=0.8:0.7:800:0.35",
    "Heavy":  "aecho=0.9:0.85:1200:0.5",
    "Mosque": "aecho=0.8:0.9:1000:0.4,aecho=0.7:0.6:600:0.25",
}

# Background search keywords for Quran videos
ISLAMIC_KEYWORDS = [
    "mosque architecture", "kaaba mecca", "islamic geometric pattern",
    "desert sunset sky", "crescent moon stars", "quran book light",
    "masjid interior", "islamic calligraphy", "medina", "prayer hall",
]


def apply_echo(input_path: str, output_path: str, preset: str = "Medium") -> str:
    """Apply echo/reverb effect + +7dB volume boost to recitation audio using FFmpeg."""
    raw_filter = ECHO_PRESETS.get(preset)
    if raw_filter:
        filter_str = f"{raw_filter},volume=2.2"
    else:
        filter_str = "volume=2.2"

    cmd = [
        "ffmpeg", "-y", "-i", input_path,
        "-af", filter_str,
        "-ar", "44100", "-ac", "2",
        output_path
    ]
    try:
        subprocess.run(cmd, capture_output=True, check=True)
        return output_path
    except subprocess.CalledProcessError as e:
        logger.error(f"Echo effect failed: {e.stderr.decode()}")
        return input_path


def merge_audio_files(audio_files: list[str], output_path: str,
                      silence_ms: int = 400) -> Optional[str]:
    """Concatenate multiple MP3 files with optional silence between them."""
    if not audio_files:
        return None
    if len(audio_files) == 1:
        import shutil
        shutil.copy(audio_files[0], output_path)
        return output_path

    # Build FFmpeg concat filter
    inputs = []
    for f in audio_files:
        inputs += ["-i", f]

    # Create silence file
    tmp_dir = tempfile.mkdtemp()
    silence_path = os.path.join(tmp_dir, "silence.mp3")
    subprocess.run([
        "ffmpeg", "-y", "-f", "lavfi",
        "-i", f"anullsrc=r=44100:cl=stereo",
        "-t", str(silence_ms / 1000),
        silence_path
    ], capture_output=True)

    # Build concat with silence between each ayah
    all_inputs = []
    for f in audio_files:
        all_inputs += ["-i", f, "-i", silence_path]

    n = len(audio_files) * 2
    filter_str = "".join(f"[{i}:a]" for i in range(n)) + f"concat=n={n}:v=0:a=1[out]"

    cmd = ["ffmpeg", "-y"] + all_inputs + [
        "-filter_complex", filter_str,
        "-map", "[out]",
        "-ar", "44100", output_path
    ]
    try:
        subprocess.run(cmd, capture_output=True, check=True)
        return output_path
    except subprocess.CalledProcessError as e:
        logger.error(f"Audio merge failed: {e.stderr.decode()}")
        # Fallback: simple concat without silence
        list_file = os.path.join(tmp_dir, "list.txt")
        with open(list_file, "w") as lf:
            for f in audio_files:
                lf.write(f"file '{f}'\n")
        subprocess.run([
            "ffmpeg", "-y", "-f", "concat", "-safe", "0",
            "-i", list_file, "-c", "copy", output_path
        ], capture_output=True)
        return output_path if os.path.exists(output_path) else None


def get_audio_duration(path: str) -> float:
    """Get duration of audio file in seconds using ffprobe."""
    try:
        result = subprocess.run([
            "ffprobe", "-v", "error", "-show_entries",
            "format=duration", "-of", "default=noprint_wrappers=1:nokey=1",
            path
        ], capture_output=True, text=True, check=True)
        return float(result.stdout.strip())
    except Exception:
        return 0.0


def generate_quran_video(
    task_id: str,
    surah: int,
    from_ayah: int,
    to_ayah: int,
    reciter_name: str = "Mishary Al-Afasy",
    translation_edition: str = "ur.jalandhry",
    video_source: str = "pexels",
    video_aspect: str = "9:16",
    arabic_font_size: int = 80,
    translation_font_size: int = 42,
    arabic_color: str = "#FFD700",
    highlight_color: str = "#FFD700",
    translation_color: str = "#FFFFFF",
    echo_preset: str = "Medium",
    bgm_file: str = "",
    bgm_volume: float = 0.15,
    subtitle_position_pct: float = 0.72,
    progress_cb: Optional[Callable] = None,
    log_cb: Optional[Callable] = None,
    pexels_api_key: str = "",
    pixabay_api_key: str = "",
    logo_path: str = "",
    logo_position: str = "top_right",
    logo_size: int = 120,
    logo_opacity: float = 0.90,
) -> Optional[str]:
    """
    Main pipeline: fetch → audio → echo → backgrounds → subtitle frames → render video.
    Returns path to final MP4 or None on failure.
    """
    def log(msg):
        logger.info(msg)
        if log_cb:
            log_cb(msg)

    def progress(val, total, msg=""):
        if progress_cb:
            progress_cb(val / total, msg)

    task_dir = utils.storage_dir(os.path.join("tasks", task_id), create=True)
    audio_dir = os.path.join(task_dir, "quran_audio")
    os.makedirs(audio_dir, exist_ok=True)

    # ── 1. Get Quran text ─────────────────────────────────────────────────────
    log(f"📖 Fetching Arabic text: Surah {surah}, Ayah {from_ayah}–{to_ayah}")
    ayahs = quran_api.get_ayahs_arabic(surah, from_ayah, to_ayah)
    if not ayahs:
        log("❌ Failed to fetch Arabic text from Quran API")
        return None
    progress(1, 10, "Arabic text fetched")

    # ── 2. Get translation ────────────────────────────────────────────────────
    translations = {}
    if translation_edition:
        log(f"🌐 Fetching translation: {translation_edition}")
        translations = quran_api.get_translations(surah, from_ayah, to_ayah, translation_edition)
    progress(2, 10, "Translation fetched")

    # ── 3. Download recitation audio ──────────────────────────────────────────
    reciters = quran_api.get_reciters_list()
    reciter_info = reciters.get(reciter_name, list(reciters.values())[0])
    reciter_slug = reciter_info["slug"]

    log(f"🎙️ Downloading recitation: {reciter_name} ({len(ayahs)} ayahs)...")
    audio_files = quran_api.download_ayahs_audio(
        surah, from_ayah, to_ayah, reciter_name, audio_dir,
        progress_cb=lambda p: progress(2 + int(p * 3), 10, f"Downloading audio {int(p*100)}%")
    )
    if not audio_files:
        log("❌ Failed to download audio")
        return None

    # ── Prepend Bismillah (Surahs 1 to 114) ──────────────────────────────
    if not (surah == 1 and from_ayah == 1):
        log("🕌 Prepending Bismillah (بِسْمِ ٱللَّهِ ٱلرَّحْمَـٰنِ ٱلرَّحِيمِ)...")
        bismillah_audio = quran_api.download_audio(1, 1, reciter_name, audio_dir)
        if bismillah_audio and os.path.exists(bismillah_audio):
            audio_files = [bismillah_audio] + audio_files
            is_urdu = "ur." in (translation_edition or "")
            bismillah_tr = "اللہ کے نام سے جو بڑا مہربان نہایت رحم والا ہے" if is_urdu else "In the name of Allah, the Entirely Merciful, the Especially Merciful."
            bismillah_data = {
                "ayah": 0,
                "arabic": "بِسْمِ ٱللَّهِ ٱلرَّحْمَـٰنِ ٱلرَّحِيمِ",
                "key": "bismillah",
                "words": ["بِسْمِ", "ٱللَّهِ", "ٱلرَّحْمَـٰنِ", "ٱلرَّحِيمِ"],
                "is_bismillah": True,
            }
            ayahs = [bismillah_data] + ayahs
            translations[0] = bismillah_tr

    progress(5, 10, "Audio downloaded")

    # ── 4. Merge audio + apply echo ───────────────────────────────────────────
    merged_raw = os.path.join(task_dir, "merged_raw.mp3")
    merged_echo = os.path.join(task_dir, "merged_echo.mp3")

    log("🔗 Merging ayah audio files...")
    merged = merge_audio_files(audio_files, merged_raw)
    if not merged:
        log("❌ Audio merge failed")
        return None

    log(f"🔊 Applying echo effect: {echo_preset}")
    final_audio = apply_echo(merged_raw, merged_echo, echo_preset)
    total_duration = get_audio_duration(final_audio)
    log(f"⏱️ Total audio duration: {total_duration:.1f}s")
    progress(6, 10, "Audio processed")

    # ── 5. Fetch background video ─────────────────────────────────────────────
    log(f"🎥 Fetching Islamic background footage from {video_source}...")
    from app.config import config as app_config

    # temporarily set api keys if provided
    if pexels_api_key:
        app_config.app["pexels_api_keys"] = [pexels_api_key]
    if pixabay_api_key:
        app_config.app["pixabay_api_keys"] = [pixabay_api_key]

    import random
    sample_k = min(8, len(ISLAMIC_KEYWORDS))
    selected_terms = random.sample(ISLAMIC_KEYWORDS, k=sample_k)
    video_width, video_height = (1080, 1920) if "9:16" in video_aspect else (1920, 1080)

    try:
        from app.models.schema import VideoAspect, VideoConcatMode
        aspect_enum = VideoAspect.portrait if "9:16" in video_aspect else VideoAspect.landscape
        materials = material.download_videos(
            task_id=task_id,
            search_terms=selected_terms,
            source=video_source,
            video_aspect=aspect_enum,
            video_contact_mode=VideoConcatMode.random,
            audio_duration=total_duration,
            max_clip_duration=4,
        )
    except Exception as e:
        log(f"⚠️ Background fetch warning: {e} — will use color background")
        materials = []
    progress(7, 10, "Backgrounds ready")

    # ── 6. Build subtitle images per ayah with word-level timing ─────────────
    log("✍️ Rendering Arabic subtitle frames with word-by-word karaoke highlight...")
    subtitle_clips_data = []  # list of (start_sec, end_sec, image_path)

    is_urdu = "ur." in (translation_edition or "")
    reciter_id = reciter_info.get("id", 7)
    elapsed = 0.0

    for idx, ayah_data in enumerate(ayahs):
        ayah_num = ayah_data["ayah"]
        arabic_text = ayah_data["arabic"]
        arabic_words = ayah_data.get("words", [arabic_text])
        translation_text = translations.get(ayah_num, "")

        is_bism = ayah_data.get("is_bismillah", False)
        s_id = 1 if is_bism else surah
        a_id = 1 if is_bism else ayah_num

        # Fetch exact word-level timings from Quran API
        word_timings = quran_api.get_word_timings(s_id, a_id, reciter_id)

        # Get this ayah's audio duration
        ayah_audio = audio_files[idx] if idx < len(audio_files) else None
        ayah_dur = get_audio_duration(ayah_audio) if ayah_audio else (total_duration / len(ayahs))
        ayah_start_time = elapsed

        # Check if we have valid non-zero word timestamps
        has_api_timings = bool(word_timings) and any(t.get("end_ms", 0) > 0 for t in word_timings)

        if has_api_timings:
            log(f"⏱️ Using exact Quran.com API timestamps for Ayah {a_id} ({len(word_timings)} words)")
            for wi, t_info in enumerate(word_timings):
                word_text = t_info["word"]
                st_ms = t_info["start_ms"]
                ed_ms = t_info["end_ms"]

                w_start = ayah_start_time + (st_ms / 1000.0)
                w_end = ayah_start_time + (ed_ms / 1000.0) if ed_ms > st_ms else w_start + 0.4
                w_dur = max(0.1, w_end - w_start)

                img = quran_renderer.build_subtitle_frame(
                    arabic_text=arabic_text,
                    translation_text=translation_text,
                    arabic_words=[t["word"] for t in word_timings],
                    highlighted_word_idx=wi,
                    video_width=video_width,
                    video_height=video_height,
                    arabic_font_size=arabic_font_size,
                    translation_font_size=translation_font_size,
                    arabic_color=arabic_color,
                    normal_color="#FFFFFF",
                    highlight_color=highlight_color,
                    stroke_color="#000000",
                    stroke_width=2,
                    translation_color=translation_color,
                    is_urdu_translation=is_urdu,
                    position_pct=subtitle_position_pct,
                )
                img_path = os.path.join(task_dir, f"sub_{a_id:03d}_w{wi:03d}.png")
                img.save(img_path, "PNG")
                subtitle_clips_data.append((w_start, w_dur, img_path))
        elif arabic_words and len(arabic_words) > 1:
            # Fallback: Character-weighted duration allocation
            total_chars = max(1, sum(len(w) for w in arabic_words))
            curr_w_start = ayah_start_time
            for wi, word in enumerate(arabic_words):
                w_dur = (len(word) / total_chars) * ayah_dur
                img = quran_renderer.build_subtitle_frame(
                    arabic_text=arabic_text,
                    translation_text=translation_text,
                    arabic_words=arabic_words,
                    highlighted_word_idx=wi,
                    video_width=video_width,
                    video_height=video_height,
                    arabic_font_size=arabic_font_size,
                    translation_font_size=translation_font_size,
                    arabic_color=arabic_color,
                    normal_color="#FFFFFF",
                    highlight_color=highlight_color,
                    stroke_color="#000000",
                    stroke_width=2,
                    translation_color=translation_color,
                    is_urdu_translation=is_urdu,
                    position_pct=subtitle_position_pct,
                )
                img_path = os.path.join(task_dir, f"sub_{a_id:03d}_w{wi:03d}.png")
                img.save(img_path, "PNG")
                subtitle_clips_data.append((curr_w_start, w_dur, img_path))
                curr_w_start += w_dur
        else:
            img = quran_renderer.build_subtitle_frame(
                arabic_text=arabic_text,
                translation_text=translation_text,
                video_width=video_width,
                video_height=video_height,
                arabic_font_size=arabic_font_size,
                translation_font_size=translation_font_size,
                arabic_color=arabic_color,
                translation_color=translation_color,
                is_urdu_translation=is_urdu,
                position_pct=subtitle_position_pct,
            )
            img_path = os.path.join(task_dir, f"sub_{a_id:03d}.png")
            img.save(img_path, "PNG")
            subtitle_clips_data.append((ayah_start_time, ayah_dur, img_path))

        elapsed += ayah_dur + (0.4 if len(audio_files) > 1 else 0.0)

    progress(8, 10, "Subtitle frames rendered")

    # ── 7. Compose final video with FFmpeg ────────────────────────────────────
    log("🎬 Composing final video...")
    output_path = os.path.join(task_dir, f"quran_{surah}_{from_ayah}_{to_ayah}.mp4")

    # download_videos returns list of file path strings
    bg_paths = materials if isinstance(materials, list) else []

    try:
        _compose_video_ffmpeg(
            subtitle_clips=subtitle_clips_data,
            audio_path=final_audio,
            total_duration=total_duration,
            video_width=video_width,
            video_height=video_height,
            background_paths=bg_paths,
            bgm_file=bgm_file,
            bgm_volume=bgm_volume,
            logo_path=logo_path,
            logo_position=logo_position,
            logo_size=logo_size,
            logo_opacity=logo_opacity,
            output_path=output_path,
            task_dir=task_dir,
            log=log,
        )
    except Exception as e:
        log(f"❌ Video composition error: {e}")
        import traceback
        log(traceback.format_exc())
        return None

    # Dedicated Quran Videos Output Folder
    quran_out_dir = os.path.join(utils.root_dir(), "storage", "quran_videos")
    os.makedirs(quran_out_dir, exist_ok=True)
    final_section_video = os.path.join(quran_out_dir, f"quran_{surah}_{from_ayah}_{to_ayah}_{task_id[:8]}.mp4")

    import shutil
    if os.path.exists(output_path):
        shutil.copy(output_path, final_section_video)
        log(f"📁 Video saved to dedicated section folder: {final_section_video}")

    # Auto-cleanup temporary render files to save disk space
    try:
        log("🧹 Cleaning up temporary PNG frames and intermediate audio files...")
        import glob
        for f in glob.glob(os.path.join(task_dir, "sub_*.png")) + glob.glob(os.path.join(task_dir, "*.mp3")) + glob.glob(os.path.join(task_dir, "*.txt")):
            try:
                os.remove(f)
            except Exception:
                pass
    except Exception as clean_err:
        log(f"⚠️ Temp cleanup notice: {clean_err}")

    progress(10, 10, "✅ Done!")
    log(f"✅ Quran video saved: {final_section_video}")
    return final_section_video


def _compose_video_ffmpeg(
    subtitle_clips: list,
    audio_path: str,
    total_duration: float,
    video_width: int,
    video_height: int,
    background_paths: list[str],
    bgm_file: str,
    bgm_volume: float,
    logo_path: str,
    logo_position: str,
    logo_size: int,
    logo_opacity: float,
    output_path: str,
    task_dir: str,
    log,
):
    """
    High-Speed Native FFmpeg Video Composer.
    Renders background + timed subtitle overlay + BGM + channel logo in seconds.
    """
    import subprocess
    from PIL import Image

    # 1. Create transparent blank PNG for subtitle gaps
    blank_path = os.path.join(task_dir, "sub_blank.png")
    blank_img = Image.new("RGBA", (video_width, video_height), (0, 0, 0, 0))
    blank_img.save(blank_path, "PNG")

    # 2. Build timed concat file for subtitle PNG sequence
    concat_file_path = os.path.join(task_dir, "sub_concat.txt")
    subtitle_clips_sorted = sorted(subtitle_clips, key=lambda x: x[0])

    cur_t = 0.0
    first_frame = subtitle_clips_sorted[0][2] if subtitle_clips_sorted else blank_path
    last_img = first_frame if (first_frame and os.path.exists(first_frame)) else blank_path
    with open(concat_file_path, "w", encoding="utf-8") as f:
        for (start_sec, dur_sec, img_path) in subtitle_clips_sorted:
            if not os.path.exists(img_path) or start_sec >= total_duration:
                continue
            if start_sec > cur_t + 0.005:
                gap = start_sec - cur_t
                gap_img = last_img if last_img and os.path.exists(last_img) else blank_path
                f.write(f"file '{gap_img.replace(os.sep, '/')}'\n")
                f.write(f"duration {gap:.3f}\n")

            valid_dur = min(dur_sec, total_duration - start_sec)
            f.write(f"file '{img_path.replace(os.sep, '/')}'\n")
            f.write(f"duration {valid_dur:.3f}\n")
            cur_t = start_sec + valid_dur
            last_img = img_path

        if cur_t < total_duration:
            gap = total_duration - cur_t
            gap_img = last_img if last_img and os.path.exists(last_img) else blank_path
            f.write(f"file '{gap_img.replace(os.sep, '/')}'\n")
            f.write(f"duration {gap:.3f}\n")

        # Repeat last file entry for FFmpeg concat demuxer format
        f.write(f"file '{last_img.replace(os.sep, '/')}'\n")

    # 3. Audio & BGM preparation
    audio_with_bgm = audio_path
    if bgm_file and os.path.exists(bgm_file) and bgm_volume > 0:
        mixed_audio = os.path.join(task_dir, "audio_mixed.mp3")
        mix_cmd = [
            "ffmpeg", "-y",
            "-i", audio_path,
            "-stream_loop", "-1", "-i", bgm_file,
            "-filter_complex", f"[1:a]volume={bgm_volume:.2f}[bgm];[0:a][bgm]amix=inputs=2:duration=first[aout]",
            "-map", "[aout]",
            "-ar", "44100",
            mixed_audio
        ]
        try:
            subprocess.run(mix_cmd, capture_output=True, check=True)
            if os.path.exists(mixed_audio) and os.path.getsize(mixed_audio) > 1000:
                audio_with_bgm = mixed_audio
        except Exception as bgm_err:
            log(f"⚠️ BGM FFmpeg mix error: {bgm_err}")

    # 4. Multi-Visual Background Concat (Normalized 30fps H.264 composition for 100% continuous video motion)
    bg_paths_str = [m.url if hasattr(m, "url") else str(m) for m in background_paths]
    valid_bg = [p for p in bg_paths_str if os.path.exists(p) and os.path.getsize(p) > 5000]
    import random
    if valid_bg:
        random.shuffle(valid_bg)

    temp_bg_path = os.path.join(task_dir, "temp_bg.mp4")
    has_bg_file = False
    if valid_bg:
        try:
            log("🎬 Building normalized 30fps motion background track with 4-second scene switches...")
            from moviepy.vfx import Loop
            from moviepy.video.VideoClip import ColorClip
            from moviepy.video.compositing.CompositeVideoClip import CompositeVideoClip
            from moviepy.video.compositing.concatenate import concatenate_videoclips
            from moviepy.video.io.VideoFileClip import VideoFileClip

            v_clips = []
            curr_bg_t = 0.0
            bg_i = 0
            while curr_bg_t < total_duration and valid_bg:
                bg_path = valid_bg[bg_i % len(valid_bg)]
                try:
                    raw_c = VideoFileClip(bg_path)
                    clip_dur = min(4.0, raw_c.duration, max(1.0, total_duration - curr_bg_t))
                    c_trimmed = raw_c.subclipped(0, clip_dur)

                    # Scale & Crop to exact (video_width, video_height)
                    vw, vh = c_trimmed.size
                    if vw != video_width or vh != video_height:
                        scale = max(video_width / float(vw), video_height / float(vh))
                        nw, nh = int(vw * scale), int(vh * scale)
                        c_trimmed = c_trimmed.resized((nw, nh))
                        cx, cy = (nw - video_width) // 2, (nh - video_height) // 2
                        c_trimmed = c_trimmed.cropped(x1=cx, y1=cy, width=video_width, height=video_height)

                    v_clips.append(c_trimmed)
                    curr_bg_t += clip_dur
                except Exception as clip_err:
                    log(f"⚠️ Clip process skip: {clip_err}")
                bg_i += 1

            if v_clips:
                bg_sequence = concatenate_videoclips(v_clips, method="compose")
                if bg_sequence.duration < total_duration:
                    bg_sequence = bg_sequence.with_effects([Loop(duration=total_duration)])
                else:
                    bg_sequence = bg_sequence.subclipped(0, total_duration)

                bg_sequence.write_videofile(
                    temp_bg_path,
                    fps=30,
                    codec="libx264",
                    preset="superfast",
                    audio=False,
                    threads=4,
                    logger=None
                )
                bg_sequence.close()
                for c in v_clips:
                    try:
                        c.close()
                    except Exception:
                        pass

                if os.path.exists(temp_bg_path) and os.path.getsize(temp_bg_path) > 10000:
                    has_bg_file = True
        except Exception as bg_build_err:
            log(f"⚠️ Motion background build fallback: {bg_build_err}")

    # 5. Build FFmpeg command inputs and filter graph
    cmd = ["ffmpeg", "-y"]

    if has_bg_file:
        cmd += ["-i", temp_bg_path]
    else:
        cmd += ["-f", "lavfi", "-i", f"color=c=black:s={video_width}x{video_height}:r=30:d={total_duration:.2f}"]

    # Input 1: Timed subtitle PNG concat stream
    cmd += ["-f", "concat", "-safe", "0", "-i", concat_file_path]
    # Input 2: Audio stream
    cmd += ["-i", audio_with_bgm]

    has_logo = logo_path and os.path.exists(logo_path) and os.path.getsize(logo_path) > 0
    if has_logo:
        cmd += ["-i", logo_path]  # Input 3

    # Filter graph
    filters = []
    if has_bg_file:
        filters.append(f"[0:v]fps=30,setpts=PTS-STARTPTS[bg]")
    else:
        filters.append(f"[0:v]setpts=PTS-STARTPTS[bg]")

    filters.append(f"[1:v]format=rgba[sub]")

    if has_logo:
        filters.append(f"[3:v]scale={logo_size}:-1,format=rgba,colorchannelmixer=aa={logo_opacity:.2f}[logo]")
        filters.append(f"[bg][sub]overlay=x=0:y=0:format=auto[v1]")

        margin = 35
        logo_y_bottom = video_height - logo_size - margin
        pos_map = {
            "top_right": (video_width - logo_size - margin, margin),
            "top_left": (margin, margin),
            "top_center": ((video_width - logo_size) // 2, margin),
            "bottom_right": (video_width - logo_size - margin, logo_y_bottom),
            "bottom_left": (margin, logo_y_bottom),
        }
        lx, ly = pos_map.get(str(logo_position).lower(), pos_map["top_right"])
        filters.append(f"[v1][logo]overlay=x={lx}:y={ly}:format=auto[vout]")
    else:
        filters.append(f"[bg][sub]overlay=x=0:y=0:format=auto[vout]")

    filter_graph = ";".join(filters)

    cmd += [
        "-filter_complex", filter_graph,
        "-map", "[vout]",
        "-map", "2:a",
        "-c:v", "libx264",
        "-preset", "superfast",
        "-pix_fmt", "yuv420p",
        "-c:a", "aac",
        "-b:a", "192k",
        "-shortest",
        output_path
    ]

    log("🚀 Launching Native FFmpeg Composer (Superfast Mode)...")
    result = subprocess.run(cmd, capture_output=True, text=True)

    if result.returncode == 0 and os.path.exists(output_path) and os.path.getsize(output_path) > 10000:
        log("⚡ FFmpeg video composition completed in seconds!")
        return

    log(f"⚠️ FFmpeg composition warning (Code {result.returncode}): {result.stderr[-300:] if result.stderr else ''}")
