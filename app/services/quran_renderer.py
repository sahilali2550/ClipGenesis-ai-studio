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
    """Render a single line of Arabic text onto a transparent image."""
    display_text = reshape_arabic(text)
    font = _get_font(_arabic_font_path() or FALLBACK_FONT_PATH, font_size)

    # Measure text size accurately
    dummy = Image.new("RGBA", (1, 1))
    draw = ImageDraw.Draw(dummy)
    bbox = draw.textbbox((0, 0), display_text, font=font, stroke_width=stroke_width)
    text_w = bbox[2] - bbox[0]
    text_h = bbox[3] - bbox[1]

    img_w = max(canvas_width, text_w + 60)
    img_h = max(100, text_h + 50)

    img = Image.new("RGBA", (img_w, img_h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    x = (img_w - text_w) // 2 - bbox[0]
    y = 25 - bbox[1]

    # Stroke
    if stroke_width > 0:
        sc = _hex_to_rgb(stroke_color)
        draw.text((x, y), display_text, font=font,
                  fill=(*sc, 255), stroke_width=stroke_width, stroke_fill=(*sc, 255))

    # Main text
    fc = _hex_to_rgb(color)
    draw.text((x, y), display_text, font=font, fill=(*fc, 255))

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
    """
    Render Arabic text where one word is highlighted.
    Arabic is RTL so words are displayed right-to-left.
    """
    font = _get_font(_arabic_font_path() or FALLBACK_FONT_PATH, font_size)

    # Reshape each word individually
    display_words = [reshape_arabic(w) for w in words]
    # For RTL visual display order: words are reversed (first word on rightmost side)
    display_words_rtl = list(reversed(display_words))
    hi_rtl = len(words) - 1 - highlighted_idx if 0 <= highlighted_idx < len(words) else -1

    dummy = Image.new("RGBA", (1, 1))
    draw  = ImageDraw.Draw(dummy)

    space_w = draw.textlength(" ", font=font)
    word_widths = []
    word_bboxes = []
    min_y = 0
    max_y = 0

    for w in display_words_rtl:
        bb = draw.textbbox((0, 0), w, font=font, stroke_width=stroke_width)
        word_widths.append(bb[2] - bb[0])
        word_bboxes.append(bb)
        if bb[1] < min_y:
            min_y = bb[1]
        if bb[3] > max_y:
            max_y = bb[3]

    total_w = sum(word_widths) + space_w * max(0, len(display_words_rtl) - 1)
    text_h = max_y - min_y

    img_w = max(canvas_width, int(total_w) + 60)
    img_h = max(110, int(text_h) + 50)
    img = Image.new("RGBA", (img_w, img_h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    sc = _hex_to_rgb(stroke_color)
    nc = _hex_to_rgb(normal_color)
    hc = _hex_to_rgb(highlight_color)

    x = (img_w - int(total_w)) // 2
    y = 25 - min_y

    for i, (word, ww, bb) in enumerate(zip(display_words_rtl, word_widths, word_bboxes)):
        color = hc if i == hi_rtl else nc
        word_x = x - bb[0]
        if stroke_width > 0:
            draw.text((word_x, y), word, font=font,
                      fill=(*sc, 255), stroke_width=stroke_width, stroke_fill=(*sc, 255))
        draw.text((word_x, y), word, font=font, fill=(*color, 255))
        x += ww + int(space_w)

    return img


def render_translation_line(
    text: str,
    font_size: int = 40,
    color: str = "#FFFFFF",
    stroke_color: str = "#000000",
    stroke_width: int = 1,
    canvas_width: int = 1080,
    is_urdu: bool = True,
) -> Image.Image:
    """Render a translation line (Urdu RTL or English LTR)."""
    font_path = URDU_FONT_PATH if is_urdu else FALLBACK_FONT_PATH
    font = _get_font(font_path, font_size)

    if is_urdu and ARABIC_SUPPORT:
        display_text = get_display(arabic_reshaper.reshape(text))
    else:
        wrapped = "\n".join(textwrap.wrap(text, width=55))
        display_text = wrapped

    dummy = Image.new("RGBA", (1, 1))
    draw  = ImageDraw.Draw(dummy)
    bbox  = draw.textbbox((0, 0), display_text, font=font, stroke_width=stroke_width)
    text_w = bbox[2] - bbox[0]
    text_h = bbox[3] - bbox[1]

    img_w = max(canvas_width, text_w + 40)
    img_h = max(60, text_h + 30)
    img = Image.new("RGBA", (img_w, img_h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    x = (img_w - text_w) // 2 - bbox[0]
    y = 15 - bbox[1]
    sc = _hex_to_rgb(stroke_color)
    fc = _hex_to_rgb(color)
    if stroke_width > 0:
        draw.text((x, y), display_text, font=font,
                  fill=(*sc, 255), stroke_width=stroke_width, stroke_fill=(*sc, 255))
    draw.text((x, y), display_text, font=font, fill=(*fc, 255))
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
    position_pct: float = 0.72,  # vertical position (0=top, 1=bottom)
) -> Image.Image:
    """
    Compose the full subtitle overlay image for one video frame.
    """
    frame = Image.new("RGBA", (video_width, video_height), (0, 0, 0, 0))

    # Arabic text image
    if arabic_words and len(arabic_words) > 1 and highlighted_word_idx >= 0:
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

    # Paste Arabic at position
    arabic_y = int(video_height * position_pct) - arabic_img.height
    frame.paste(arabic_img, (0, arabic_y), arabic_img)

    # Translation image
    if translation_text:
        tr_img = render_translation_line(
            translation_text,
            font_size=translation_font_size,
            color=translation_color,
            stroke_color=stroke_color,
            stroke_width=1,
            canvas_width=video_width,
            is_urdu=is_urdu_translation,
        )
        tr_y = arabic_y + arabic_img.height + 8
        frame.paste(tr_img, (0, tr_y), tr_img)

    return frame
