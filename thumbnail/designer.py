import os
from typing import Optional, Dict, Any
from loguru import logger
from PIL import Image, ImageDraw, ImageFont
from thumbnail.schemas import ThumbnailComposition
from brand.loader import load_brand
try:
    from app.services.templates import load_template
except ImportError:
    def load_template(t_id): return None


LAYOUT_PRESETS = {
    "variant_1": {
        "layout": "top_banner",
        "title_size": 52,
        "backdrop_overlay": True,
        "text_color": "#FFFFFF",
        "accent_color": "#FFD700"
    },
    "variant_2": {
        "layout": "centered_large",
        "title_size": 64,
        "backdrop_overlay": True,
        "text_color": "#00FFFF",
        "accent_color": "#FF007F"
    },
    "variant_3": {
        "layout": "bottom_split",
        "title_size": 44,
        "backdrop_overlay": True,
        "text_color": "#FFFFFF",
        "accent_color": "#00FF88"
    }
}


def build_thumbnail_composition(
    title_text: str,
    subtitle_text: Optional[str] = "",
    brand_id: Optional[str] = None,
    template_id: Optional[str] = None,
    variant_id: str = "variant_1"
) -> ThumbnailComposition:
    """
    Builds thumbnail composition metadata by merging Brand Kit & Template styles.
    """
    preset = LAYOUT_PRESETS.get(variant_id, LAYOUT_PRESETS["variant_1"])
    text_color = preset["text_color"]
    accent_color = preset["accent_color"]
    font_family = "Arial"
    logo_path = None
    watermark = False

    # Apply Brand Kit styles if available
    if brand_id:
        brand = load_brand(brand_id)
        if brand:
            text_color = brand.colors.primary or text_color
            accent_color = brand.colors.secondary or accent_color
            font_family = brand.fonts.title_font or font_family
            logo_path = brand.logo_path if brand.logo_path else None
            watermark = brand.watermark_enabled

    # Apply Template styles if available
    if template_id:
        template = load_template(template_id)
        if template and isinstance(template, dict):
            sub_style = template.get("subtitle_style", {})
            if isinstance(sub_style, dict) and sub_style.get("primary_color"):
                text_color = sub_style.get("primary_color")

    return ThumbnailComposition(
        title_text=title_text,
        subtitle_text=subtitle_text or "",
        layout=preset["layout"],
        text_color=text_color,
        accent_color=accent_color,
        backdrop_overlay=preset["backdrop_overlay"],
        font_family=font_family,
        title_size=preset["title_size"],
        logo_path=logo_path,
        watermark=watermark
    )


def render_thumbnail_image(
    base_frame_path: str,
    composition: ThumbnailComposition,
    output_path: str
) -> str:
    """
    Composes text overlays, backdrop gradients, and brand assets on base frame image.
    """
    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
    try:
        base_img = Image.open(base_frame_path).convert("RGBA")
    except Exception as e:
        logger.warning(f"Could not open base frame {base_frame_path}: {e}, creating canvas.")
        base_img = Image.new("RGBA", (1280, 720), (30, 30, 45, 255))

    img_w, img_h = base_img.size
    overlay = Image.new("RGBA", (img_w, img_h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)

    # 1. Dark backdrop overlay for text contrast
    if composition.backdrop_overlay:
        if composition.layout == "top_banner":
            draw.rectangle([(0, 0), (img_w, int(img_h * 0.35))], fill=(0, 0, 0, 160))
        elif composition.layout == "bottom_split":
            draw.rectangle([(0, int(img_h * 0.65)), (img_w, img_h)], fill=(0, 0, 0, 180))
        else:
            draw.rectangle([(0, int(img_h * 0.25)), (img_w, int(img_h * 0.75))], fill=(0, 0, 0, 140))

    # 2. Draw Title Text
    title = composition.title_text.upper()
    sub = composition.subtitle_text or ""

    if composition.layout == "top_banner":
        text_pos = (50, 40)
    elif composition.layout == "bottom_split":
        text_pos = (50, int(img_h * 0.70))
    else:
        text_pos = (60, int(img_h * 0.38))

    draw.text(text_pos, title, fill=composition.text_color)
    if sub:
        sub_pos = (text_pos[0], text_pos[1] + 55)
        draw.text(sub_pos, sub, fill=composition.accent_color)

    # Composite overlay on base image
    final_img = Image.alpha_composite(base_img, overlay).convert("RGB")
    final_img.save(output_path, format="JPEG", quality=92)
    logger.info(f"Rendered thumbnail image -> {output_path}")
    return output_path
