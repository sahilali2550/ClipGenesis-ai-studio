"""
AI Video Enhancement - Background removal, color grading, upscaling, slow motion, speed ramp.
"""

import os
import subprocess
from typing import Optional, Tuple
from loguru import logger


class VideoEnhancer:
    """AI-powered video enhancement pipeline"""

    @staticmethod
    def remove_background(input_path: str, output_path: str = "") -> Optional[str]:
        """Remove video background using AI (rembg for images, frame-by-frame processing)"""
        try:
            from rembg import remove, new_session
            from PIL import Image
            import numpy as np

            if not output_path:
                output_path = input_path.replace(".mp4", "_no_bg.mp4")

            # Use frame-by-frame processing
            import cv2
            cap = cv2.VideoCapture(input_path)
            fps = cap.get(cv2.CAP_PROP_FPS)
            width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

            # Ensure even dimensions
            width = width // 2 * 2
            height = height // 2 * 2

            out = cv2.VideoWriter(output_path, cv2.VideoWriter_fourcc(*'mp4v'),
                                  fps, (width, height))

            session = new_session("u2net")
            frame_count = 0

            while True:
                ret, frame = cap.read()
                if not ret:
                    break

                # Remove background
                pil_img = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
                result = remove(pil_img, session=session)
                result_bgr = cv2.cvtColor(np.array(result), cv2.COLOR_RGB2BGR)
                out.write(result_bgr)
                frame_count += 1

            cap.release()
            out.release()
            logger.success(f"Background removed: {frame_count} frames processed")
            return output_path

        except ImportError:
            logger.warning("Background removal requires: pip install rembg opencv-python")
            return None
        except Exception as e:
            logger.error(f"Background removal failed: {e}")
            return None

    @staticmethod
    def apply_color_grade(input_path: str, preset: str = "cinematic",
                          output_path: str = "") -> Optional[str]:
        """Apply color grading preset using FFmpeg"""
        color_presets = {
            "cinematic": {
                "eq": "saturation=1.2:contrast=1.1:brightness=0.02",
                "curves": "preset=crossprocess"
            },
            "vintage": {
                "eq": "saturation=0.8:contrast=1.1:brightness=0.05",
                "curves": "preset=sepia"
            },
            "vivid": {
                "eq": "saturation=1.5:contrast=1.2",
                "curves": "preset=vintage"
            },
            "noir": {
                "eq": "saturation=0:contrast=1.3:brightness=0.0",
                "curves": "preset=line"
            },
            "warm": {
                "eq": "saturation=1.1:brightness=0.05",
                "colortemperature": "temperature=6500"
            },
            "cool": {
                "eq": "saturation=1.0:brightness=-0.02",
                "colortemperature": "temperature=5000"
            },
        }

        preset_config = color_presets.get(preset, color_presets["cinematic"])
        if not output_path:
            output_path = input_path.replace(".mp4", f"_{preset}.mp4")

        try:
            cmd = [
                "ffmpeg", "-y", "-i", input_path,
                "-vf", preset_config["eq"],
                "-c:v", "libx264", "-crf", "18", "-preset", "medium",
                "-c:a", "copy",
                output_path
            ]
            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode == 0:
                logger.success(f"Color grade applied: {preset}")
                return output_path
            else:
                logger.error(f"FFmpeg color grade failed: {result.stderr[-500:]}")
        except Exception as e:
            logger.error(f"Color grading failed: {e}")
        return None

    @staticmethod
    def upscale_video(input_path: str, target_scale: int = 2,
                      output_path: str = "") -> Optional[str]:
        """Upscale video using Real-ESRGAN or basic FFmpeg lanczos"""
        if not output_path:
            output_path = input_path.replace(".mp4", f"_upscaled{target_scale}x.mp4")

        try:
            # Try Real-ESRGAN if available
            from realesrgan import RealESRGANer
            from basicsr.archs.rrdbnet_arch import RRDBNet
            import cv2
            import numpy as np
            import torch

            model = RRDBNet(num_in_ch=3, num_out_ch=3, num_feat=64,
                            num_block=23, num_grow_ch=32, scale=target_scale)
            upsampler = RealESRGANer(
                scale=target_scale,
                model_path='weights/RealESRGAN_x4plus.pth',
                model=model,
                tile=400,
                tile_pad=10,
                pre_pad=0,
                half=False
            )

            cap = cv2.VideoCapture(input_path)
            fps = cap.get(cv2.CAP_PROP_FPS)
            w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)) * target_scale
            h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT)) * target_scale
            w = w // 2 * 2
            h = h // 2 * 2

            out = cv2.VideoWriter(output_path, cv2.VideoWriter_fourcc(*'mp4v'), fps, (w, h))

            while True:
                ret, frame = cap.read()
                if not ret:
                    break
                output, _ = upsampler.enhance(frame, outscale=target_scale)
                out.write(output)

            cap.release()
            out.release()
            logger.success(f"Video upscaled {target_scale}x with Real-ESRGAN")
            return output_path

        except ImportError:
            logger.info("Real-ESRGAN not available, using FFmpeg lanczos upscale")
            try:
                cmd = [
                    "ffmpeg", "-y", "-i", input_path,
                    "-vf", f"scale=iw*{target_scale}:ih*{target_scale}:flags=lanczos",
                    "-c:v", "libx264", "-crf", "18", "-preset", "medium",
                    "-c:a", "copy", output_path
                ]
                result = subprocess.run(cmd, capture_output=True, text=True)
                if result.returncode == 0:
                    logger.success(f"Video upscaled {target_scale}x with lanczos")
                    return output_path
            except Exception as e:
                logger.error(f"Upscale failed: {e}")
        return None

    @staticmethod
    def apply_speed_ramp(input_path: str, speed_curve: list,
                         output_path: str = "") -> Optional[str]:
        """Apply variable speed effect (speed ramp) to video

        speed_curve: list of (time_in_seconds, speed_multiplier) tuples
        Example: [(0, 0.5), (2, 1.0), (4, 1.5), (6, 0.5)]
        """
        if not output_path:
            output_path = input_path.replace(".mp4", "_speedramp.mp4")

        try:
            # Build FFmpeg setpts filter for speed ramp
            # Speed ramp using complex filter
            filter_parts = []
            for i, (t, speed) in enumerate(speed_curve):
                filter_parts.append(f"between(t,{t},{speed_curve[i+1][0] if i+1 < len(speed_curve) else 999})")

            # Simplified: use single speed change
            if len(speed_curve) == 2:
                start_time, start_speed = speed_curve[0]
                end_time, end_speed = speed_curve[1]

                # Use atempo filter (0.5-2.0 range, chain for higher values)
                atempo = end_speed
                atempo_chain = ""
                while atempo > 2.0:
                    atempo_chain += "atempo=2.0,"
                    atempo /= 2.0
                while atempo < 0.5:
                    atempo_chain += "atempo=0.5,"
                    atempo /= 0.5
                atempo_chain += f"atempo={atempo:.2f}"

                cmd = [
                    "ffmpeg", "-y", "-i", input_path,
                    "-filter:v", atempo_chain,
                    "-c:a", "aac", "-b:a", "320k",
                    output_path
                ]
                result = subprocess.run(cmd, capture_output=True, text=True)
                if result.returncode == 0:
                    logger.success(f"Speed ramp applied: {speed_curve}")
                    return output_path
        except Exception as e:
            logger.error(f"Speed ramp failed: {e}")
        return None

    @staticmethod
    def apply_slow_motion(input_path: str, factor: float = 0.5,
                          output_path: str = "") -> Optional[str]:
        """Apply slow motion effect (factor < 1.0 = slower, > 1.0 = faster)"""
        if not output_path:
            output_path = input_path.replace(".mp4", f"_slow{int(factor*100)}.mp4")

        try:
            # FFmpeg atempo filter
            atempo = factor
            atempo_chain = ""
            while atempo > 2.0:
                atempo_chain += "atempo=2.0,"
                atempo /= 2.0
            while atempo < 0.5:
                atempo_chain += "atempo=0.5,"
                atempo /= 0.5
            atempo_chain += f"atempo={atempo:.2f}"

            cmd = [
                "ffmpeg", "-y", "-i", input_path,
                "-filter:v", atempo_chain,
                "-c:a", "aac", "-b:a", "320k",
                output_path
            ]
            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode == 0:
                logger.success(f"Slow motion applied: {factor}x")
                return output_path
        except Exception as e:
            logger.error(f"Slow motion failed: {e}")
        return None

    @staticmethod
    def add_green_screen(input_path: str, background_path: str,
                         output_path: str = "") -> Optional[str]:
        """Replace video background with a custom image/video"""
        if not output_path:
            output_path = input_path.replace(".mp4", "_greenscreen.mp4")

        try:
            cmd = [
                "ffmpeg", "-y",
                "-i", input_path,
                "-i", background_path,
                "-filter_complex",
                "[0:v]chromakey=0x00ff00:0.1:0.2[fg];[1:v][fg]overlay=0:0",
                "-c:a", "copy",
                output_path
            ]
            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode == 0:
                logger.success("Green screen replacement applied")
                return output_path
        except Exception as e:
            logger.error(f"Green screen failed: {e}")
        return None
