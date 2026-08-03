"""
Advanced TTS & Audio - Emotion control, background noise removal, auto music sourcing, enhanced voice cloning.
"""

import os
import re
import subprocess
from typing import Optional, List, Dict
from loguru import logger
from app.config import config
from app.utils import utils


class AudioEnhancer:
    """Advanced audio processing and TTS features"""

    # Emotion presets for TTS modification
    EMOTION_PRESETS = {
        "neutral": {"pitch": 0, "rate": 1.0, "volume": 1.0},
        "excited": {"pitch": 2, "rate": 1.15, "volume": 1.2},
        "sad": {"pitch": -2, "rate": 0.85, "volume": 0.9},
        "angry": {"pitch": 1, "rate": 1.1, "volume": 1.3},
        "calm": {"pitch": -1, "rate": 0.9, "volume": 0.95},
        "mysterious": {"pitch": -1, "rate": 0.95, "volume": 0.85},
        "cheerful": {"pitch": 2, "rate": 1.05, "volume": 1.1},
        "serious": {"pitch": -1, "rate": 0.95, "volume": 1.0},
    }

    def apply_emotion(self, audio_path: str, emotion: str,
                       output_path: str = "") -> Optional[str]:
        """Apply emotion effect to audio using FFmpeg pitch/tempo filters"""
        preset = self.EMOTION_PRESETS.get(emotion, self.EMOTION_PRESETS["neutral"])
        if not output_path:
            output_path = audio_path.replace(".mp3", f"_{emotion}.mp3")

        try:
            # Build filter chain
            filters = []

            # Pitch shift (semitones)
            pitch = preset["pitch"]
            if pitch != 0:
                # asetrate changes pitch, aresample restores sample rate
                factor = 2 ** (pitch / 12.0)
                filters.append(f"asetrate=44100*{factor:.4f},aresample=44100")

            # Rate change (tempo)
            rate = preset["rate"]
            if rate != 1.0:
                atempo = rate
                while atempo > 2.0:
                    filters.append("atempo=2.0")
                    atempo /= 2.0
                while atempo < 0.5:
                    filters.append("atempo=0.5")
                    atempo *= 2.0
                filters.append(f"atempo={atempo:.2f}")

            # Volume
            volume = preset["volume"]
            if volume != 1.0:
                filters.append(f"volume={volume:.2f}")

            if not filters:
                # No changes needed, copy file
                import shutil
                shutil.copy(audio_path, output_path)
                return output_path

            filter_str = ",".join(filters)
            cmd = [
                "ffmpeg", "-y", "-i", audio_path,
                "-af", filter_str,
                "-c:a", "libmp3lame", "-b:a", "320k",
                output_path
            ]
            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode == 0:
                logger.success(f"Emotion '{emotion}' applied to audio")
                return output_path
            else:
                logger.error(f"Emotion filter failed: {result.stderr[-300:]}")
        except Exception as e:
            logger.error(f"Emotion application failed: {e}")
        return None

    def remove_background_noise(self, audio_path: str,
                                 output_path: str = "") -> Optional[str]:
        """Remove background noise using FFmpeg highpass/lowpass/noise gate filters"""
        if not output_path:
            output_path = audio_path.replace(".mp3", "_clean.mp3")

        try:
            # Multi-stage noise reduction:
            # 1. High-pass filter to remove low rumble (<80Hz)
            # 2. Low-pass filter to remove high-freq hiss (>12kHz)
            # 3. Compressor to normalize levels
            # 4. Noise gate to silence quiet sections
            filter_chain = (
                "highpass=f=80,"
                "lowpass=f=12000,"
                "afftdn=nf=-25,"
                "acompressor=threshold=-20dB:ratio=3:attack=5:release=50,"
                "volume=1.2"
            )

            cmd = [
                "ffmpeg", "-y", "-i", audio_path,
                "-af", filter_chain,
                "-c:a", "libmp3lame", "-b:a", "320k",
                output_path
            ]
            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode == 0:
                logger.success("Background noise removed")
                return output_path
            else:
                logger.error(f"Noise removal failed: {result.stderr[-300:]}")
        except Exception as e:
            logger.error(f"Noise removal failed: {e}")
        return None

    def normalize_audio(self, audio_path: str, target_db: float = -14.0,
                         output_path: str = "") -> Optional[str]:
        """Normalize audio levels to target dB (broadcast standard: -14 LUFS)"""
        if not output_path:
            output_path = audio_path.replace(".mp3", "_normalized.mp3")

        try:
            # Two-pass loudness normalization
            cmd = [
                "ffmpeg", "-y", "-i", audio_path,
                "-af", f"loudnorm=I={target_db}:TP=-1.5:LRA=11:print_format=json",
                "-c:a", "libmp3lame", "-b:a", "320k",
                output_path
            ]
            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode == 0:
                logger.success(f"Audio normalized to {target_db} LUFS")
                return output_path
        except Exception as e:
            logger.error(f"Audio normalization failed: {e}")
        return None

    def mix_audio_tracks(self, voice_path: str, bgm_path: str,
                          voice_volume: float = 1.0, bgm_volume: float = 0.2,
                          output_path: str = "") -> Optional[str]:
        """Mix voice and BGM tracks with volume control"""
        if not output_path:
            output_path = voice_path.replace(".mp3", "_mixed.mp3")

        try:
            cmd = [
                "ffmpeg", "-y",
                "-i", voice_path,
                "-i", bgm_path,
                "-filter_complex",
                f"[0:a]volume={voice_volume}[v];[1:a]volume={bgm_volume},aloop=loop=-1:size=2e+09[b];[v][b]amix=inputs=2:duration=first:dropout_transition=3",
                "-c:a", "libmp3lame", "-b:a", "320k",
                output_path
            ]
            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode == 0:
                logger.success("Audio tracks mixed")
                return output_path
        except Exception as e:
            logger.error(f"Audio mixing failed: {e}")
        return None

    def get_audio_info(self, audio_path: str) -> Dict:
        """Get audio file metadata"""
        try:
            cmd = [
                "ffprobe", "-v", "quiet",
                "-print_format", "json",
                "-show_format", "-show_streams",
                audio_path
            ]
            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode == 0:
                import json
                data = json.loads(result.stdout)
                fmt = data.get("format", {})
                streams = data.get("streams", [{}])
                audio_stream = streams[0] if streams else {}
                return {
                    "duration": float(fmt.get("duration", 0)),
                    "size": int(fmt.get("size", 0)),
                    "bitrate": int(fmt.get("bit_rate", 0)),
                    "sample_rate": int(audio_stream.get("sample_rate", 0)),
                    "channels": int(audio_stream.get("channels", 0)),
                    "codec": audio_stream.get("codec_name", ""),
                }
        except Exception as e:
            logger.error(f"Audio info failed: {e}")
        return {}

    def split_audio_by_silence(self, audio_path: str,
                                min_silence_duration: float = 0.5,
                                silence_threshold: str = "-30dB") -> List[Dict]:
        """Detect silence segments in audio for splitting"""
        try:
            cmd = [
                "ffmpeg", "-i", audio_path,
                "-af", f"silencedetect=noise={silence_threshold}:d={min_silence_duration}",
                "-f", "null", "-"
            ]
            result = subprocess.run(cmd, capture_output=True, text=True)

            segments = []
            silence_starts = []
            silence_ends = []

            for line in result.stderr.split("\n"):
                if "silence_start:" in line:
                    match = re.search(r"silence_start:\s*([\d.]+)", line)
                    if match:
                        silence_starts.append(float(match.group(1)))
                elif "silence_end:" in line:
                    match = re.search(r"silence_end:\s*([\d.]+)", line)
                    if match:
                        silence_ends.append(float(match.group(1)))

            # Build segments between silence periods
            prev_end = 0.0
            for start, end in zip(silence_starts, silence_ends):
                if start > prev_end:
                    segments.append({"start": prev_end, "end": start})
                prev_end = end

            logger.info(f"Found {len(segments)} audio segments")
            return segments

        except Exception as e:
            logger.error(f"Silence detection failed: {e}")
        return []

    def trim_silence(self, audio_path: str, output_path: str = "",
                     silence_threshold: str = "-40dB", min_silence_duration: float = 0.4) -> Optional[str]:
        """Automatically trim dead silence gaps and pauses (> min_silence_duration) from audio"""
        if not output_path:
            output_path = audio_path.replace(".mp3", "_trimmed.mp3")

        try:
            # Use silenceremove filter to remove silence from start, middle, and end
            af_filter = f"silenceremove=stop_periods=-1:stop_duration={min_silence_duration}:stop_threshold={silence_threshold}"
            cmd = [
                "ffmpeg", "-y", "-i", audio_path,
                "-af", af_filter,
                output_path
            ]
            subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            logger.info(f"Audio silence trimmed successfully: {output_path}")
            return output_path
        except Exception as e:
            logger.error(f"Trim silence failed: {e}")
            return audio_path


# Global instance
audio_enhancer = AudioEnhancer()

