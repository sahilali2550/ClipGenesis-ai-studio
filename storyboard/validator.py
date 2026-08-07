from typing import List, Tuple
from storyboard.schemas import StoryboardProject, Timeline


def validate_storyboard(project: StoryboardProject) -> Tuple[bool, List[str]]:
    """
    Validates storyboard project consistency, timing, and narration.
    """
    errors = []

    if not project.title:
        errors.append("Project title is empty.")

    if not project.timeline or not project.timeline.scenes:
        errors.append("Timeline has no scenes.")
        return False, errors

    for idx, scene in enumerate(project.timeline.scenes):
        if scene.duration <= 0:
            errors.append(f"Scene {idx+1} ({scene.scene_id}) has invalid duration {scene.duration}s.")

        if not scene.narration and not scene.subtitle_text:
            errors.append(f"Scene {idx+1} ({scene.scene_id}) has missing narration and subtitle text.")

    is_valid = len(errors) == 0
    return is_valid, errors
