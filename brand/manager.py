from typing import Union, Optional, Dict, Any
from loguru import logger
from app.models.schema import VideoParams
from app.services import templates
from brand.schemas import BrandKit
from brand.loader import load_brand


def apply_brand_to_params(brand_input: Union[str, BrandKit, Dict[str, Any]], params: VideoParams) -> VideoParams:
    """
    Applies BrandKit identity parameters (Logo, Watermark, Fonts, Colors, Intro/Outro) to VideoParams.
    """
    kit: Optional[BrandKit] = None
    if isinstance(brand_input, str):
        kit = load_brand(brand_input)
    elif isinstance(brand_input, BrandKit):
        kit = brand_input
    elif isinstance(brand_input, dict):
        try:
            kit = BrandKit.model_validate(brand_input)
        except Exception as e:
            logger.warning(f"Failed to validate dict as BrandKit: {e}")

    if not kit:
        logger.warning(f"Brand kit not found or invalid: {brand_input}")
        return params

    logger.info(f"Applying Brand Kit: {kit.name} ({kit.brand_id})")

    # Apply Logo identity (supports raw file path or Asset Library ID)
    if kit.logo_path:
        from assets import resolve_asset_path
        params.logo_path = resolve_asset_path(kit.logo_path)
    params.logo_position = kit.logo_position
    params.logo_size = kit.logo_size
    params.logo_opacity = kit.logo_opacity

    # Apply Watermark identity
    if kit.watermark_text:
        params.watermark_text = kit.watermark_text
        params.watermark_color = kit.watermark_color
        params.watermark_position = kit.watermark_position

    # Apply Fonts identity
    if kit.fonts.subtitle_font:
        params.font_name = kit.fonts.subtitle_font

    # Apply Brand Colors
    if kit.colors.primary:
        params.text_fore_color = kit.colors.primary
    if kit.colors.secondary:
        params.stroke_color = kit.colors.secondary

    # Apply Intro/Outro video identity if present
    if kit.intro_video:
        params.intro_video = kit.intro_video
    if kit.outro_video:
        params.outro_video = kit.outro_video

    return params


def merge_template_and_brand(template_input: Any, brand_input: Any, params: VideoParams) -> VideoParams:
    """
    Combines Video Template and Brand Kit into VideoParams cleanly.
    - Template decides: video style, aspect ratio, transitions, subtitle behavior.
    - Brand Kit decides: identity, logo, brand colors, fonts, watermark text & positioning.
    """
    # 1. Apply Template first (defines video layout & structure)
    if template_input:
        params = templates.apply_template_to_params(template_input, params)

    # 2. Apply Brand Kit second (overrides brand identity, colors, fonts, logo)
    if brand_input:
        params = apply_brand_to_params(brand_input, params)

    return params
