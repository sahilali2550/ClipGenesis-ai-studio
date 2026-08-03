"""
Template Library - Pre-made video templates for intro/outro/transitions.
"""

import os
import json
from typing import Dict, List, Optional
from dataclasses import dataclass, field
from loguru import logger
from app.utils import utils


@dataclass
class VideoTemplate:
    template_id: str
    name: str
    description: str
    category: str  # "intro", "outro", "transition", "full"
    tags: List[str] = field(default_factory=list)
    params: Dict = field(default_factory=dict)  # Pre-configured VideoParams overrides
    thumbnail_url: str = ""  # Placeholder for template preview
    is_builtin: bool = True


# Built-in templates
BUILTIN_TEMPLATES = [
    # Intro Templates
    VideoTemplate(
        template_id="intro_minimal",
        name="Minimal Intro",
        description="Clean, minimal text intro with fade-in animation",
        category="intro",
        tags=["minimal", "clean", "professional"],
        params={
            "video_concat_mode": "sequential",
            "video_clip_duration": 3,
            "subtitle_enabled": True,
            "font_size": 70,
            "stroke_width": 2.0,
        }
    ),
    VideoTemplate(
        template_id="intro_dynamic",
        name="Dynamic Intro",
        description="High-energy intro with zoom effects and bold text",
        category="intro",
        tags=["dynamic", "bold", "youtube"],
        params={
            "video_concat_mode": "sequential",
            "video_clip_duration": 4,
            "subtitle_enabled": True,
            "font_size": 80,
            "stroke_width": 3.0,
            "enable_ken_burns": True,
        }
    ),
    VideoTemplate(
        template_id="intro_cinematic",
        name="Cinematic Intro",
        description="Movie-style intro with letterbox bars and dramatic text",
        category="intro",
        tags=["cinematic", "movie", "dramatic"],
        params={
            "video_aspect": "16:9",
            "video_concat_mode": "sequential",
            "video_clip_duration": 5,
            "subtitle_enabled": True,
            "font_size": 75,
            "text_fore_color": "#FFFFFF",
            "stroke_color": "#000000",
            "stroke_width": 3.0,
        }
    ),
    # Outro Templates
    VideoTemplate(
        template_id="outro_call_to_action",
        name="Call to Action",
        description="Standard outro with subscribe/like prompts",
        category="outro",
        tags=["cta", "subscribe", "youtube"],
        params={
            "video_concat_mode": "sequential",
            "video_clip_duration": 3,
            "subtitle_enabled": True,
            "font_size": 65,
        }
    ),
    VideoTemplate(
        template_id="outro_credits",
        name="Credits Roll",
        description="Simple credits outro with background music",
        category="outro",
        tags=["credits", "music", "simple"],
        params={
            "bgm_type": "random",
            "bgm_volume": 0.4,
            "video_concat_mode": "sequential",
            "video_clip_duration": 3,
        }
    ),
    # Transition Templates
    VideoTemplate(
        template_id="trans_fade",
        name="Fade Transition",
        description="Smooth fade transitions between clips",
        category="transition",
        tags=["fade", "smooth", "professional"],
        params={
            "video_transition_mode": "fade_in",
            "video_concat_mode": "sequential",
        }
    ),
    VideoTemplate(
        template_id="trans_shuffle",
        name="Shuffle Mix",
        description="Random mix of fade, slide, and shuffle transitions",
        category="transition",
        tags=["shuffle", "dynamic", "engaging"],
        params={
            "video_transition_mode": "shuffle",
            "video_concat_mode": "random",
        }
    ),
    # Full Video Templates
    VideoTemplate(
        template_id="full_short_viral",
        name="Viral Short-Form",
        description="Optimized for TikTok/Reels/Shorts - fast cuts, bold text",
        category="full",
        tags=["short", "viral", "tiktok", "shorts"],
        params={
            "video_aspect": "9:16",
            "video_clip_duration": 2,
            "video_concat_mode": "random",
            "subtitle_enabled": True,
            "enable_word_highlighting": True,
            "font_size": 70,
            "word_highlight_color": "#FFD700",
            "enable_audio_ducking": True,
            "enable_ken_burns": True,
        }
    ),
    VideoTemplate(
        template_id="full_educational",
        name="Educational Long-Form",
        description="Professional 16:9 format for YouTube educational content",
        category="full",
        tags=["educational", "youtube", "16:9", "professional"],
        params={
            "video_aspect": "16:9",
            "video_clip_duration": 5,
            "video_concat_mode": "semantic",
            "subtitle_enabled": True,
            "enable_word_highlighting": False,
            "font_size": 55,
            "enable_audio_ducking": True,
            "bgm_type": "smart",
        }
    ),
    VideoTemplate(
        template_id="full_storytelling",
        name="Storytelling Mode",
        description="Warm, narrative-focused with slow cuts and emotive BGM",
        category="full",
        tags=["story", "narrative", "emotional"],
        params={
            "video_aspect": "16:9",
            "video_clip_duration": 6,
            "video_concat_mode": "semantic",
            "video_transition_mode": "fade_in",
            "subtitle_enabled": True,
            "font_size": 60,
            "bgm_type": "smart",
            "bgm_volume": 0.3,
            "enable_audio_ducking": True,
        }
    ),
]


class TemplateManager:
    def __init__(self):
        self._templates: Dict[str, VideoTemplate] = {t.template_id: t for t in BUILTIN_TEMPLATES}
        self._custom_dir = os.path.join(utils.root_dir(), "templates")
        os.makedirs(self._custom_dir, exist_ok=True)
        self._load_custom_templates()

    def _load_custom_templates(self):
        """Load custom templates from disk"""
        for fname in os.listdir(self._custom_dir):
            if fname.endswith(".json"):
                try:
                    with open(os.path.join(self._custom_dir, fname), "r", encoding="utf-8") as f:
                        data = json.load(f)
                    t = VideoTemplate(**data)
                    self._templates[t.template_id] = t
                except Exception as e:
                    logger.warning(f"Failed to load template {fname}: {e}")

    def get_all_templates(self) -> List[Dict]:
        """Get all templates (builtin + custom)"""
        return [self._template_to_dict(t) for t in self._templates.values()]

    def get_template(self, template_id: str) -> Optional[VideoTemplate]:
        """Get a specific template"""
        return self._templates.get(template_id)

    def get_templates_by_category(self, category: str) -> List[Dict]:
        """Get templates filtered by category"""
        return [self._template_to_dict(t) for t in self._templates.values()
                if t.category == category]

    def create_custom_template(self, name: str, description: str, category: str,
                                params: Dict, tags: List[str] = None) -> VideoTemplate:
        """Create a new custom template"""
        template_id = f"custom_{int(time.time())}"
        t = VideoTemplate(
            template_id=template_id,
            name=name,
            description=description,
            category=category,
            tags=tags or [],
            params=params,
            is_builtin=False,
        )
        self._templates[template_id] = t
        self._save_template(t)
        return t

    def delete_template(self, template_id: str) -> bool:
        """Delete a custom template"""
        t = self._templates.get(template_id)
        if t and not t.is_builtin:
            del self._templates[template_id]
            path = os.path.join(self._custom_dir, f"{template_id}.json")
            if os.path.exists(path):
                os.remove(path)
            return True
        return False

    def apply_template(self, base_params, template_id: str):
        """Apply template params to a base VideoParams object"""
        t = self._templates.get(template_id)
        if not t:
            logger.warning(f"Template not found: {template_id}")
            return base_params

        for key, value in t.params.items():
            if hasattr(base_params, key):
                setattr(base_params, key, value)
        return base_params

    def _save_template(self, t: VideoTemplate):
        """Save template to disk"""
        path = os.path.join(self._custom_dir, f"{t.template_id}.json")
        with open(path, "w", encoding="utf-8") as f:
            json.dump(self._template_to_dict(t), f, ensure_ascii=False, indent=2)

    def _template_to_dict(self, t: VideoTemplate) -> Dict:
        d = asdict(t)
        return d


# Global instance
template_manager = TemplateManager()
