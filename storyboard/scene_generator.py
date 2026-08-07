import re
from typing import List
from loguru import logger
from storyboard.schemas import Scene, Shot


def breakdown_script_into_scenes(script: str, default_clip_duration: float = 5.0) -> List[Scene]:
    """
    Breaks down input script into structured scenes:
    Scene 1: Hook
    Scene 2..N-1: Main message
    Scene N: Conclusion
    """
    scenes: List[Scene] = []
    if not script:
        return scenes

    # Clean sentences
    raw_sentences = [s.strip() for s in re.split(r"[.!?\n]+", script) if s.strip()]
    if not raw_sentences:
        raw_sentences = [script.strip()]

    total_sentences = len(raw_sentences)

    for idx, sentence in enumerate(raw_sentences):
        scene_num = idx + 1
        if idx == 0:
            scene_type = "hook"
            title = f"Scene {scene_num}: Hook"
            cam_move = "zoom_in"
        elif idx == total_sentences - 1 and total_sentences > 1:
            scene_type = "conclusion"
            title = f"Scene {scene_num}: Conclusion"
            cam_move = "zoom_out"
        else:
            scene_type = "main_message"
            title = f"Scene {scene_num}: Main Message"
            cam_move = "pan_left" if idx % 2 == 0 else "static"

        shot = Shot(
            shot_id=f"shot_{scene_num}_1",
            visual_description=f"Cinematic visual representation of: {sentence[:60]}",
            camera_movement=cam_move,
            duration=default_clip_duration
        )

        scene = Scene(
            scene_id=f"scene_{scene_num}",
            title=title,
            scene_type=scene_type,
            narration=sentence,
            visual_description=f"High quality cinematic shot showing {sentence[:60]}",
            shots=[shot],
            asset_requirements=[w.lower() for w in sentence.split() if len(w) > 4][:3],
            camera_movement=cam_move,
            subtitle_text=sentence,
            duration=default_clip_duration
        )
        scenes.append(scene)

    logger.info(f"Generated {len(scenes)} structured scenes from script.")
    return scenes
