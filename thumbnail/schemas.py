from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any


class ThumbnailComposition(BaseModel):
    title_text: str
    subtitle_text: Optional[str] = ""
    layout: str = Field(default="centered_large", description="Layout style: top_banner, centered_large, bottom_split, left_badge")
    text_color: str = "#FFFFFF"
    accent_color: str = "#FFD700"
    backdrop_overlay: bool = True
    font_family: str = "Arial"
    title_size: int = 48
    logo_path: Optional[str] = None
    watermark: bool = False


class ThumbnailVariant(BaseModel):
    variant_id: str
    layout_name: str
    frame_timestamp: float
    composition: ThumbnailComposition
    output_path: Optional[str] = None
    ai_score: float = 0.0


class ThumbnailCollection(BaseModel):
    collection_id: str
    source_video: str
    num_variants: int
    variants: List[ThumbnailVariant]
    created_at: str
