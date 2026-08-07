import uuid
from datetime import datetime
from typing import Dict, List, Optional, Any
from loguru import logger
from thumbnail.schemas import ThumbnailCollection, ThumbnailVariant
from thumbnail.variants import generate_thumbnail_variants


_collection_registry: Dict[str, ThumbnailCollection] = {}


def create_video_thumbnails(
    source_video: str,
    title_text: str,
    subtitle_text: Optional[str] = "",
    brand_id: Optional[str] = None,
    template_id: Optional[str] = None,
    num_variants: int = 3,
    output_dir: Optional[str] = None
) -> ThumbnailCollection:
    """
    High-level manager function to generate and register thumbnail collections for a video.
    """
    collection_id = f"tc_{uuid.uuid4().hex[:8]}"

    variants = generate_thumbnail_variants(
        video_path=source_video,
        title_text=title_text,
        subtitle_text=subtitle_text,
        brand_id=brand_id,
        template_id=template_id,
        num_variants=num_variants,
        output_dir=output_dir
    )

    collection = ThumbnailCollection(
        collection_id=collection_id,
        source_video=source_video,
        num_variants=len(variants),
        variants=variants,
        created_at=datetime.utcnow().isoformat()
    )

    _collection_registry[collection_id] = collection
    logger.info(f"Registered ThumbnailCollection {collection_id} with {len(variants)} variants.")
    return collection


def get_thumbnail_collection(collection_id: str) -> Optional[ThumbnailCollection]:
    return _collection_registry.get(collection_id)


def list_thumbnail_collections() -> List[ThumbnailCollection]:
    return list(_collection_registry.values())


def get_thumbnail_stats() -> Dict[str, Any]:
    """
    Returns lightweight stats for the Streamlit Dashboard.
    """
    total_collections = len(_collection_registry)
    total_thumbnails = sum(c.num_variants for c in _collection_registry.values())
    recent = []
    for c in list(_collection_registry.values())[-5:]:
        title = c.variants[0].composition.title_text if c.variants else "Untitled"
        recent.append({
            "collection_id": c.collection_id,
            "title": title,
            "num_variants": c.num_variants,
            "created_at": c.created_at
        })

    return {
        "total_collections": total_collections,
        "total_thumbnails": total_thumbnails,
        "recent_thumbnails": recent
    }
