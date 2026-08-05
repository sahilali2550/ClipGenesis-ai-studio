"""
quran_api.py — Quran.com API v4 integration
Fetches: Arabic text, Urdu/English translation, word timings, recitation audio
All APIs are FREE — no key required.
"""

import os
import time
import requests
from typing import Optional
from loguru import logger
from app.utils import utils


BASE_URL = "https://api.quran.com/api/v4"
AUDIO_BASE = "https://verses.quran.com"
CDN_BASE = "https://cdn.islamic.network/quran/audio"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

# ── Popular & Viral Reciters ──────────────────────────────────────────────────
RECITERS = {
    "🔥 Yasser Al-Dosari (یاسر الدوسري) — Viral Reels ⭐":   {"id": 161, "slug": "ar.yasserdussary",     "everyayah": "Yasser_Ad-Dussary_128kbps"},
    "Mishary Al-Afasy (مشاری العفاسی) ⭐":                 {"id": 7,   "slug": "ar.alafasy",           "everyayah": "Alafasy_128kbps"},
    "🔥 Nasser Al-Qatami (ناصر القطامي) — Viral ⭐":       {"id": 166, "slug": "ar.nasseralqatami",   "everyayah": "Nasser_Alqatami_128kbps"},
    " Mohamed Siddiq Al-Minshawi (Mujawwad)":             {"id": 8,   "slug": "ar.minshawimujawwad", "everyayah": "Minshawy_Mujawwad_192kbps"},
    " Mohamed Siddiq Al-Minshawi (Murattal)":             {"id": 9,   "slug": "ar.minshawi",         "everyayah": "Minshawy_Murattal_128kbps"},
    " Abdul Basit (Mujawwad)":                            {"id": 2,   "slug": "ar.abdulsamad",       "everyayah": "Abdul_Basit_Mujawwad_128kbps"},
    " Abdul Basit (Murattal)":                            {"id": 1,   "slug": "ar.abdulsamad",       "everyayah": "Abdul_Basit_Murattal_192kbps"},
    " Abu Bakr Al-Shatri (أبو بكر الشاطري)":              {"id": 4,   "slug": "ar.shaatree",         "everyayah": "Abu_Bakr_Ash-Shaatree_128kbps"},
    " Maher Al-Mueaqly (ماهر المعيقلي)":                    {"id": 9,   "slug": "ar.mahermuaiqly",     "everyayah": "MaherAlMuaiqly128kbps"},
    " Abdur-Rahman As-Sudais (إمام الحرم)":                {"id": 3,   "slug": "ar.abdurrahmaansudais", "everyayah": "Abdurrahmaan_As-Sudais_192kbps"},
    " Saud Al-Shuraym (سعود الشريم)":                      {"id": 10,  "slug": "ar.saoodshuraym",     "everyayah": "Saood_ash-Shuraym_128kbps"},
    " Saad Al-Ghamdi (سعد الغامدي)":                       {"id": 8,   "slug": "ar.ghanim",           "everyayah": "Ghamadi_40kbps"},
    " Mahmoud Al-Hussary (الحصري)":                       {"id": 6,   "slug": "ar.husary",           "everyayah": "Husary_128kbps"},
    " Hani Ar-Rifai (هاني الرفاعي)":                       {"id": 5,   "slug": "ar.hanirifai",        "everyayah": "Hani_Rifai_192kbps"},
    " Ali Jaber (علي جابر)":                              {"id": 167, "slug": "ar.alijaber",         "everyayah": "Ali_Jaber_64kbps"},
}

# ── Translation editions ──────────────────────────────────────────────────────
TRANSLATIONS = {
    "اردو (جالندھری)":    "ur.jalandhry",
    "اردو (احمد علی)":    "ur.ahmedali",
    "English (Sahih Int)": "en.sahih",
    "English (Yusuf Ali)": "en.yusufali",
    "None":               None,
}

# ── Surah names ───────────────────────────────────────────────────────────────
SURAH_NAMES = {
    1: "Al-Fatiha", 2: "Al-Baqarah", 3: "Aali Imran", 4: "An-Nisa",
    5: "Al-Maidah", 6: "Al-Anam", 7: "Al-Araf", 8: "Al-Anfal",
    9: "At-Tawbah", 10: "Yunus", 11: "Hud", 12: "Yusuf",
    13: "Ar-Rad", 14: "Ibrahim", 15: "Al-Hijr", 16: "An-Nahl",
    17: "Al-Isra", 18: "Al-Kahf", 19: "Maryam", 20: "Ta-Ha",
    21: "Al-Anbiya", 22: "Al-Hajj", 23: "Al-Muminun", 24: "An-Nur",
    25: "Al-Furqan", 26: "Ash-Shuara", 27: "An-Naml", 28: "Al-Qasas",
    29: "Al-Ankabut", 30: "Ar-Rum", 31: "Luqman", 32: "As-Sajdah",
    33: "Al-Ahzab", 34: "Saba", 35: "Fatir", 36: "Ya-Sin",
    37: "As-Saffat", 38: "Sad", 39: "Az-Zumar", 40: "Ghafir",
    41: "Fussilat", 42: "Ash-Shura", 43: "Az-Zukhruf", 44: "Ad-Dukhan",
    45: "Al-Jathiyah", 46: "Al-Ahqaf", 47: "Muhammad", 48: "Al-Fath",
    49: "Al-Hujurat", 50: "Qaf", 51: "Adh-Dhariyat", 52: "At-Tur",
    53: "An-Najm", 54: "Al-Qamar", 55: "Ar-Rahman", 56: "Al-Waqiah",
    57: "Al-Hadid", 58: "Al-Mujadila", 59: "Al-Hashr", 60: "Al-Mumtahanah",
    61: "As-Saf", 62: "Al-Jumuah", 63: "Al-Munafiqun", 64: "At-Taghabun",
    65: "At-Talaq", 66: "At-Tahrim", 67: "Al-Mulk", 68: "Al-Qalam",
    69: "Al-Haqqah", 70: "Al-Maarij", 71: "Nuh", 72: "Al-Jinn",
    73: "Al-Muzzammil", 74: "Al-Muddaththir", 75: "Al-Qiyamah", 76: "Al-Insan",
    77: "Al-Mursalat", 78: "An-Naba", 79: "An-Naziat", 80: "Abasa",
    81: "At-Takwir", 82: "Al-Infitar", 83: "Al-Mutaffifin", 84: "Al-Inshiqaq",
    85: "Al-Buruj", 86: "At-Tariq", 87: "Al-Ala", 88: "Al-Ghashiyah",
    89: "Al-Fajr", 90: "Al-Balad", 91: "Ash-Shams", 92: "Al-Layl",
    93: "Ad-Duha", 94: "Ash-Sharh", 95: "At-Tin", 96: "Al-Alaq",
    97: "Al-Qadr", 98: "Al-Bayyinah", 99: "Az-Zalzalah", 100: "Al-Adiyat",
    101: "Al-Qariah", 102: "At-Takathur", 103: "Al-Asr", 104: "Al-Humazah",
    105: "Al-Fil", 106: "Quraysh", 107: "Al-Maun", 108: "Al-Kawthar",
    109: "Al-Kafirun", 110: "An-Nasr", 111: "Al-Masad", 112: "Al-Ikhlas",
    113: "Al-Falaq", 114: "An-Nas",
}

# Ayah counts per Surah
AYAH_COUNTS = {
    1:7,2:286,3:200,4:176,5:120,6:165,7:206,8:75,9:129,10:109,
    11:123,12:111,13:43,14:52,15:99,16:128,17:111,18:110,19:98,20:135,
    21:112,22:78,23:118,24:64,25:77,26:227,27:93,28:88,29:69,30:60,
    31:34,32:30,33:73,34:54,35:45,36:83,37:182,38:88,39:75,40:85,
    41:54,42:53,43:89,44:59,45:37,46:35,47:38,48:29,49:18,50:45,
    51:60,52:49,53:62,54:55,55:78,56:96,57:29,58:22,59:24,60:13,
    61:14,62:11,63:11,64:18,65:12,66:12,67:30,68:52,69:52,70:44,
    71:28,72:28,73:20,74:56,75:40,76:31,77:50,78:40,79:46,80:42,
    81:29,82:19,83:36,84:25,85:22,86:17,87:19,88:26,89:30,90:20,
    91:15,92:21,93:11,94:8,95:8,96:19,97:5,98:8,99:8,100:11,
    101:11,102:8,103:3,104:9,105:5,106:4,107:7,108:3,109:6,110:3,
    111:5,112:4,113:5,114:6,
}


def get_surah_info(surah_number: int) -> dict:
    """Get Surah metadata."""
    return {
        "number": surah_number,
        "name": SURAH_NAMES.get(surah_number, f"Surah {surah_number}"),
        "ayah_count": AYAH_COUNTS.get(surah_number, 0),
    }


def get_ayahs_arabic(surah: int, from_ayah: int, to_ayah: int) -> list[dict]:
    """
    Fetch Arabic text for a range of ayahs.
    Returns list of {"ayah": int, "arabic": str, "key": "surah:ayah"}
    """
    results = []
    try:
        url = f"{BASE_URL}/verses/by_chapter/{surah}"
        params = {
            "language": "ar",
            "words": "true",
            "word_fields": "text_uthmani,position",
            "fields": "text_uthmani",
            "per_page": 50,
            "page": 1,
        }
        resp = requests.get(url, params=params, timeout=15)
        resp.raise_for_status()
        verses = resp.json().get("verses", [])
        for v in verses:
            ayah_num = v.get("verse_number", 0)
            if from_ayah <= ayah_num <= to_ayah:
                results.append({
                    "ayah": ayah_num,
                    "arabic": v.get("text_uthmani", ""),
                    "key": f"{surah}:{ayah_num}",
                    "words": [w.get("text_uthmani", "") for w in v.get("words", [])],
                })
    except Exception as e:
        logger.error(f"Quran API error (arabic): {e}")
    return results


def get_translations(surah: int, from_ayah: int, to_ayah: int,
                     edition: str = "ur.jalandhry") -> dict:
    """
    Fetch translation for a range of ayahs.
    Returns dict {ayah_number: translation_text}
    """
    translations = {}
    if not edition:
        return translations
    try:
        url = f"{BASE_URL}/verses/by_chapter/{surah}"
        params = {
            "translations": edition,
            "per_page": 50,
            "page": 1,
        }
        resp = requests.get(url, params=params, timeout=15)
        resp.raise_for_status()
        verses = resp.json().get("verses", [])
        for v in verses:
            ayah_num = v.get("verse_number", 0)
            if from_ayah <= ayah_num <= to_ayah:
                tr_list = v.get("translations", [])
                if tr_list:
                    # Strip HTML tags
                    import re
                    text = re.sub(r"<[^>]+>", "", tr_list[0].get("text", ""))
                    translations[ayah_num] = text
    except Exception as e:
        logger.error(f"Quran API error (translation): {e}")
    return translations


def get_word_timings(surah: int, ayah: int, reciter_id: int = 7) -> list[dict]:
    """
    Fetch word-level timestamps for a single ayah.
    Returns list of {"word": str, "position": int, "start_ms": int, "end_ms": int}
    """
    timings = []
    try:
        key = f"{surah}:{ayah}"
        url = f"{BASE_URL}/verses/by_key/{key}"
        params = {
            "words": "true",
            "word_fields": "text_uthmani,position,location",
            "audio": reciter_id,
            "fields": "text_uthmani",
        }
        resp = requests.get(url, params=params, headers=HEADERS, timeout=15)
        resp.raise_for_status()
        verse = resp.json().get("verse", {})
        words = verse.get("words", [])
        audio_info = verse.get("audio", {})
        segments = audio_info.get("segments", []) if isinstance(audio_info, dict) else []

        seg_map = {}
        for seg in segments:
            if len(seg) >= 4:
                w_pos = seg[1]
                st_ms = seg[2]
                ed_ms = seg[3]
                seg_map[w_pos] = (st_ms, ed_ms)

        for w in words:
            char_type = w.get("char_type_name", "word")
            word_text = w.get("text_uthmani", "")
            pos = w.get("position", 0)

            if char_type == "end" or not word_text:
                continue

            st_ms, ed_ms = seg_map.get(pos, (0, 0))
            timings.append({
                "word": word_text,
                "position": pos,
                "start_ms": st_ms,
                "end_ms": ed_ms,
            })
    except Exception as e:
        logger.warning(f"Word timing fetch failed for {surah}:{ayah}: {e}")
    return timings



def get_global_verse_number(surah: int, ayah: int) -> int:
    num = 0
    for s in range(1, surah):
        num += AYAH_COUNTS.get(s, 0)
    return num + ayah


def download_audio(surah: int, ayah: int, reciter_key_or_slug: str = "Mishary Al-Afasy",
                   output_dir: str = "") -> Optional[str]:
    """
    Download recitation MP3 for a single ayah.
    Uses Quran.com API -> Islamic Network CDN fallback.
    """
    if not output_dir:
        output_dir = utils.storage_dir("quran_audio", create=True)
    os.makedirs(output_dir, exist_ok=True)

    # Determine reciter_id and slug
    if reciter_key_or_slug in RECITERS:
        r_info = RECITERS[reciter_key_or_slug]
    else:
        # Fallback search by slug or name
        r_info = next((v for k, v in RECITERS.items() if v.get("slug") == reciter_key_or_slug), list(RECITERS.values())[0])

    reciter_id = r_info.get("id", 7)
    reciter_slug = r_info.get("slug", "ar.alafasy")

    filename = f"{surah:03d}_{ayah:03d}_r{reciter_id}.mp3"
    filepath = os.path.join(output_dir, filename)
    if os.path.exists(filepath) and os.path.getsize(filepath) > 1000:
        return filepath

    # Method 1: EveryAyah CDN Direct Download (High Quality & Fast)
    everyayah_slug = r_info.get("everyayah", "")
    if everyayah_slug:
        try:
            ea_url = f"https://everyayah.com/data/{everyayah_slug}/{surah:03d}{ayah:03d}.mp3"
            res = requests.get(ea_url, headers=HEADERS, timeout=(4, 8))
            if res.status_code == 200 and len(res.content) > 1000:
                with open(filepath, "wb") as f:
                    f.write(res.content)
                logger.info(f"Downloaded (EveryAyah CDN): {surah}:{ayah} → {filename}")
                return filepath
        except Exception as e:
            logger.warning(f"EveryAyah audio fetch failed for {surah}:{ayah}: {e}")

    # Method 2: Quran.com API v4
    try:
        url = f"{BASE_URL}/verses/by_key/{surah}:{ayah}"
        params = {"audio": reciter_id}
        resp = requests.get(url, params=params, headers=HEADERS, timeout=(3, 5))
        if resp.status_code == 200:
            audio_url = resp.json().get("verse", {}).get("audio", {}).get("url", "")
            if audio_url:
                full_url = audio_url if audio_url.startswith("http") else f"https://verses.quran.com/{audio_url}"
                res = requests.get(full_url, headers=HEADERS, timeout=(3, 6), stream=True)
                if res.status_code == 200 and len(res.content) > 1000:
                    with open(filepath, "wb") as f:
                        f.write(res.content)
                    logger.info(f"Downloaded (Quran.com API): {surah}:{ayah} → {filename}")
                    return filepath
    except Exception as e:
        logger.warning(f"Quran.com API audio fetch failed for {surah}:{ayah}: {e}")

    # Method 3: Islamic Network CDN with global verse index
    try:
        g_verse = get_global_verse_number(surah, ayah)
        cdn_url = f"{CDN_BASE}/128/{reciter_slug}/{g_verse}.mp3"
        res = requests.get(cdn_url, headers=HEADERS, timeout=(3, 6))
        if res.status_code == 200 and len(res.content) > 1000:
            with open(filepath, "wb") as f:
                f.write(res.content)
            logger.info(f"Downloaded (Islamic Network CDN): {surah}:{ayah} → {filename}")
            return filepath
    except Exception as e:
        logger.warning(f"CDN audio download failed for {surah}:{ayah}: {e}")

    logger.error(f"All audio download methods failed ({surah}:{ayah})")
    return None


def download_ayahs_audio(surah: int, from_ayah: int, to_ayah: int,
                          reciter_name: str = "Mishary Al-Afasy",
                          output_dir: str = "",
                          progress_cb=None) -> list[str]:
    """Download audio for a range of ayahs. Returns list of file paths."""
    files = []
    total = to_ayah - from_ayah + 1
    for i, ayah in enumerate(range(from_ayah, to_ayah + 1)):
        path = download_audio(surah, ayah, reciter_name, output_dir)
        if path:
            files.append(path)
        if progress_cb:
            progress_cb((i + 1) / total)
        time.sleep(0.1)
    return files


def get_reciters_list() -> dict:
    """Return the available reciters dict."""
    return RECITERS
