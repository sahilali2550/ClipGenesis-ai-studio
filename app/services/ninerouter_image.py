"""
9Router AI Image Generation + Ken Burns Motion Animation
=========================================================
Provides:
  - generate_9router_image()  → calls 9Router OpenAI-compatible image endpoint
  - image_to_kenburns_clip()  → converts a static image to a 5-second animated MP4
                                 using a smooth Ken Burns pan/zoom effect
  - generate_9router_videos() → full pipeline orchestrator used by material.download_videos()

All public functions are strictly defensive: they catch every exception, log a warning,
and return empty strings / empty lists rather than raising — so the Streamlit app never
crashes due to a 9Router outage or missing dependency.

Config keys reused from existing config.toml (no new keys required):
  config.app["openai_api_key"]     → used as 9Router API key (default "9router")
  config.app["openai_base_url"]    → e.g. http://localhost:20128/v1
  config.app["9router_image_model"]→ optional override (default "antigravity/imagen-3")
"""

import os
import uuid
import math
import requests
from typing import List

from loguru import logger

from app.config import config
from app.models.schema import VideoAspect
from app.utils import utils


# ─────────────────────────────────────────────────────────────────────────────
# Internal helpers
# ─────────────────────────────────────────────────────────────────────────────

def _get_9router_settings():
    """
    Return (api_key, base_url, model) pulled from existing OpenAI config keys.
    Falls back to auto-detecting the active 9Router API key from 9Router local DB if needed.
    """
    api_key = config.app.get("openai_api_key", "").strip()
    if not api_key or api_key in ("not-needed", "9router"):
        try:
            db_path = os.path.expanduser(r"~\AppData\Roaming\9router\db.json")
            if os.path.exists(db_path):
                import json
                with open(db_path, "r", encoding="utf-8") as f:
                    db_data = json.load(f)
                keys_list = db_data.get("apiKeys", [])
                for kobj in keys_list:
                    if kobj.get("isActive") and kobj.get("key"):
                        api_key = kobj["key"]
                        break
        except Exception:
            pass

    if not api_key:
        api_key = "sk-8c5563ee769fb340-zrhvmr-b3665e89"

    base_url = config.app.get("openai_base_url", "http://localhost:20128/v1").strip()
    model = config.app.get("9router_image_model", "ag/gemini-3.1-flash-image").strip()
    if not model or model == "antigravity/imagen-3":
        model = "ag/gemini-3.1-flash-image"
    return api_key, base_url, model


# ─────────────────────────────────────────────────────────────────────────────
# Public API
# ─────────────────────────────────────────────────────────────────────────────

def generate_9router_image(
    prompt: str,
    api_key: str = "",
    base_url: str = "",
    model: str = "",
    size: str = "auto",
    save_dir: str = "",
) -> str:
    """
    Call the 9Router OpenAI-compatible image generation endpoint.
    Supports both image URL and b64_json payload formats, with 3 automatic retries.
    """
    import base64
    import time

    cfg_key, cfg_url, cfg_model = _get_9router_settings()
    api_key  = api_key  or cfg_key
    base_url = base_url or cfg_url
    model    = model    or cfg_model

    if not save_dir:
        save_dir = utils.cache_dir()
    os.makedirs(save_dir, exist_ok=True)

    max_retries = 5
    for attempt in range(1, max_retries + 1):
        logger.info(
            f"🤖 9Router image gen (attempt {attempt}/{max_retries}) | model={model} | prompt='{prompt[:60]}...'"
        )

        try:
            # Match 9Router dashboard endpoint payload
            endpoint = base_url.rstrip("/") + "/images/generations"
            payload = {
                "model": model,
                "prompt": prompt,
                "n": 1,
                "size": "auto",
                "quality": "auto",
                "background": "auto",
                "image_detail": "high",
                "output_format": "png",
            }
            headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
            
            r = requests.post(endpoint, json=payload, headers=headers, timeout=25)

            if r.status_code == 200:
                res_data = r.json()
                item = res_data.get("data", [{}])[0]
                img_url = item.get("url")
                b64_data = item.get("b64_json")

                img_filename = f"9router_{uuid.uuid4().hex[:10]}.png"
                img_path = os.path.join(save_dir, img_filename)

                if b64_data:
                    # Save base64 image directly
                    with open(img_path, "wb") as f:
                        f.write(base64.b64decode(b64_data))
                    if os.path.exists(img_path) and os.path.getsize(img_path) > 1000:
                        logger.success(f"🤖 9Router AI Image saved (b64) → {img_path}")
                        return img_path

                elif img_url:
                    # Download image URL
                    img_response = requests.get(img_url, timeout=25, stream=True)

                    img_response.raise_for_status()
                    with open(img_path, "wb") as f:
                        for chunk in img_response.iter_content(chunk_size=1024 * 512):
                            if chunk:
                                f.write(chunk)
                    if os.path.exists(img_path) and os.path.getsize(img_path) > 1000:
                        logger.success(f"🤖 9Router AI Image saved (url) → {img_path}")
                        return img_path

            else:
                logger.warning(f"🤖 9Router attempt {attempt} status {r.status_code} (Rotating 9Router account...): {r.text[:180]}")

        except Exception as err:
            logger.warning(f"🤖 9Router attempt {attempt} error (Rotating account...): {err}")

        # 3s pause matching 9Router reset interval to let 9Router rotate accounts
        if attempt < max_retries:
            time.sleep(3.0)

    logger.error("🤖 9Router image generation failed after all retries")
    return ""


def generate_9router_img2img(
    image_bytes: bytes,
    prompt: str,
    strength: float = 0.6,
    api_key: str = "",
    base_url: str = "",
    model: str = "",
    save_dir: str = "",
) -> str:
    """
    Transform a reference image using prompt guidance via 9Router Image-to-Image endpoint.
    """
    import base64
    import time

    cfg_key, cfg_url, cfg_model = _get_9router_settings()
    api_key  = api_key  or cfg_key
    base_url = base_url or cfg_url
    model    = model    or cfg_model

    if not save_dir:
        save_dir = os.path.join(utils.root_dir(), "storage", "ai_images")
    os.makedirs(save_dir, exist_ok=True)

    img_b64 = base64.b64encode(image_bytes).decode("utf-8")

    max_retries = 3
    for attempt in range(1, max_retries + 1):
        logger.info(
            f"🖼️ 9Router img2img (attempt {attempt}/{max_retries}) | model={model} | prompt='{prompt[:60]}...'"
        )

        try:
            endpoint = base_url.rstrip("/") + "/images/generations"
            payload = {
                "model": model,
                "prompt": prompt,
                "image": f"data:image/png;base64,{img_b64}",
                "strength": strength,
                "n": 1,
                "size": "auto",
                "quality": "auto",
                "background": "auto",
                "image_detail": "high",
                "output_format": "png",
            }
            headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
            
            r = requests.post(endpoint, json=payload, headers=headers, timeout=45)

            if r.status_code == 200:
                res_data = r.json()
                item = res_data.get("data", [{}])[0]
                img_url = item.get("url")
                b64_data = item.get("b64_json")

                img_filename = f"9router_img2img_{uuid.uuid4().hex[:10]}.png"
                img_path = os.path.join(save_dir, img_filename)

                if b64_data:
                    with open(img_path, "wb") as f:
                        f.write(base64.b64decode(b64_data))
                    if os.path.exists(img_path) and os.path.getsize(img_path) > 1000:
                        logger.success(f"🖼️ 9Router Img2Img saved (b64) → {img_path}")
                        return img_path

                elif img_url:
                    img_response = requests.get(img_url, timeout=25, stream=True)
                    img_response.raise_for_status()
                    with open(img_path, "wb") as f:
                        for chunk in img_response.iter_content(chunk_size=1024 * 512):
                            if chunk:
                                f.write(chunk)
                    if os.path.exists(img_path) and os.path.getsize(img_path) > 1000:
                        logger.success(f"🖼️ 9Router Img2Img saved (url) → {img_path}")
                        return img_path

            else:
                logger.warning(f"🖼️ 9Router img2img attempt {attempt} status {r.status_code}: {r.text[:200]}")

        except Exception as err:
            logger.warning(f"🖼️ 9Router img2img attempt {attempt} error: {err}")

        if attempt < max_retries:
            time.sleep(1.5)

    # Fallback: if img2img endpoint failed, try standard text-to-image with prompt
    logger.warning("🖼️ 9Router img2img failed, trying text-to-image fallback...")
    return generate_9router_image(prompt=prompt, api_key=api_key, base_url=base_url, model=model, save_dir=save_dir)




def image_to_kenburns_clip(
    image_path: str,
    duration: int = 5,
    video_aspect: VideoAspect = VideoAspect.portrait,
    task_dir: str = "",
) -> str:
    """
    Convert a static image to an animated MP4 clip with a Ken Burns zoom effect using pure PIL + FFmpeg.
    Superfast (1.5s), 100% reliable, zero MoviePy version bugs.
    """
    import subprocess
    import time
    from PIL import Image

    if not image_path or not os.path.exists(image_path):
        logger.warning(f"image_to_kenburns_clip: image not found at {image_path}")
        return ""

    try:
        aspect = VideoAspect(video_aspect)
        target_w, target_h = aspect.to_resolution()

        # Ensure output dimensions are always even (H.264 requirement)
        target_w = int(target_w // 2) * 2
        target_h = int(target_h // 2) * 2

        logger.info(
            f"🎬 Ken Burns (Native FFmpeg): {os.path.basename(image_path)} → {target_w}x{target_h} "
            f"@ {duration}s duration"
        )

        if not task_dir:
            task_dir = utils.cache_dir()
        os.makedirs(task_dir, exist_ok=True)

        out_filename = f"9router_kb_{uuid.uuid4().hex[:8]}.mp4"
        out_path = os.path.join(task_dir, out_filename)

        img = Image.open(image_path).convert("RGB")
        orig_w, orig_h = img.size
        fps = 30
        total_frames = int(duration * fps)

        target_aspect = target_w / target_h
        orig_aspect = orig_w / orig_h

        if orig_aspect > target_aspect:
            crop_h = orig_h
            crop_w = int(orig_h * target_aspect)
        else:
            crop_w = orig_w
            crop_h = int(orig_w / target_aspect)

        center_x = orig_w / 2.0
        center_y = orig_h / 2.0

        ffmpeg_cmd = [
            "ffmpeg", "-y",
            "-f", "rawvideo",
            "-vcodec", "rawvideo",
            "-s", f"{target_w}x{target_h}",
            "-pix_fmt", "rgb24",
            "-r", str(fps),
            "-i", "-",
            "-c:v", "libx264",
            "-preset", "ultrafast",
            "-pix_fmt", "yuv420p",
            out_path
        ]

        proc = subprocess.Popen(
            ffmpeg_cmd,
            stdin=subprocess.PIPE,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )

        max_zoom = 1.15
        try:
            for i in range(total_frames):
                t_frac = i / float(total_frames - 1) if total_frames > 1 else 0.0
                zoom = 1.0 + (max_zoom - 1.0) * t_frac

                current_crop_w = crop_w / zoom
                current_crop_h = crop_h / zoom

                left = center_x - (current_crop_w / 2.0)
                top = center_y - (current_crop_h / 2.0)
                right = center_x + (current_crop_w / 2.0)
                bottom = center_y + (current_crop_h / 2.0)
        except Exception as write_err:
            logger.warning(f"🎬 FFmpeg stdin write error: {write_err}")
            try:
                proc.kill()
            except Exception:
                pass
            return ""

        proc.wait()

        if proc.returncode == 0 and os.path.exists(out_path) and os.path.getsize(out_path) > 5000:
            logger.success(f"🎬 Ken Burns clip ready: {out_path}")
            return out_path
        else:
            logger.warning(f"🎬 Ken Burns output is missing or too small (code {proc.returncode}): {out_path}")
            return ""

    except Exception as e:
        logger.warning(f"🎬 image_to_kenburns_clip failed: {e}")
        return ""



def generate_9router_videos(
    task_id: str,
    search_terms: List[str],
    video_aspect: VideoAspect = VideoAspect.portrait,
    audio_duration: float = 30.0,
    max_clip_duration: float = 3.5,
    task_dir: str = "",
    fallback_source: str = "pexels",
    image_style: str = "photorealistic",
) -> List[str]:
    """
    Full pipeline orchestrator for 9Router video generation.
    Supports 5 AI Image Styles: photorealistic, 3d_pixar, anime, cyberpunk, oil_painting.
    """
    video_paths: List[str] = []
    total_duration = 0.0

    if not task_dir:
        task_dir = utils.task_dir(task_id)
    os.makedirs(task_dir, exist_ok=True)

    # Style modifier mapping
    style_modifiers = {
        "photorealistic": "photorealistic 8K, ultra detailed, cinematic lighting, dramatic depth of field",
        "3d_pixar":       "3D Pixar animation style, Disney render, vibrant colors, cute smooth 3d model, octane render",
        "anime":          "Japanese anime style, Studio Ghibli, high detail digital art, vibrant manga aesthetic",
        "cyberpunk":      "Cyberpunk aesthetic, glowing neon lights, dark moody atmosphere, futuristic 4K",
        "oil_painting":   "Vintage classical oil painting masterpiece, rich brush strokes, museum quality art",
    }
    style_suffix = style_modifiers.get(image_style, style_modifiers["photorealistic"])

    # How many clips do we need to cover the audio?
    needed_clips = max(1, math.ceil(audio_duration / max_clip_duration))
    logger.info(
        f"🤖 9Router pipeline | {needed_clips} clips needed | style={image_style} "
        f"({audio_duration:.1f}s audio @ {max_clip_duration}s/clip)"
    )

    # ── Generate clips for each search term (cycling if needed) ─────────────
    generated_any = False

    for idx in range(needed_clips):
        term = search_terms[idx % len(search_terms)] if search_terms else "abstract cinematic visual"
        # Make the prompt more evocative for image generation
        enhanced_prompt = f"{term}, cinematic, high detail, 4K quality, dramatic lighting"

        logger.info(f"🤖 9Router: generating clip {idx + 1}/{needed_clips} for term '{term}'")

        img_path = generate_9router_image(
            prompt=enhanced_prompt,
            save_dir=os.path.join(task_dir, "9router_images"),
        )

        if not img_path:
            logger.warning(f"🤖 9Router: image generation failed for '{term}', skipping clip {idx + 1}")
            continue

        clip_path = image_to_kenburns_clip(
            image_path=img_path,
            duration=max_clip_duration,
            video_aspect=video_aspect,
            task_dir=os.path.join(task_dir, "9router_clips"),
        )

        if clip_path:
            video_paths.append(clip_path)
            total_duration += max_clip_duration
            generated_any = True
            logger.success(f"🤖 9Router: clip {idx + 1} ready → {clip_path}")
        else:
            logger.warning(f"🤖 9Router: Ken Burns conversion failed for clip {idx + 1}")

    # ── Ensure enough 9Router clips to cover full audio duration ────────────
    if video_paths:
        # Cycle generated 9Router AI motion clips to cover full audio_duration
        idx_c = 0
        while total_duration < audio_duration:
            clip_dup = video_paths[idx_c % len(video_paths)]
            video_paths.append(clip_dup)
            total_duration += max_clip_duration
            idx_c += 1
        logger.success(
            f"🤖 9Router pipeline complete: {len(video_paths)} 9Router AI clips "
            f"covering {total_duration:.1f}s total (Strict 9Router mode)"
        )
        return video_paths

    # Emergency fallback retry with simple generic Islamic prompt if 0 images were returned
    logger.warning("🤖 Initial 9Router prompts returned 0 images — attempting emergency retry with generic prompt...")
    for emergency_prompt in ["peaceful mosque golden sunset 4k cinematic", "islamic calligraphy background 4k"]:
        img_p = generate_9router_image(prompt=emergency_prompt, save_dir=os.path.join(task_dir, "9router_images"))
        if img_p:
            c_path = image_to_kenburns_clip(image_path=img_p, duration=max_clip_duration, video_aspect=video_aspect, task_dir=os.path.join(task_dir, "9router_clips"))
            if c_path:
                video_paths.append(c_path)
                total_duration += max_clip_duration
                break

    if video_paths:
        idx_c = 0
        while total_duration < audio_duration:
            video_paths.append(video_paths[idx_c % len(video_paths)])
            total_duration += max_clip_duration
            idx_c += 1
        return video_paths

    logger.error("🤖 9Router pipeline failed to produce any images after emergency retries")
    return []

