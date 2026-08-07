"""
Asset Library Manager Package
"""
from assets.schemas import AssetItem, AssetQuery
from assets.database.db import init_db
from assets.scanner import scan_directory, extract_metadata
from assets.manager import add_asset_from_file, get_asset, resolve_asset_path, search, get_stats

__all__ = [
    "AssetItem",
    "AssetQuery",
    "init_db",
    "scan_directory",
    "extract_metadata",
    "add_asset_from_file",
    "get_asset",
    "resolve_asset_path",
    "search",
    "get_stats",
]
