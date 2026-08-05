"""
quran_renderer.py — Arabic text → PIL Image renderer
Handles RTL, Arabic reshaping, Uthmanic font, word highlighting, and translation overlay.
"""

import os
import textwrap
from typing import Optional
from loguru import logger
from PIL import Image, ImageDraw, ImageFont

try:
    import arabic_reshaper
    from bidi.algorithm import get_display
    ARABIC_SUPPORT = True
except ImportError:
    ARABIC_SUPPORT = False
    logger.warning("arabic-reshaper / python-bidi not installed. Run: pip install arabic-reshaper python-bidi")

# ── Font paths ────────────────────────────────────────────────────────────────
_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.realpath(__file__))))
FONTS_DIR = os.path.join(_ROOT, "resource", "fonts")

ARABIC_FONT_PATH   = os.path.join(FONTS_DIR, "UthmanicHafs.ttf")
URDU_FONT_PATH     = os.path.join(FONTS_DIR, "JameelNooriNastaleeq.ttf")
FALLBACK_FONT_PATH = os.path.join(FONTS_DIR, "MicrosoftYaHeiBold.ttc")

# Fallback chain for Arabic: UthmanicHafs → JameelNooriNastaleeq → MicrosoftYaHei
def _arabic_font_path():
    """Return best available Arabic font path."""
    for p in [ARABIC_FONT_PATH, URDU_FONT_PATH, FALLBACK_FONT_PATH]:
        if os.path.exists(p):
            return p
    return None


def _get_font(path: str, size: int) -> ImageFont.FreeTypeFont:
    """Load a font, falling back to default if not found."""
    if os.path.exists(path):
        return ImageFont.truetype(path, size)
    logger.warning(f"Font not found: {path}, using fallback")
    if os.path.exists(FALLBACK_FONT_PATH):
        return ImageFont.truetype(FALLBACK_FONT_PATH, size)
    return ImageFont.load_default()


def reshape_arabic(text: str) -> str:
    """Reshape Arabic text for proper rendering (joins characters + RTL)."""
    if not ARABIC_SUPPORT or not text:
        return text
    try:
        reshaped = arabic_reshaper.reshape(text)
        return get_display(reshaped)
    except Exception as e:
        logger.warning(f"Arabic reshape failed: {e}")
        return text


def _hex_to_rgb(hex_color: str) -> tuple:
    h = hex_color.lstrip("#")
    return tuple(int(h[i:i+2], 16) for i in (0, 2, 4))


def render_arabic_line(
    text: str,
    font_size: int = 80,
    color: str = "#FFD700",
    stroke_color: str = "#000000",
    stroke_width: int = 2,
    canvas_width: int = 1080,
) -> Image.Image:
    """Render a single or multi-line Arabic text onto a canvas matching canvas_width."""
    display_text = reshape_arabic(text)
    font = _get_font(_arabic_font_path() or FALLBACK_FONT_PATH, font_size)

    # Word wrap long Arabic text if needed
    lines = textwrap.wrap(display_text, width=32) if len(display_text) > 35 else [display_text]
    wrapped_text = "\n".join(lines)

    dummy = Image.new("RGBA", (1, 1))
    draw = ImageDraw.Draw(dummy)
    bbox = draw.multiline_textbbox((0, 0), wrapped_text, font=font, stroke_width=stroke_width, align="center")
    text_w = bbox[2] - bbox[0]
    text_h = bbox[3] - bbox[1]

    img_w = canvas_width
    img_h = max(90, text_h + 30)

    img = Image.new("RGBA", (img_w, img_h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    x = (img_w - text_w) // 2 - bbox[0]
    y = 15 - bbox[1]

    sc = _hex_to_rgb(stroke_color)
    fc = _hex_to_rgb(color)

    if stroke_width > 0:
        draw.multiline_text((x, y), wrapped_text, font=font,
                           fill=(*sc, 255), stroke_width=stroke_width, stroke_fill=(*sc, 255), align="center")

    draw.multiline_text((x, y), wrapped_text, font=font, fill=(*fc, 255), align="center")

    return img


def render_arabic_with_highlight(
    words: list[str],
    highlighted_idx: int,
    font_size: int = 80,
    normal_color: str = "#FFFFFF",
    highlight_color: str = "#FFD700",
    stroke_color: str = "#000000",
    stroke_width: int = 2,
    canvas_width: int = 1080,
) -> Image.Image:
    """Render reshaped Arabic text with current word highlighted in gold."""
    full_arabic = " ".join(words)
    return render_arabic_line(
        full_arabic,
        font_size=font_size,
        color=highlight_color if highlighted_idx >= 0 else normal_color,
        stroke_color=stroke_color,
        stroke_width=stroke_width,
        canvas_width=canvas_width,
    )


def render_translation_line(
    text: str,
    font_size: int = 40,
    color: str = "#FFFFFF",
    stroke_color: str = "#000000",
    stroke_width: int = 1,
    canvas_width: int = 1080,
    is_urdu: bool = True,
) -> Image.Image:
    """Render a translation line (Urdu RTL or English LTR) wrapped to canvas_width."""
    font_path = URDU_FONT_PATH if is_urdu else FALLBACK_FONT_PATH
    font = _get_font(font_path, font_size)

    if is_urdu and ARABIC_SUPPORT:
        reshaped = arabic_reshaper.reshape(text)
        lines = textwrap.wrap(reshaped, width=32)
        wrapped_lines = [get_display(line) for line in lines]
        display_text = "\n".join(wrapped_lines)
    else:
        display_text = "\n".join(textwrap.wrap(text, width=40))

    dummy = Image.new("RGBA", (1, 1))
    draw  = ImageDraw.Draw(dummy)
    bbox  = draw.multiline_textbbox((0, 0), display_text, font=font, stroke_width=stroke_width, align="center")
    text_w = bbox[2] - bbox[0]
    text_h = bbox[3] - bbox[1]

    img_w = canvas_width
    img_h = max(60, text_h + 20)
    img = Image.new("RGBA", (img_w, img_h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    x = (img_w - text_w) // 2 - bbox[0]
    y = 10 - bbox[1]
    sc = _hex_to_rgb(stroke_color)
    fc = _hex_to_rgb(color)

    if stroke_width > 0:
        draw.multiline_text((x, y), display_text, font=font,
                           fill=(*sc, 255), stroke_width=stroke_width, stroke_fill=(*sc, 255), align="center")
    draw.multiline_text((x, y), display_text, font=font, fill=(*fc, 255), align="center")
    return img


def build_subtitle_frame(
    arabic_text: str,
    translation_text: str = "",
    arabic_words: list[str] = None,
    highlighted_word_idx: int = -1,
    video_width: int = 1080,
    video_height: int = 1920,
    arabic_font_size: int = 80,
    translation_font_size: int = 42,
    arabic_color: str = "#FFD700",
    normal_color: str = "#FFFFFF",
    highlight_color: str = "#FFD700",
    stroke_color: str = "#000000",
    stroke_width: int = 2,
    translation_color: str = "#EEEEEE",
    is_urdu_translation: bool = True,
    position_pct: float = 0.52,  # vertical position (0.52 = middle of screen, mobile UI safe)
) -> Image.Image:
    """
    Compose the full subtitle overlay image for one video frame with golden container card.
    """
    frame = Image.new("RGBA", (video_width, video_height), (0, 0, 0, 0))

    # Arabic text image
    if arabic_words:
        arabic_img = render_arabic_with_highlight(
            arabic_words, highlighted_word_idx,
            font_size=arabic_font_size,
            normal_color=normal_color,
            highlight_color=highlight_color,
            stroke_color=stroke_color,
            stroke_width=stroke_width,
            canvas_width=video_width,
        )
    else:
        arabic_img = render_arabic_line(
            arabic_text,
            font_size=arabic_font_size,
            color=arabic_color,
            stroke_color=stroke_color,
            stroke_width=stroke_width,
            canvas_width=video_width,
        )

    # Translation image
    tr_img = None
    if translation_text:
        tr_img = render_translation_line(
            translation_text,
            font_size=translation_font_size,
            color=translation_color,
            stroke_color=stroke_color,
            stroke_width=2,
            canvas_width=video_width,
            is_urdu=is_urdu_translation,
        )

    # Calculate positions & total container box
    total_content_h = arabic_img.height + (tr_img.height + 8 if tr_img else 0)
    center_y = int(video_height * position_pct)
    box_padding = 24
    box_w = min(video_width - 60, max(800, video_width - 80))
    box_h = total_content_h + box_padding * 2

    box_x0 = (video_width - box_w) // 2
    box_y0 = center_y - (box_h // 2)
    box_x1 = box_x0 + box_w
    box_y1 = box_y0 + box_h

    arabic_y = box_y0 + box_padding
    tr_y = arabic_y + arabic_img.height + 8

    draw = ImageDraw.Draw(frame)
    # Dark backdrop pill card with golden border
    draw.rounded_rectangle([box_x0, box_y0, box_x1, box_y1], radius=16, fill=(0, 0, 0, 185), outline=(255, 215, 0, 180), width=2)

    # Paste Arabic
    frame.paste(arabic_img, (0, arabic_y), arabic_img)

    # Paste Translation
    if tr_img:
        frame.paste(tr_img, (0, tr_y), tr_img)

    return frame


def render_lower_third_badge(
    title: str,
    subtitle: str = "",
    canvas_width: int = 1080,
    canvas_height: int = 1920,
    bg_color: tuple = (20, 20, 20, 210),
    accent_color: tuple = (255, 215, 0, 255),
    text_color: tuple = (255, 255, 255, 255),
) -> Image.Image:
    """Render a modern lower-third identity badge (e.g. Reciter Name, Surah info, Topic Card)"""
    img = Image.new("RGBA", (canvas_width, canvas_height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    font_title = _get_font(URDU_FONT_PATH, 32)
    font_sub = _get_font(FALLBACK_FONT_PATH, 24)

    card_w = min(600, canvas_width - 80)
    card_h = 75 if subtitle else 55
    x0 = 40
    y0 = canvas_height - card_h - 100
    x1 = x0 + card_w
    y1 = y0 + card_h

    # Draw card background & accent border bar
    draw.rounded_rectangle([x0, y0, x1, y1], radius=12, fill=bg_color)
    draw.rectangle([x0, y0, x0 + 6, y1], fill=accent_color)

    # Draw text
    draw.text((x0 + 20, y0 + 10), reshape_arabic(title), font=font_title, fill=text_color)
    if subtitle:
        draw.text((x0 + 20, y0 + 44), subtitle, font=font_sub, fill=(200, 200, 200, 255))

    return img

