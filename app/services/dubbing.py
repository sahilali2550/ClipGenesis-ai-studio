import os
import re
import shutil
from loguru import logger

from app.services import voice
from app.utils import utils

try:
    from faster_whisper import WhisperModel
    FASTER_WHISPER_AVAILABLE = True
except ImportError:
    FASTER_WHISPER_AVAILABLE = False

try:
    from moviepy.video.io.VideoFileClip import VideoFileClip
    from moviepy.audio.io.AudioFileClip import AudioFileClip
    from moviepy.audio.AudioClip import concatenate_audioclips
    MOVIEPY_AVAILABLE = True
except ImportError:
    try:
        from moviepy import VideoFileClip, AudioFileClip, concatenate_audioclips
        MOVIEPY_AVAILABLE = True
    except ImportError:
        MOVIEPY_AVAILABLE = False

def format_srt_time(seconds: float) -> str:
    millis = int((seconds % 1) * 1000)
    total_seconds = int(seconds)
    mins, secs = divmod(total_seconds, 60)
    hrs, mins = divmod(mins, 60)
    return f"{hrs:02d}:{mins:02d}:{secs:02d},{millis:03d}"


_whisper_model_cache = {}


def get_whisper_model(model_size: str = "base"):
    """Lazy load faster-whisper model."""
    global _whisper_model_cache
    if model_size not in _whisper_model_cache:
        logger.info(f"Loading faster-whisper model ({model_size}) on CPU...")
        _whisper_model_cache[model_size] = WhisperModel(model_size, device="cpu", compute_type="int8")
        logger.success("Whisper model loaded.")
    return _whisper_model_cache[model_size]


def transcribe_media(input_file: str, model_size: str = "base") -> list[dict]:
    """
    Transcribe audio or video file and return list of segments:
    [ {"start": 0.0, "end": 2.5, "text": "Hello world"}, ... ]
    """
    if not FASTER_WHISPER_AVAILABLE:
        raise RuntimeError("faster-whisper is not installed.")

    model = get_whisper_model(model_size)
    logger.info(f"Transcribing media file: {input_file}...")
    
    segments, info = model.transcribe(input_file, beam_size=5, word_timestamps=True)
    
    result_segments = []
    for seg in segments:
        text_clean = seg.text.strip()
        if text_clean:
            result_segments.append({
                "start": seg.start,
                "end": seg.end,
                "text": text_clean,
                "words": [{"word": w.word, "start": w.start, "end": w.end} for w in seg.words] if seg.words else []
            })
            
    logger.success(f"Transcription complete: {len(result_segments)} segments detected. Language: {info.language}")
    return result_segments


def auto_dub_media(
    input_file: str,
    target_voice: str,
    speech_rate: float = 1.0,
    model_size: str = "base",
    output_filename: str = "dubbed_output.mp4",
) -> tuple[str, str]:
    """
    Complete AI Auto-Dubbing Pipeline:
    1. Transcribe original media with Whisper
    2. Re-voice each segment using target voice (Kokoro/Edge/Chatterbox)
    3. Concatenate new audio segments preserving natural timing
    4. Replace original audio in video with dubbed audio
    Returns (dubbed_media_path, srt_subtitle_path).
    """
    output_dir = os.path.join(utils.root_dir(), "storage", "dubbing")
    os.makedirs(output_dir, exist_ok=True)

    logger.info(f"Starting Auto-Dubbing for {input_file} -> Target Voice: {target_voice}")

    # 1. Transcribe
    segments = transcribe_media(input_file, model_size=model_size)
    if not segments:
        raise RuntimeError("No spoken audio detected in input file.")

    # 2. Re-voice segments
    temp_audio_clips = []
    srt_lines = []
    
    for idx, seg in enumerate(segments):
        text = seg["text"]
        start_time = seg["start"]
        end_time = seg["end"]
        
        seg_file = os.path.join(output_dir, f"dub_seg_{idx}.wav")
        
        # Generate new voice audio
        voice.tts(
            text=text,
            voice_name=target_voice,
            voice_rate=speech_rate,
            voice_file=seg_file,
        )
        
        if os.path.exists(seg_file):
            temp_audio_clips.append(seg_file)
            
        # Build SRT entry
        start_srt = format_srt_time(start_time)
        end_srt = format_srt_time(end_time)
        srt_lines.append(f"{idx + 1}\n{start_srt} --> {end_srt}\n{text}\n")

    # Save SRT subtitles file
    srt_path = os.path.join(output_dir, output_filename.replace(".mp4", ".srt").replace(".mp3", ".srt"))
    with open(srt_path, "w", encoding="utf-8") as f:
        f.write("\n".join(srt_lines))

    # 3. Concatenate dubbed audio clips
    audio_clips = [AudioFileClip(f) for f in temp_audio_clips if os.path.exists(f)]
    if not audio_clips:
        raise RuntimeError("Failed to generate dubbed audio segments.")

    combined_audio = concatenate_audioclips(audio_clips)
    combined_audio_path = os.path.join(output_dir, "dubbed_track.wav")
    combined_audio.write_audiofile(combined_audio_path, logger=None)

    # 4. If input is video (mp4), merge new audio with original video stream
    is_video = input_file.lower().endswith((".mp4", ".mov", ".avi", ".mkv"))
    final_output_path = os.path.join(output_dir, output_filename)

    if is_video:
        logger.info("Merging dubbed audio track into video container...")
        video_clip = VideoFileClip(input_file)
        dubbed_audio_clip = AudioFileClip(combined_audio_path)
        
        # Set new audio on video clip
        if hasattr(video_clip, "with_audio"):
            final_video = video_clip.with_audio(dubbed_audio_clip)
        else:
            final_video = video_clip.set_audio(dubbed_audio_clip)
        final_video.write_videofile(final_output_path, codec="libx264", audio_codec="aac", logger=None)
        
        video_clip.close()
        dubbed_audio_clip.close()
        final_video.close()
    else:
        # Output is audio only
        shutil.copy(combined_audio_path, final_output_path)

    # Clean up segment clips
    for c in audio_clips:
        c.close()
    combined_audio.close()
    for f in temp_audio_clips:
        try:
            os.remove(f)
        except Exception:
            pass

    logger.success(f"Auto-Dubbing completed successfully! Output: {final_output_path}")
    return final_output_path, srt_path
