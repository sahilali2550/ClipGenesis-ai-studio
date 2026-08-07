import uuid
from typing import List, Dict, Any, Optional
from storyboard.schemas import Scene, Timeline


def generate_timeline(scenes: List[Scene], render_settings: Optional[Dict[str, Any]] = None) -> Timeline:
    """
    Creates a render-ready Timeline JSON from a list of Scenes.
    """
    total_duration = sum(s.duration for s in scenes)
    timeline_id = f"tl_{uuid.uuid4().hex[:8]}"

    return Timeline(
        timeline_id=timeline_id,
        total_duration=round(total_duration, 2),
        scenes=scenes,
        render_settings=render_settings or {
            "fps": 30,
            "resolution": [1080, 1920],
            "audio_ducking": True,
            "subtitles": True
        }
    )
