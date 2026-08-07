"""
Template Library Engine - JSON Based Video Templates Manager.
"""

import os
import json
import glob
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from loguru import logger
from app.utils import utils
from app.models.schema import VideoParams, VideoAspect, VideoConcatMode, VideoTransitionMode


TEMPLATES_DIR = os.path.join(utils.root_dir(), "templates")


@dataclass
class VideoTemplate:
    template_id: str
    name: str
    description: str
    category: str
    aspect_ratio: str = "9:16"
    tags: List[str] = field(default_factory=list)
    params: Dict[str, Any] = field(default_factory=dict)
    thumbnail_url: str = ""
    is_builtin: bool = True


def get_templates_dir() -> str:
    if not os.path.exists(TEMPLATES_DIR):
        os.makedirs(TEMPLATES_DIR, exist_ok=True)
    return TEMPLATES_DIR


def list_templates() -> List[Dict[str, Any]]:
    """
    Scans templates/ directory for JSON templates and returns list of template dictionaries.
    """
    templates = []
    t_dir = get_templates_dir()
    json_files = glob.glob(os.path.join(t_dir, "*.json"))

    for filepath in json_files:
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                data = json.load(f)
                data["_file"] = filepath
                templates.append(data)
        except Exception as e:
            logger.warning(f"Failed to load template from {filepath}: {e}")

    return templates


def load_template(template_id: str) -> Optional[Dict[str, Any]]:
    """
    Loads a specific template dictionary by ID or filename.
    """
    templates = list_templates()
    for t in templates:
        if t.get("template_id") == template_id or os.path.basename(t.get("_file", "")).startswith(template_id):
            return t
    return None


def apply_template_to_params(template_id_or_data: Any, params: VideoParams) -> VideoParams:
    """
    Applies template settings to a VideoParams object without overwriting user script/subject.
    """
    if isinstance(template_id_or_data, str):
        tmpl = load_template(template_id_or_data)
    elif isinstance(template_id_or_data, dict):
        tmpl = template_id_or_data
    else:
        tmpl = None

    if not tmpl:
        logger.warning(f"Template not found: {template_id_or_data}")
        return params

    logger.info(f"Applying video template: {tmpl.get('name', tmpl.get('template_id'))}")

    # Map aspect ratio
    asp_str = tmpl.get("aspect_ratio", "9:16")
    if asp_str == "16:9":
        params.video_aspect = VideoAspect.landscape
    elif asp_str == "1:1":
        params.video_aspect = VideoAspect.square
    else:
        params.video_aspect = VideoAspect.portrait

    # Map video source & duration
    if tmpl.get("video_source"):
        params.video_source = tmpl.get("video_source")
    if tmpl.get("video_clip_duration"):
        params.video_clip_duration = int(tmpl.get("video_clip_duration"))

    # Map concat & transition mode
    concat_str = tmpl.get("video_concat_mode", "random")
    if concat_str in [e.value for e in VideoConcatMode]:
        params.video_concat_mode = VideoConcatMode(concat_str)

    trans_str = tmpl.get("video_transition_mode")
    if trans_str and trans_str in [e.value for e in VideoTransitionMode if e.value]:
        params.video_transition_mode = VideoTransitionMode(trans_str)

    # Subtitle styling
    sub_style = tmpl.get("subtitle_style", {})
    if sub_style:
        params.subtitle_enabled = sub_style.get("enabled", True)
        params.font_name = sub_style.get("font_name", params.font_name)
        params.font_size = sub_style.get("font_size", params.font_size)
        params.text_fore_color = sub_style.get("font_color", params.text_fore_color)
        params.stroke_color = sub_style.get("stroke_color", params.stroke_color)
        params.stroke_width = sub_style.get("stroke_width", params.stroke_width)
        params.subtitle_position = sub_style.get("position", params.subtitle_position)
        if "enable_word_highlighting" in sub_style:
            params.enable_word_highlighting = sub_style["enable_word_highlighting"]

    # Audio settings
    audio_cfg = tmpl.get("audio", {})
    if audio_cfg:
        params.bgm_type = audio_cfg.get("bgm_type", params.bgm_type)
        params.bgm_volume = audio_cfg.get("bgm_volume", params.bgm_volume)
        if "enable_audio_ducking" in audio_cfg:
            params.enable_audio_ducking = audio_cfg["enable_audio_ducking"]

    # Effects
    fx_cfg = tmpl.get("effects", {})
    if fx_cfg and "enable_ken_burns" in fx_cfg:
        params.enable_ken_burns = fx_cfg["enable_ken_burns"]

    # Logo & Watermark
    logo_cfg = tmpl.get("logo", {})
    if logo_cfg:
        if logo_cfg.get("path"):
            params.logo_path = logo_cfg.get("path")
        params.logo_position = logo_cfg.get("position", getattr(params, "logo_position", "top_right"))
        params.logo_size = logo_cfg.get("size", getattr(params, "logo_size", 120))
        params.logo_opacity = logo_cfg.get("opacity", getattr(params, "logo_opacity", 0.90))

    return params


# Backward compatibility export
BUILTIN_TEMPLATES = [
    VideoTemplate(
        template_id=t.get("template_id", ""),
        name=t.get("name", ""),
        description=t.get("description", ""),
        category=t.get("category", "general"),
        aspect_ratio=t.get("aspect_ratio", "9:16"),
        params=t,
    )
    for t in list_templates()
]
