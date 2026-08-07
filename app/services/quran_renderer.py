"""
quran_renderer.py — Arabic text → PIL Image renderer
Handles RTL, Arabic reshaping, Uthmanic font, word-by-word karaoke highlighting, and translation overlay.
Strictly borderless: NO dark box card behind text.
"""

import os
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


def _arabic_font_path():
    """Return best available Arabic font path."""
    for p in [ARABIC_FONT_PATH, URDU_FONT_PATH, FALLBACK_FONT_PATH]:
        if os.path.exists(p):
            return p
    return None


def _get_font(path: str, size: int) -> ImageFont.FreeTypeFont:
    """Load a font, falling back to default if not found."""
    if path and os.path.exists(path):
        try:
            return ImageFont.truetype(path, size)
        except Exception:
            pass
    if os.path.exists(FALLBACK_FONT_PATH):
        try:
            return ImageFont.truetype(FALLBACK_FONT_PATH, size)
        except Exception:
            pass
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
    if len(h) == 6:
        return tuple(int(h[i:i+2], 16) for i in (0, 2, 4))
    return (255, 255, 255)


def _wrap_words_to_lines(words: list[str], font: ImageFont.FreeTypeFont, max_width: int) -> list[list[str]]:
    """Group words into lines where each line fits within max_width pixels."""
    if not words:
        return []
    lines = []
    current_line = []
    dummy = Image.new("RGBA", (1, 1))
    draw = ImageDraw.Draw(dummy)

    for w in words:
        test_line = " ".join(current_line + [w])
        reshaped = reshape_arabic(test_line)
        bbox = draw.textbbox((0, 0), reshaped, font=font)
        w_px = bbox[2] - bbox[0]
        if w_px <= max_width or not current_line:
            current_line.append(w)
        else:
            lines.append(current_line)
            current_line = [w]

    if current_line:
        lines.append(current_line)
    return lines


def render_arabic_line(
    text: str,
    font_size: int = 75,
    color: str = "#FFD700",
    stroke_color: str = "#000000",
    stroke_width: int = 3,
    canvas_width: int = 1080,
) -> Image.Image:
    """Render single or multi-line Arabic text with crisp stroke and NO box."""
    font = _get_font(_arabic_font_path() or FALLBACK_FONT_PATH, font_size)
    words = [w.strip() for w in text.split() if w.strip()]
    lines_words = _wrap_words_to_lines(words, font, max_width=canvas_width - 120)

    line_images = []
    for line in lines_words:
        line_str = " ".join(line)
        display_text = reshape_arabic(line_str)
        dummy = Image.new("RGBA", (1, 1))
        draw = ImageDraw.Draw(dummy)
        bbox = draw.textbbox((0, 0), display_text, font=font, stroke_width=stroke_width)
        tw = bbox[2] - bbox[0]
        th = bbox[3] - bbox[1]

        l_img = Image.new("RGBA", (canvas_width, th + 24), (0, 0, 0, 0))
        ldraw = ImageDraw.Draw(l_img)
        lx = (canvas_width - tw) // 2 - bbox[0]
        ly = 12 - bbox[1]

        sc = _hex_to_rgb(stroke_color)
        fc = _hex_to_rgb(color)

        if stroke_width > 0:
            for dx, dy in [(-3,0),(3,0),(0,-3),(0,3),(-2,-2),(2,-2),(-2,2),(2,2)]:
                ldraw.text((lx+dx, ly+dy), display_text, font=font, fill=(*sc, 255))
            ldraw.text((lx, ly), display_text, font=font, fill=(*fc, 255), stroke_width=stroke_width, stroke_fill=(*sc, 255))
        else:
            ldraw.text((lx, ly), display_text, font=font, fill=(*fc, 255))

        line_images.append(l_img)

    total_h = sum(img.height for img in line_images) + max(0, len(line_images) - 1) * 10
    canvas = Image.new("RGBA", (canvas_width, total_h), (0, 0, 0, 0))
    curr_y = 0
    for l_img in line_images:
        canvas.paste(l_img, (0, curr_y), l_img)
        curr_y += l_img.height + 10

    return canvas


def render_arabic_with_highlight(
    words: list[str],
    highlighted_idx: int,
    font_size: int = 75,
    normal_color: str = "#FFFFFF",
    highlight_color: str = "#FFD700",
    stroke_color: str = "#000000",
    stroke_width: int = 3,
    canvas_width: int = 1080,
) -> Image.Image:
    """
    Render Arabic words line-by-line with exact word-level karaoke highlighting in gold/cyan.
    NO background box.
    """
    font = _get_font(_arabic_font_path() or FALLBACK_FONT_PATH, font_size)
    clean_words = [w.strip() for w in words if w.strip()]
    lines_words = _wrap_words_to_lines(clean_words, font, max_width=canvas_width - 120)

    word_counter = 0
    line_images = []

    for line_w in lines_words:
        line_str = " ".join(line_w)
        display_text = reshape_arabic(line_str)

        dummy = Image.new("RGBA", (1, 1))
        draw = ImageDraw.Draw(dummy)
        bbox = draw.textbbox((0, 0), display_text, font=font, stroke_width=stroke_width)
        tw = bbox[2] - bbox[0]
        th = bbox[3] - bbox[1]

        l_img = Image.new("RGBA", (canvas_width, th + 24), (0, 0, 0, 0))
        ldraw = ImageDraw.Draw(l_img)
        lx = (canvas_width - tw) // 2 - bbox[0]
        ly = 12 - bbox[1]

        line_start_idx = word_counter
        line_end_idx = word_counter + len(line_w) - 1
        word_counter += len(line_w)

        color = highlight_color if (line_start_idx <= highlighted_idx <= line_end_idx) else normal_color
        sc = _hex_to_rgb(stroke_color)
        fc = _hex_to_rgb(color)

        if stroke_width > 0:
            for dx, dy in [(-3,0),(3,0),(0,-3),(0,3),(-2,-2),(2,-2),(-2,2),(2,2)]:
                ldraw.text((lx+dx, ly+dy), display_text, font=font, fill=(*sc, 255))
            ldraw.text((lx, ly), display_text, font=font, fill=(*fc, 255), stroke_width=stroke_width, stroke_fill=(*sc, 255))
        else:
            ldraw.text((lx, ly), display_text, font=font, fill=(*fc, 255))

        line_images.append(l_img)

    total_h = sum(img.height for img in line_images) + max(0, len(line_images) - 1) * 10
    canvas = Image.new("RGBA", (canvas_width, max(80, total_h)), (0, 0, 0, 0))
    curr_y = 0
    for l_img in line_images:
        canvas.paste(l_img, (0, curr_y), l_img)
        curr_y += l_img.height + 10

    return canvas


def render_translation_line(
    text: str,
    font_size: int = 42,
    color: str = "#EEEEEE",
    stroke_color: str = "#000000",
    stroke_width: int = 2,
    canvas_width: int = 1080,
    is_urdu: bool = True,
) -> Image.Image:
    """Render a translation line (Urdu RTL or English LTR) wrapped cleanly with NO background box."""
    if not text or not text.strip():
        return Image.new("RGBA", (canvas_width, 1), (0, 0, 0, 0))

    font_path = URDU_FONT_PATH if (is_urdu and os.path.exists(URDU_FONT_PATH)) else FALLBACK_FONT_PATH
    font = _get_font(font_path, font_size)

    words = [w.strip() for w in text.split() if w.strip()]
    lines_words = _wrap_words_to_lines(words, font, max_width=canvas_width - 140)

    line_images = []
    for line_w in lines_words:
        line_str = " ".join(line_w)
        display_text = reshape_arabic(line_str) if is_urdu else line_str

        dummy = Image.new("RGBA", (1, 1))
        draw = ImageDraw.Draw(dummy)
        bbox = draw.textbbox((0, 0), display_text, font=font, stroke_width=stroke_width)
        tw = bbox[2] - bbox[0]
        th = bbox[3] - bbox[1]

        l_img = Image.new("RGBA", (canvas_width, th + 20), (0, 0, 0, 0))
        ldraw = ImageDraw.Draw(l_img)
        lx = (canvas_width - tw) // 2 - bbox[0]
        ly = 10 - bbox[1]

        sc = _hex_to_rgb(stroke_color)
        fc = _hex_to_rgb(color)

        if stroke_width > 0:
            for dx, dy in [(-2,0),(2,0),(0,-2),(0,2),(-2,-2),(2,-2),(-2,2),(2,2)]:
                ldraw.text((lx+dx, ly+dy), display_text, font=font, fill=(*sc, 240))
            ldraw.text((lx, ly), display_text, font=font, fill=(*fc, 255), stroke_width=stroke_width, stroke_fill=(*sc, 240))
        else:
            ldraw.text((lx, ly), display_text, font=font, fill=(*fc, 255))

        line_images.append(l_img)

    total_h = sum(img.height for img in line_images) + max(0, len(line_images) - 1) * 8
    canvas = Image.new("RGBA", (canvas_width, max(50, total_h)), (0, 0, 0, 0))
    curr_y = 0
    for l_img in line_images:
        canvas.paste(l_img, (0, curr_y), l_img)
        curr_y += l_img.height + 8

    return canvas


def build_subtitle_frame(
    arabic_text: str,
    translation_text: str = "",
    arabic_words: list[str] = None,
    highlighted_word_idx: int = -1,
    video_width: int = 1080,
    video_height: int = 1920,
    arabic_font_size: int = 75,
    translation_font_size: int = 42,
    arabic_color: str = "#FFD700",
    normal_color: str = "#FFFFFF",
    highlight_color: str = "#FFD700",
    stroke_color: str = "#000000",
    stroke_width: int = 3,
    translation_color: str = "#EEEEEE",
    is_urdu_translation: bool = True,
    position_pct: float = 0.55,
) -> Image.Image:
    """
    Compose full borderless subtitle overlay for one video frame (NO black background box).
    """
    frame = Image.new("RGBA", (video_width, video_height), (0, 0, 0, 0))

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

    tr_img = None
    if translation_text and translation_text.strip():
        tr_img = render_translation_line(
            translation_text,
            font_size=translation_font_size,
            color=translation_color,
            stroke_color=stroke_color,
            stroke_width=2,
            canvas_width=video_width,
            is_urdu=is_urdu_translation,
        )

    total_h = arabic_img.height + (tr_img.height + 12 if tr_img else 0)
    center_y = int(video_height * position_pct)
    arabic_y = center_y - (total_h // 2)
    tr_y = arabic_y + arabic_img.height + 12

    # Paste directly on frame with NO dark box background
    frame.paste(arabic_img, (0, max(20, arabic_y)), arabic_img)
    if tr_img:
        frame.paste(tr_img, (0, min(video_height - tr_img.height - 20, tr_y)), tr_img)

    return frame


def render_lower_third_badge(
    title: str,
    subtitle: str = "",
    canvas_width: int = 1080,
    canvas_height: int = 1920,
    bg_color: tuple = (0, 0, 0, 0),
    accent_color: tuple = (255, 215, 0, 255),
    text_color: tuple = (255, 255, 255, 255),
) -> Image.Image:
    """Render a clean, borderless identity badge with NO black rectangle box."""
    img = Image.new("RGBA", (canvas_width, canvas_height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    font_title = _get_font(URDU_FONT_PATH, 32)
    font_sub = _get_font(FALLBACK_FONT_PATH, 24)

    x0 = 40
    y0 = canvas_height - 120

    display_title = reshape_arabic(title)
    for dx, dy in [(-2,0),(2,0),(0,-2),(0,2)]:
        draw.text((x0 + dx, y0 + dy), display_title, font=font_title, fill=(0, 0, 0, 240))
    draw.text((x0, y0), display_title, font=font_title, fill=accent_color)

    if subtitle:
        for dx, dy in [(-2,0),(2,0),(0,-2),(0,2)]:
            draw.text((x0 + dx, y0 + 38 + dy), subtitle, font=font_sub, fill=(0, 0, 0, 240))
        draw.text((x0, y0 + 38), subtitle, font=font_sub, fill=text_color)

    return img


