import os
from typing import List, Optional
from loguru import logger
from thumbnail.schemas import ThumbnailVariant, ThumbnailCollection
from thumbnail.extractor import select_candidate_timestamps, extract_frame_at_timestamp
from thumbnail.designer import build_thumbnail_composition, render_thumbnail_image


def generate_thumbnail_variants(
    video_path: str,
    title_text: str,
    subtitle_text: Optional[str] = "",
    brand_id: Optional[str] = None,
    template_id: Optional[str] = None,
    num_variants: int = 3,
    output_dir: Optional[str] = None
) -> List[ThumbnailVariant]:
    """
    Generates multiple distinct thumbnail variants for a source video.
    """
    if not output_dir:
        video_dir = os.path.dirname(os.path.abspath(video_path))
        output_dir = os.path.join(video_dir, "thumbnails")
    os.makedirs(output_dir, exist_ok=True)

    timestamps = select_candidate_timestamps(video_path, count=num_variants)
    variant_ids = [f"variant_{i+1}" for i in range(num_variants)]
    variants: List[ThumbnailVariant] = []

    # Mock baseline AI scores for future A-B testing readiness
    base_scores = [0.85, 0.92, 0.78]

    for i in range(num_variants):
        var_id = variant_ids[i]
        ts = timestamps[i] if i < len(timestamps) else timestamps[0]

        # Step 1: Extract candidate keyframe
        frame_name = f"frame_{var_id}_{ts:.1f}s.jpg"
        frame_path = os.path.join(output_dir, frame_name)
        extract_frame_at_timestamp(video_path, ts, frame_path)

        # Step 2: Build composition metadata
        composition = build_thumbnail_composition(
            title_text=title_text,
            subtitle_text=subtitle_text,
            brand_id=brand_id,
            template_id=template_id,
            variant_id=var_id
        )

        # Step 3: Render finalized composite thumbnail image
        thumb_name = f"thumb_{var_id}.jpg"
        thumb_output_path = os.path.join(output_dir, thumb_name)
        render_thumbnail_image(frame_path, composition, thumb_output_path)

        score = base_scores[i] if i < len(base_scores) else 0.80

        variant = ThumbnailVariant(
            variant_id=var_id,
            layout_name=composition.layout,
            frame_timestamp=ts,
            composition=composition,
            output_path=thumb_output_path,
            ai_score=score
        )
        variants.append(variant)

    logger.info(f"Generated {len(variants)} thumbnail variants for video: {video_path}")
    return variants
