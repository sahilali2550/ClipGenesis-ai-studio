"""
AI Image/Video Generation - Generate custom images/videos, auto thumbnails, scene detection.
"""

import os
import uuid
import json
import subprocess
import requests
import urllib.parse
from typing import Optional, List, Dict
from loguru import logger
from app.utils import utils
from app.config import config


class AIMediaGenerator:
    """AI-powered media generation for missing clips and thumbnails"""

    def generate_image(self, prompt: str, width: int = 1080, height: int = 1920,
                       output_dir: str = "") -> Optional[str]:
        """Generate AI image using Pollinations.ai (free, no API key required)"""
        if not output_dir:
            output_dir = utils.storage_dir("ai_images", create=True)

        encoded = urllib.parse.quote(prompt + " highly detailed cinematic")
        url = f"https://image.pollinations.ai/prompt/{encoded}?width={width}&height={height}&nologo=true"

        try:
            logger.info(f"Generating AI image: {prompt[:60]}...")
            response = requests.get(url, timeout=60)
            if response.status_code == 200:
                img_path = os.path.join(output_dir, f"ai_{uuid.uuid4().hex[:8]}.jpg")
                with open(img_path, "wb") as f:
                    f.write(response.content)
                logger.success(f"AI image generated: {img_path}")
                return img_path
        except Exception as e:
            logger.error(f"AI image generation failed: {e}")
        return None

    def generate_thumbnail(self, title: str, style: str = "youtube",
                           width: int = 1280, height: int = 720) -> Optional[str]:
        """Generate AI thumbnail for a video"""
        style_prompts = {
            "youtube": f"professional YouTube thumbnail for: {title}. Bold text, colorful, eye-catching, high contrast",
            "tiktok": f"vertical TikTok cover image for: {title}. Trendy, bold text, neon colors",
            "educational": f"clean educational thumbnail for: {title}. Professional, minimalist, informative",
            "dramatic": f"dramatic cinematic thumbnail for: {title}. Dark background, spotlight, tension",
            "fun": f"fun playful thumbnail for: {title}. Bright colors, cartoon style, energetic",
        }
        prompt = style_prompts.get(style, style_prompts["youtube"])
        return self.generate_image(prompt, width, height)

    def image_to_video(self, image_path: str, duration: int = 5,
                       effect: str = "zoom_in") -> Optional[str]:
        """Convert image to short video clip with motion effect"""
        output_path = image_path + ".mp4"

        effects = {
            "zoom_in": "zoompan=z='min(zoom+0.0015,1.5)':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d=150:s=1080x1920:fps=30",
            "zoom_out": "zoompan=z='if(eq(on,1),1.5,max(1.0,zoom-0.0015))':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d=150:s=1080x1920:fps=30",
            "pan_left": "zoompan=z='1.1':x='iw*0.3*(1-on/150)':y='ih/2-(ih/zoom/2)':d=150:s=1080x1920:fps=30",
            "pan_right": "zoompan=z='1.1':x='iw*0.3*(on/150)':y='ih/2-(ih/zoom/2)':d=150:s=1080x1920:fps=30",
            "static": "zoompan=z='1':d=150:s=1080x1920:fps=30",
        }
        vf = effects.get(effect, effects["zoom_in"])

        try:
            cmd = [
                "ffmpeg", "-y",
                "-loop", "1", "-i", image_path,
                "-vf", vf,
                "-t", str(duration),
                "-c:v", "libx264", "-crf", "18", "-pix_fmt", "yuv420p",
                output_path
            ]
            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode == 0:
                logger.success(f"Image to video: {output_path} ({effect})")
                return output_path
        except Exception as e:
            logger.error(f"Image to video failed: {e}")
        return None

    def detect_scenes(self, video_path: str, threshold: float = 0.3) -> List[Dict]:
        """Detect scene changes in a video using FFmpeg"""
        try:
            cmd = [
                "ffprobe", "-v", "quiet",
                "-f", "lavfi",
                "-i", f"movie={video_path},select=gt(scene\\,{threshold})",
                "-show_entries", "frame=pts_time,pkt_pts_time",
                "-of", "json"
            ]
            result = subprocess.run(cmd, capture_output=True, text=True)

            if result.returncode == 0 and result.stdout.strip():
                data = json.loads(result.stdout)
                scenes = []
                for frame in data.get("frames", []):
                    scenes.append({
                        "time": float(frame.get("pts_time", frame.get("pkt_pts_time", 0))),
                    })
                logger.info(f"Detected {len(scenes)} scene changes in {video_path}")
                return scenes
        except Exception as e:
            logger.error(f"Scene detection failed: {e}")
        return []

    def generate_batch_images(self, prompts: List[str], width: int = 1080,
                               height: int = 1920) -> List[str]:
        """Generate multiple images in batch"""
        paths = []
        for prompt in prompts:
            path = self.generate_image(prompt, width, height)
            if path:
                paths.append(path)
        return paths


# Global instance
ai_media = AIMediaGenerator()
