import uuid
from typing import List, Dict, Optional, Any
from loguru import logger
from storyboard.schemas import StoryboardProject, Scene
from storyboard.scene_generator import breakdown_script_into_scenes
from storyboard.visual_prompt import enhance_scene_visuals
from storyboard.timeline import generate_timeline
from storyboard.validator import validate_storyboard


_storyboard_registry: Dict[str, StoryboardProject] = {}


def create_storyboard_project(
    topic: str,
    script: str,
    title: str = "",
    template_id: str = "youtube_short",
    brand_id: Optional[str] = None,
    match_assets: bool = True
) -> StoryboardProject:
    """
    Creates a full production Storyboard Project from script and topic.
    """
    storyboard_id = f"sb_{uuid.uuid4().hex[:8]}"
    project_title = title or f"Storyboard - {topic[:30]}"

    # Step 1: Breakdown script into structured scenes
    scenes = breakdown_script_into_scenes(script)

    # Step 2: Enhance scenes with visual prompts & camera metadata
    enhanced_scenes: List[Scene] = []
    for scene in scenes:
        enhanced = enhance_scene_visuals(scene)

        # Step 3: Match scene asset requirements with Asset Library if available
        if match_assets and scene.asset_requirements:
            try:
                from assets import search as asset_search
                query_term = scene.asset_requirements[0]
                results = asset_search(query=query_term, limit=1)
                if results:
                    enhanced.matched_asset_id = results[0].asset_id
            except Exception as e:
                logger.debug(f"Asset Library search skipped for scene {scene.scene_id}: {e}")

        enhanced_scenes.append(enhanced)

    # Step 4: Generate render-ready Timeline JSON
    timeline = generate_timeline(enhanced_scenes)

    project = StoryboardProject(
        storyboard_id=storyboard_id,
        title=project_title,
        topic=topic,
        script=script,
        template_id=template_id,
        brand_id=brand_id,
        timeline=timeline
    )

    valid, errors = validate_storyboard(project)
    if not valid:
        logger.warning(f"Storyboard validation warnings for {storyboard_id}: {errors}")

    _storyboard_registry[storyboard_id] = project
    logger.info(f"Created Storyboard project {storyboard_id} with {len(scenes)} scenes.")
    return project


def get_storyboard(storyboard_id: str) -> Optional[StoryboardProject]:
    return _storyboard_registry.get(storyboard_id)


def list_storyboards() -> List[StoryboardProject]:
    return list(_storyboard_registry.values())


def get_storyboard_stats() -> Dict[str, Any]:
    total_projects = len(_storyboard_registry)
    total_scenes = sum(len(p.timeline.scenes) for p in _storyboard_registry.values())
    recent_titles = [p.title for p in list(_storyboard_registry.values())[-5:]]

    return {
        "total_storyboards": total_projects,
        "total_scenes": total_scenes,
        "recent_storyboards": recent_titles
    }
