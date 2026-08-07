from typing import Dict, Any
from storyboard.schemas import Scene, Shot


CAMERA_MOVEMENTS = ["zoom_in", "zoom_out", "pan_left", "pan_right", "static", "tilt_up"]
LIGHTING_STYLES = ["cinematic warm", "dramatic studio", "bright daylight", "moody ambient"]


def generate_visual_prompt_for_scene(scene: Scene, style_preset: str = "photorealistic") -> Dict[str, Any]:
    """
    Generates rich visual description, camera movement, lighting, and style parameters.
    """
    kw_desc = ", ".join(scene.asset_requirements) if scene.asset_requirements else scene.title
    visual_description = f"{style_preset} 8k resolution shot, {kw_desc}, highly detailed, cinematic composition"
    
    return {
        "visual_description": visual_description,
        "camera_movement": scene.camera_movement,
        "lighting": "cinematic warm",
        "style": style_preset,
        "aspect_ratio": "9:16"
    }


def enhance_scene_visuals(scene: Scene, style_preset: str = "photorealistic") -> Scene:
    prompt_meta = generate_visual_prompt_for_scene(scene, style_preset=style_preset)
    scene.visual_description = prompt_meta["visual_description"]
    
    for shot in scene.shots:
        shot.visual_description = prompt_meta["visual_description"]
        shot.lighting = prompt_meta["lighting"]
        shot.style = prompt_meta["style"]
        
    return scene
