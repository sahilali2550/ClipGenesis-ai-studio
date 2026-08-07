import os
from typing import List, Optional, Dict
from assets.schemas import AssetItem, AssetQuery
from assets.database import db
from assets.scanner import extract_metadata, scan_directory


def add_asset_from_file(filepath: str, category: str = "general", tags: Optional[List[str]] = None) -> Optional[AssetItem]:
    if not os.path.exists(filepath):
        return None
    item = extract_metadata(filepath)
    item.category = category
    if tags:
        item.tags.extend(tags)
    return db.register_asset(item)


def get_asset(asset_id_or_path: str) -> Optional[AssetItem]:
    return db.get_asset_by_id(asset_id_or_path)


def resolve_asset_path(asset_id_or_path: str) -> str:
    """
    Resolves asset IDs (e.g. ast_1a2b3c4d) to absolute local file paths.
    If input is already an existing path, returns it directly.
    """
    if not asset_id_or_path:
        return ""
    if os.path.exists(asset_id_or_path):
        return asset_id_or_path

    asset = get_asset(asset_id_or_path)
    if asset and os.path.exists(asset.path):
        return asset.path

    return asset_id_or_path


def search(
    query: str = "",
    asset_type: Optional[str] = None,
    category: Optional[str] = None,
    tag: Optional[str] = None,
    limit: int = 50,
) -> List[AssetItem]:
    q = AssetQuery(
        query=query,
        asset_type=asset_type,
        category=category,
        tag=tag,
        limit=limit,
    )
    return db.search_assets(q)


def get_stats() -> Dict[str, int]:
    return db.get_asset_stats()
