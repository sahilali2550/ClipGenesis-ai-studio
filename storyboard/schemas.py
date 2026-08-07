from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
from datetime import datetime


class Shot(BaseModel):
    shot_id: str
    visual_description: str = ""
    camera_movement: str = "static"  # "zoom_in", "pan_left", "static", "tilt_up"
    lighting: str = "cinematic"
    style: str = "photorealistic"
    duration: float = 3.0


class Scene(BaseModel):
    scene_id: str
    title: str = ""
    scene_type: str = "main_message"  # "hook", "main_message", "conclusion"
    narration: str = ""
    visual_description: str = ""
    shots: List[Shot] = Field(default_factory=list)
    asset_requirements: List[str] = Field(default_factory=list)
    matched_asset_id: Optional[str] = None
    camera_movement: str = "zoom_in"
    transition: str = "fade"
    subtitle_text: str = ""
    duration: float = 5.0


class Timeline(BaseModel):
    timeline_id: str
    total_duration: float = 0.0
    scenes: List[Scene] = Field(default_factory=list)
    render_settings: Dict[str, Any] = Field(default_factory=dict)


class StoryboardProject(BaseModel):
    storyboard_id: str
    title: str
    topic: str
    script: str = ""
    template_id: str = "youtube_short"
    brand_id: Optional[str] = None
    timeline: Timeline
    created_at: str = Field(default_factory=lambda: datetime.now().isoformat())
