from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel, Field


class AssetItem(BaseModel):
    id: Optional[int] = None
    asset_id: str = ""
    filename: str
    path: str
    type: str  # "image", "video", "audio", "voice"
    category: str = "general"
    tags: List[str] = Field(default_factory=list)
    duration: float = 0.0
    width: int = 0
    height: int = 0
    format: str = ""
    favorite: bool = False
    usage_count: int = 0
    created_at: Optional[str] = None


class AssetQuery(BaseModel):
    query: str = ""
    asset_type: Optional[str] = None
    category: Optional[str] = None
    tag: Optional[str] = None
    favorite_only: bool = False
    limit: int = 50
    offset: int = 0
