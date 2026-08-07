import os
import json
import glob
from typing import List, Optional, Dict, Any
from loguru import logger
from app.utils import utils
from brand.schemas import BrandKit


PRESETS_DIR = os.path.join(utils.root_dir(), "brand", "presets")


def get_presets_dir() -> str:
    if not os.path.exists(PRESETS_DIR):
        os.makedirs(PRESETS_DIR, exist_ok=True)
    return PRESETS_DIR


def list_brands() -> List[BrandKit]:
    """
    Scans brand/presets/ folder and validates brand JSON presets with Pydantic schema.
    """
    brands = []
    p_dir = get_presets_dir()
    json_files = glob.glob(os.path.join(p_dir, "*.json"))

    for filepath in json_files:
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                raw_data = json.load(f)
                brand = BrandKit.model_validate(raw_data)
                brands.append(brand)
        except Exception as e:
            logger.warning(f"Failed to validate brand preset at {filepath}: {e}")

    return brands


def load_brand(brand_id: str) -> Optional[BrandKit]:
    """
    Retrieves a validated BrandKit instance by brand_id.
    """
    brands = list_brands()
    for b in brands:
        if b.brand_id == brand_id or b.brand_id.lower() == brand_id.lower():
            return b
    return None
