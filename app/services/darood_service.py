import os
import re
import random
import datetime
import textwrap
import numpy as np
import arabic_reshaper
from bidi.algorithm import get_display
from PIL import Image, ImageDraw, ImageFont
from loguru import logger
from app.services import voice, material
from app.models.schema import VideoAspect
from app.utils import utils

# Catalog of 30 Authentic Darood Shareefs with Arabic text, Urdu Translation, and Benefits
DAROOD_CATALOG = [
    {
        "id": "darood_ibrahimi",
        "title": "Darood-e-Ibrahimi (درودِ ابراہیمی)",
        "arabic": "اللَّهُمَّ صَلِّ عَلَى مُحَمَّدٍ وَعَلَى آلِ مُحَمَّدٍ كَمَا صَلَّيْتَ عَلَى إِبْرَاهِيمَ وَعَلَى آلِ إِبْرَاهِيمَ إِنَّكَ حَمِيدٌ مَجِيدٌ ۞ اللَّهُمَّ بَارِكْ عَلَى مُحَمَّدٍ وَعَلَى آلِ مُحَمَّدٍ كَمَا بَارَكْتَ عَلَى إِبْرَاهِيمَ وَعَلَى آلِ إِبْرَاهِيمَ إِنَّكَ حَمِيدٌ مَجِيدٌ",
        "urdu": "اے اللہ! درود بھیج محمد صلی اللہ علیہ وسلم پر اور ان کی آل پر، جیسے تو نے درود بھیجا ابراہیم علیہ السلام اور ان کی آل پر، بے شک تو تعریف کیا ہوا اور بزرگ ہے۔ اے اللہ! برکت نازل فرما محمد صلی اللہ علیہ وسلم پر اور ان کی آل پر، جیسے تو نے برکت نازل فرمائی ابراہیم علیہ السلام اور ان کی آل پر، بے شک تو تعریف کیا ہوا اور بزرگ ہے۔",
        "english": "O Allah, send blessings upon Muhammad and upon the family of Muhammad, as You sent blessings upon Ibrahim and upon the family of Ibrahim. Indeed, You are Praiseworthy and Glorious.",
        "benefit": "افضل ترین درود شریف جو نماز میں پڑھا جاتا ہے۔"
    },
    {
        "id": "darood_tanjina",
        "title": "Darood-e-Tanjina (درودِ تنجینا)",
        "arabic": "اللَّهُمَّ صَلِّ عَلَى سَيِّدِنَا مُحَمَّدٍ صَلاَةً تُنْجِينَا بِهَا مِنْ جَمِيعِ الأَهْوَالِ وَالآفَاتِ وَتَقْضِي لَنَا بِهَا جَمِيعَ الحَاجَاتِ وَتُطَهِّرُنَا بِهَا مِنْ جَمِيعِ السَّيِّئَاتِ وَتَرْفَعُنَا بِهَا عِنْدَكَ أَعْلَى الدَّرَجَاتِ",
        "urdu": "اے اللہ! ہمارے آقا محمد صلی اللہ علیہ وسلم پر ایسی رحمت نازل فرما جس کے ذریعے تو ہمیں تمام ہولناکیوں اور آفات سے نجات دے اور ہماری تمام حاجات پوری فرمائے۔",
        "english": "O Allah, bestow blessings upon our Master Muhammad, such blessings by which You rescue us from all terrors and calamities.",
        "benefit": "تمام مشکلات اور پریشانیوں سے نجات کا باعث۔"
    },
    {
        "id": "darood_nariyah",
        "title": "Darood-e-Nariyah / Taziyyah (درودِ ناریہ)",
        "arabic": "اللَّهُمَّ صَلِّ صَلاَةً كَامِلَةً وَسَلِّمْ سَلاَماً تَامّاً عَلَى سَيِّدِنَا مُحَمَّدٍ الَّذِي تَنْحَلُّ بِهِ العُقَدُ وَتَنْفَرِجُ بِهِ الكُرَبُ وَتُقْضَى بِهِ الحَوَائِجُ وَتُنَالُ بِهِ الرَّغَائِبُ",
        "urdu": "اے اللہ! ہمارے آقا محمد صلی اللہ علیہ وسلم پر کامل درود اور سلام نازل فرما جن کے وسیلے سے گرہیں کھلتی ہیں اور رنج و غم دور ہوتے ہیں۔",
        "english": "O Allah, grant complete blessings and perfect peace upon our Master Muhammad, through whom difficulties are solved and desires attained.",
        "benefit": "مقاصد میں کامیابی اور تنگیوں کے خاتمے کے لیے مؤثر۔"
    },
    {
        "id": "darood_taj",
        "title": "Darood-e-Taj (درودِ تاج)",
        "arabic": "اللَّهُمَّ صَلِّ عَلَى سَيِّدِنَا وَمَوْلاَنَا مُحَمَّدٍ صَاحِبِ التَّاجِ وَالمِعْرَاجِ وَالبُرَاقِ وَالعَلَمِ ۞ دَافِعِ البَلاَءِ وَالوَبَاءِ وَالقَحْطِ وَالمَرَضِ وَالأَلَمِ",
        "urdu": "اے اللہ! ہمارے آقا اور مولا محمد صلی اللہ علیہ وسلم پر درود بھیج جو تاج، معراج، براق اور علم والے ہیں، اور بلاؤں، وباؤں، قحط اور بیماریوں کو دور کرنے والے ہیں۔",
        "english": "O Allah, send peace upon our Master Muhammad, the owner of the Crown, the Ascension, the Buraq, and the Banner.",
        "benefit": "برکت، حفاظت اور روحانی ترقی کے لیے معروف۔"
    },
    {
        "id": "darood_shafi",
        "title": "Darood-e-Shafi (درودِ شفا)",
        "arabic": "اللَّهُمَّ صَلِّ عَلَى مُحَمَّدٍ بِعَدَدِ كُلِّ دَاءٍ وَدَوَاءٍ وَبَارِكْ وَسَلِّمْ",
        "urdu": "اے اللہ! حضرت محمد صلی اللہ علیہ وسلم پر ہر بیماری اور ہر دوا کی تعداد کے برابر درود اور برکت و سلام نازل فرما۔",
        "english": "O Allah, send blessings upon Muhammad equal to the number of every disease and every cure.",
        "benefit": "بیماریوں سے شفا اور صحت کے لیے بااثر۔"
    },
    {
        "id": "darood_ghausia",
        "title": "Darood-e-Ghausia (درودِ غوثیہ)",
        "arabic": "اللَّهُمَّ صَلِّ عَلَى سَيِّدِنَا مُحَمَّدٍ الكَهْفِ وَالرَّقِيمِ وَعَلَى آلِ سَيِّدِنَا مُحَمَّدٍ وَبَارِكْ وَسَلِّمْ",
        "urdu": "اے اللہ! ہمارے آقا حضرت محمد صلی اللہ علیہ وسلم اور ان کی آل پر درود و سلام اور برکتیں نازل فرما۔",
        "english": "O Allah, send blessings and peace upon our Master Muhammad and the family of our Master Muhammad.",
        "benefit": "دل کا سکون اور قربِ الٰہی۔"
    },
    {
        "id": "darood_kibriya",
        "title": "Darood-e-Kibriya (درودِ کبریا)",
        "arabic": "اللَّهُمَّ صَلِّ عَلَى سَيِّدِنَا مُحَمَّدٍ عَدَدَ مَا فِي عِلْمِ اللهِ صَلاَةً دَائِمَةً بِدَوَامِ مُلْكِ اللهِ",
        "urdu": "اے اللہ! ہمارے آقا محمد صلی اللہ علیہ وسلم پر اللہ کے علم کی تعداد کے برابر درود نازل فرما، ایسا درود جو اللہ کی بادشاہی کے دوام کے ساتھ ہمیشگی والا ہو۔",
        "english": "O Allah, send blessings upon our Master Muhammad equal to that which is in the Knowledge of Allah.",
        "benefit": "بے شمار ثواب اور ہمیشگی کی برکت۔"
    },
    {
        "id": "darood_al_alfi",
        "title": "Darood-e-Al-Alfi (درودِ الفی - 10 لاکھ ثواب)",
        "arabic": "اللَّهُمَّ صَلِّ عَلَى مُحَمَّدٍ وَعَلَى آلِ مُحَمَّدٍ أَلْفَ أَلْفِ مَرَّةٍ",
        "urdu": "اے اللہ! حضرت محمد صلی اللہ علیہ وسلم اور ان کی آل پر دس لاکھ مرتبہ درود نازل فرما۔",
        "english": "O Allah, send blessings upon Muhammad and the family of Muhammad a million times.",
        "benefit": "ایک باری پڑھنے پر عظیم ثواب۔"
    },
    {
        "id": "darood_khizri",
        "title": "Darood-e-Khizri (درودِ خضری)",
        "arabic": "صَلَّى اللهُ عَلَى حَبِيبِهِ مُحَمَّدٍ وَآلِهِ وَسَلَّمَ",
        "urdu": "اللہ تعالیٰ اپنے حبیب حضرت محمد صلی اللہ علیہ وسلم اور ان کی آل پر درود و سلام نازل فرمائے۔",
        "english": "May Allah send blessings and peace upon His Beloved Muhammad and his family.",
        "benefit": "روزمرہ کثرت سے پڑھنے کے لیے بہترین اور مختصر ترین درود۔"
    },
    {
        "id": "darood_mustafa",
        "title": "Darood-e-Mustafa / Juma Special (درودِ مصطفیٰ)",
        "arabic": "اللَّهُمَّ صَلِّ عَلَى مُحَمَّدٍ النَّبِيِّ الأُمِّيِّ وَعَلَى آلِهِ وَسَلِّمْ تَسْلِيماً",
        "urdu": "اے اللہ! امی نبی حضرت محمد صلی اللہ علیہ وسلم اور ان کی آل پر کامل سلامتی والا درود نازل فرما۔",
        "english": "O Allah, send blessings and perfect peace upon Muhammad, the Unlettered Prophet, and his family.",
        "benefit": "جمعہ المبارک کے دن پڑھنے کی خصوصی فضیلت۔"
    },
]


def reshape_text_for_display(raw_text: str) -> str:
    """Helper to reshape Arabic and Urdu text for proper connected RTL character display."""
    if not raw_text or not raw_text.strip():
        return ""
    try:
        reshaped = arabic_reshaper.reshape(raw_text)
        return get_display(reshaped)
    except Exception as e:
        logger.warning(f"Reshaping fallback for text: {e}")
        return raw_text


def get_darood_list() -> list[dict]:
    """Return all Darood items for UI selection, merging built-in and offline JSON additions."""
    items = list(DAROOD_CATALOG)
    json_path = os.path.join(utils.root_dir(), "resource", "darood_data", "darood_collection.json")
    if os.path.exists(json_path):
        try:
            import json
            with open(json_path, "r", encoding="utf-8") as f:
                offline_items = json.load(f)
                existing_ids = {i["id"] for i in items}
                for oi in offline_items:
                    item_dict = {
                        "id": oi.get("id", f"custom_{len(items)}"),
                        "title": oi.get("name", oi.get("title", "Custom Darood")),
                        "arabic": oi.get("arabic", ""),
                        "urdu": oi.get("translation", oi.get("urdu", "")),
                        "english": oi.get("english", ""),
                        "benefit": oi.get("benefit", "خاص درود شریف"),
                    }
                    if item_dict["id"] not in existing_ids:
                        items.append(item_dict)
                        existing_ids.add(item_dict["id"])
        except Exception as e:
            logger.warning(f"Failed to load offline Darood collection JSON: {e}")
    return items


def add_custom_darood(title: str, arabic: str, urdu: str = "", english: str = "", benefit: str = "") -> dict:
    """Dynamically add a new custom Darood / Islamic text to the collection."""
    import json
    darood_dir = os.path.join(utils.root_dir(), "resource", "darood_data")
    os.makedirs(darood_dir, exist_ok=True)
    json_path = os.path.join(darood_dir, "darood_collection.json")

    item_id = f"custom_{int(datetime.datetime.now().timestamp())}"
    new_entry = {
        "id": item_id,
        "name": title,
        "title": title,
        "arabic": arabic.strip(),
        "translation": urdu.strip(),
        "urdu": urdu.strip(),
        "english": english.strip(),
        "benefit": benefit.strip() or "خاص اسلامک متن",
    }

    current_data = []
    if os.path.exists(json_path):
        try:
            with open(json_path, "r", encoding="utf-8") as f:
                current_data = json.load(f)
        except Exception:
            current_data = []

    current_data.append(new_entry)
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(current_data, f, ensure_ascii=False, indent=2)

    DAROOD_CATALOG.append(new_entry)
    logger.info(f"➕ Added custom Darood entry: {title}")
    return new_entry


def get_darood_by_id(darood_id: str) -> dict:
    """Find specific Darood item by ID."""
    all_items = get_darood_list()
    for item in all_items:
        if item["id"] == darood_id:
            return item
    return all_items[0] if all_items else DAROOD_CATALOG[0]


def get_daily_rotating_darood() -> dict:
    """Automatically select today's Darood Shareef based on day of year."""
    day_of_year = datetime.datetime.now().timetuple().tm_yday
    idx = (day_of_year - 1) % len(DAROOD_CATALOG)
    item = DAROOD_CATALOG[idx].copy()
    item["daily_note"] = f"Today's Special Darood (Day {day_of_year})"
    return item


def create_dynamic_phrase_card(
    darood_item: dict,
    arabic_phrase: str,
    urdu_phrase: str,
    width: int = 1080,
    height: int = 1920,
    show_box: bool = False,
    pure_arabic_only: bool = True,
) -> Image.Image:
    """
    Render a clean, borderless overlay displaying pure Arabic calligraphy + optional Urdu text directly over video.
    """
    img = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    root = utils.root_dir()
    f_arabic_path = os.path.join(root, "resource", "fonts", "UthmanicHafs.ttf")
    f_urdu_path = os.path.join(root, "resource", "fonts", "JameelNooriNastaleeq.ttf")

    try:
        font_arabic = ImageFont.truetype(f_arabic_path, 64)
    except Exception:
        font_arabic = ImageFont.load_default()

    try:
        font_urdu = ImageFont.truetype(f_urdu_path, 38)
    except Exception:
        font_urdu = ImageFont.load_default()

    try:
        font_badge = ImageFont.truetype(f_urdu_path, 28)
    except Exception:
        font_badge = ImageFont.load_default()

    # Optional box frame (only if show_box is True)
    if show_box:
        card_w = int(width * 0.90)
        card_h = int(height * 0.45)
        c_x1 = (width - card_w) // 2
        c_y1 = (height - card_h) // 2
        c_x2 = c_x1 + card_w
        c_y2 = c_y1 + card_h
        draw.rounded_rectangle([c_x1, c_y1, c_x2, c_y2], radius=24, fill=(0, 0, 0, 140), outline=(255, 215, 0, 180), width=2)

    # Active Spoken Arabic Phrase (Pure Arabic Calligraphy with Drop Shadow & Gold Glow)
    arabic_lines = textwrap.wrap(arabic_phrase, width=26)
    
    total_lines = len(arabic_lines)
    if not pure_arabic_only and urdu_phrase:
        total_lines += len(textwrap.wrap(urdu_phrase, width=32)) + 1

    y_start = (height // 2) - (total_lines * 40)
    y_curr = y_start

    for line in arabic_lines:
        line_shaped = reshape_text_for_display(line)
        # Deep drop shadow for maximum legibility over moving video
        for dx, dy in [(-3, -3), (3, -3), (-3, 3), (3, 3), (0, 3), (0, -3), (3, 0), (-3, 0)]:
            draw.text((width // 2 + dx, y_curr + dy), line_shaped, fill=(0, 0, 0, 240), font=font_arabic, anchor="mm")
        
        draw.text((width // 2, y_curr), line_shaped, fill=(255, 215, 0), font=font_arabic, anchor="mm")
        y_curr += 85

    # Optional Urdu Subtitle (Crisp White with drop shadow at bottom edge)
    if not pure_arabic_only and urdu_phrase.strip():
        y_curr += 20
        urdu_lines = textwrap.wrap(urdu_phrase, width=34)
        for line in urdu_lines:
            line_shaped = reshape_text_for_display(line)
            draw.text((width // 2 + 2, y_curr + 2), line_shaped, fill=(0, 0, 0, 220), font=font_urdu, anchor="mm")
            draw.text((width // 2, y_curr), line_shaped, fill=(255, 255, 255), font=font_urdu, anchor="mm")
            y_curr += 55

    return img


def generate_darood_video(
    darood_item: dict,
    voice_name: str = "ar-SA-HamedNeural",
    aspect_ratio: str = "portrait",
    background_type: str = "driving",
    custom_audio_path: str = "",
    show_box: bool = False,
    pure_arabic_only: bool = True,
    logo_path: str = "",
    logo_position: str = "top_right",
    logo_size: int = 120,
    logo_opacity: float = 0.90,
    output_filename: str = "darood_video.mp4",
) -> str:
    """
    ⚡ Exact Facebook Reel Style Darood Video Generator with Custom Channel Logo Watermark.
    Features: Channel Logo Overlay, No Box Frame, Pure Arabic Calligraphy, Custom Audio Support, Multi-Category Pexels 4K Footage.
    """
    output_dir = os.path.join(utils.root_dir(), "storage", "darood_videos")
    os.makedirs(output_dir, exist_ok=True)
    out_path = os.path.join(output_dir, output_filename)

    logger.info(f"Generating Reel Video for {darood_item['title']} (Theme: {background_type})")

    # 1. Audio Source (Custom Uploaded MP3 OR Generated Edge-TTS Recitation)
    temp_audio = ""
    if custom_audio_path and os.path.exists(custom_audio_path) and os.path.getsize(custom_audio_path) > 0:
        logger.info(f"Using Custom Audio file: {custom_audio_path}")
        audio_file_to_use = custom_audio_path
    else:
        temp_audio = os.path.join(output_dir, f"darood_audio_{random.randint(1000,9999)}.mp3")
        if not voice_name or "kokoro" in voice_name.lower() or "bella" in voice_name.lower():
            voice_name = "ar-SA-HamedNeural"

        script_text = darood_item['arabic']
        voice.tts(
            text=script_text,
            voice_name=voice_name,
            voice_rate=0.88,  # Emotional, slow recitation speed
            voice_file=temp_audio,
        )
        if not os.path.exists(temp_audio):
            raise RuntimeError("Failed to generate Darood audio recitation.")
        audio_file_to_use = temp_audio

    try:
        from moviepy.video.io.VideoFileClip import VideoFileClip
        from moviepy.audio.io.AudioFileClip import AudioFileClip
        from moviepy.audio.AudioClip import CompositeAudioClip
        from moviepy.audio.fx.MultiplyVolume import MultiplyVolume
        from moviepy.video.VideoClip import ImageClip, ColorClip
        from moviepy.video.compositing.CompositeVideoClip import CompositeVideoClip
        from moviepy.video.fx.Loop import Loop

        raw_audio_clip = AudioFileClip(audio_file_to_use)
        duration = raw_audio_clip.duration
        w, h = (1080, 1920) if aspect_ratio == "portrait" else (1920, 1080)

        # 🛡️ Automatic Anti-Copyright Audio Protection (Ambient Rain ASMR Layering)
        asmr_path = os.path.join(utils.root_dir(), "resource", "audio", "rain_asmr.wav")
        if os.path.exists(asmr_path):
            try:
                rain_bg = AudioFileClip(asmr_path)
                if rain_bg.duration < duration:
                    rain_bg = rain_bg.with_effects([Loop(duration=duration)])
                else:
                    rain_bg = rain_bg.subclipped(0, duration)
                
                # Soft ambient volume (-22dB = 0.08 multiplier)
                rain_bg = rain_bg.with_effects([MultiplyVolume(0.08)])
                audio_clip = CompositeAudioClip([raw_audio_clip, rain_bg])
                logger.info("🛡️ Applied automatic Anti-Copyright ASMR Audio Protection mixing!")
            except Exception as asmr_err:
                logger.warning(f"ASMR audio mixing fallback: {asmr_err}")
                audio_clip = raw_audio_clip
        else:
            audio_clip = raw_audio_clip

        # Clear old cache and RAM to ensure a fresh video is fetched
        try:
            material.clear_video_cache()
        except Exception as cache_err:
            logger.warning(f"Cache clear warning in Darood service: {cache_err}")

        # 2. Multi-Category Background Video Sourcing
        theme_keywords = {
            "driving": ["scenic drive rain", "foggy mountain road", "rainy car window", "sunset driving pov", "highway driving night"],
            "islamic": ["islamic architecture", "mosque sunset", "kaaba madinah", "peaceful mosque", "quran lighting"],
            "rain": ["rain on glass window", "rainy forest", "scenic rain driving", "water drops window"],
            "nature": ["peaceful sunset clouds", "night sky stars", "mountain sunset nature", "flowing river forest"],
        }

        keywords_list = theme_keywords.get(background_type.lower(), theme_keywords["driving"])
        term = random.choice(keywords_list)
        logger.info(f"Searching Pexels for theme '{background_type}' video: '{term}'")

        video_clip = None
        try:
            v_aspect = VideoAspect.portrait if aspect_ratio == "portrait" else VideoAspect.landscape
            items = material.search_videos_pexels(term, minimum_duration=5, video_aspect=v_aspect)
            if items:
                v_clips = []
                selected_items = items[:min(6, len(items))]
                random.shuffle(selected_items)
                curr_t = 0.0

                for item_obj in selected_items:
                    if curr_t >= duration:
                        break
                    v_path = material.save_video(item_obj.url, search_term=term)
                    if os.path.exists(v_path) and os.path.getsize(v_path) > 5000:
                        raw_c = VideoFileClip(v_path)
                        sub_dur = min(4.0, raw_c.duration, max(1.0, duration - curr_t))
                        c_trimmed = raw_c.subclipped(0, sub_dur)

                        # Resize & Crop to exact (w, h)
                        vw, vh = c_trimmed.size
                        if vw != w or vh != h:
                            scale = max(w / float(vw), h / float(vh))
                            nw, nh = int(vw * scale), int(vh * scale)
                            c_trimmed = c_trimmed.resized((nw, nh))
                            cx, cy = (nw - w) // 2, (nh - h) // 2
                            c_trimmed = c_trimmed.cropped(x1=cx, y1=cy, width=w, height=h)

                        v_clips.append(c_trimmed)
                        curr_t += sub_dur

                if v_clips:
                    # Loop concatenated clips sequence if needed to cover full duration
                    full_concat = concatenate_videoclips(v_clips)
                    if full_concat.duration < duration:
                        full_concat = full_concat.with_effects([Loop(duration=duration)])
                    else:
                        full_concat = full_concat.subclipped(0, duration)
                    video_clip = full_concat
        except Exception as pexels_err:
            logger.warning(f"Pexels video download fallback: {pexels_err}")

        # Fallback to ColorClip if video search fails
        if video_clip is None:
            video_clip = ColorClip(size=(w, h), color=(10, 22, 16), duration=duration)

        # Subtle dark overlay mask to boost text contrast over bright scenes
        dark_mask = ColorClip(size=(w, h), color=(0, 0, 0), duration=duration)
        if hasattr(dark_mask, "with_opacity"):
            dark_mask = dark_mask.with_opacity(0.30)
        else:
            dark_mask = dark_mask.set_opacity(0.30)

        # 3. Dynamic Subtitle Overlay Clips (Borderless Pure Arabic)
        arabic_phrases = [p.strip() for p in re.split(r'[۞٫.]', darood_item["arabic"]) if p.strip()]
        urdu_phrases = [p.strip() for p in re.split(r'[۞٫.]', darood_item["urdu"]) if p.strip()]

        if not arabic_phrases:
            arabic_phrases = [darood_item["arabic"]]
        if not urdu_phrases:
            urdu_phrases = [darood_item["urdu"]]

        num_phrases = max(len(arabic_phrases), len(urdu_phrases))
        phrase_duration = duration / float(num_phrases)

        overlay_clips = []
        for i in range(num_phrases):
            ar_p = arabic_phrases[i % len(arabic_phrases)]
            ur_p = urdu_phrases[i % len(urdu_phrases)]

            card_img = create_dynamic_phrase_card(
                darood_item,
                ar_p,
                ur_p,
                width=w,
                height=h,
                show_box=show_box,
                pure_arabic_only=pure_arabic_only
            )
            card_arr = np.array(card_img)

            start_t = i * phrase_duration
            end_t = min(duration, (i + 1) * phrase_duration)

            if hasattr(ImageClip, "with_duration"):
                ic = ImageClip(card_arr).with_duration(end_t - start_t)
            else:
                ic = ImageClip(card_arr).set_duration(end_t - start_t)

            if hasattr(ic, "with_start"):
                ic = ic.with_start(start_t)
            else:
                ic = ic.set_start(start_t)

            overlay_clips.append(ic)

        # 🏷️ 3.5. Channel Logo Watermark Overlay
        logo_clip = None
        if logo_path and os.path.exists(logo_path) and os.path.getsize(logo_path) > 0:
            try:
                raw_logo = ImageClip(logo_path)
                if hasattr(raw_logo, "with_duration"):
                    raw_logo = raw_logo.with_duration(duration)
                else:
                    raw_logo = raw_logo.set_duration(duration)

                if hasattr(raw_logo, "resized"):
                    raw_logo = raw_logo.resized(width=logo_size)
                else:
                    raw_logo = raw_logo.resize(width=logo_size)

                if hasattr(raw_logo, "with_opacity"):
                    raw_logo = raw_logo.with_opacity(logo_opacity)
                else:
                    raw_logo = raw_logo.set_opacity(logo_opacity)

                margin = 35
                pos_map = {
                    "top_right": (w - logo_size - margin, margin),
                    "top_left": (margin, margin),
                    "top_center": ((w - logo_size) // 2, margin),
                    "bottom_right": (w - logo_size - margin, h - raw_logo.h - margin),
                    "bottom_left": (margin, h - raw_logo.h - margin),
                }
                pos = pos_map.get(logo_position.lower(), pos_map["top_right"])

                if hasattr(raw_logo, "with_position"):
                    raw_logo = raw_logo.with_position(pos)
                else:
                    raw_logo = raw_logo.set_position(pos)

                logo_clip = raw_logo
                logger.info(f"🏷️ Channel Logo overlaid at position '{logo_position}', width: {logo_size}px")
            except Exception as logo_err:
                logger.warning(f"Channel logo overlay fallback: {logo_err}")

        # 4. Composite Final Video (Video + Dark Tint + Subtitles + Channel Logo)
        all_clips = [video_clip, dark_mask] + overlay_clips
        if logo_clip is not None:
            all_clips.append(logo_clip)

        final_video = CompositeVideoClip(all_clips)

        if hasattr(final_video, "with_audio"):
            final_video = final_video.with_audio(audio_clip)
        else:
            final_video = final_video.set_audio(audio_clip)

        final_video.write_videofile(
            out_path,
            fps=24,
            codec="libx264",
            audio_codec="aac",
            preset="fast",
            threads=4,
            logger=None
        )

        audio_clip.close()
        video_clip.close()
        dark_mask.close()
        if logo_clip is not None:
            logo_clip.close()
        for c in overlay_clips:
            c.close()
        final_video.close()

        if temp_audio and os.path.exists(temp_audio):
            try:
                os.remove(temp_audio)
            except Exception:
                pass

        # Save to dedicated section folder storage/darood_videos/
        darood_out_dir = os.path.join(utils.root_dir(), "storage", "darood_videos")
        os.makedirs(darood_out_dir, exist_ok=True)
        final_darood_video = os.path.join(darood_out_dir, f"darood_{darood_id}_{task_id[:8]}.mp4")

        import shutil
        if os.path.exists(out_path):
            shutil.copy(out_path, final_darood_video)

        logger.success(f"Viral Darood Video saved to dedicated folder: {final_darood_video}")
        return final_darood_video
    except Exception as ex:
        logger.error(f"Failed to generate Reel Video: {ex}")
        raise ex
