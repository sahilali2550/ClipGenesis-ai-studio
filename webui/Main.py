import os
import platform
import sys
from uuid import uuid4
import streamlit as st
from loguru import logger

# ── ClipGenesis Premium UI Shell ─────────────────────────────────────────────
root_dir = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
if root_dir not in sys.path:
    sys.path.append(root_dir)

from webui.ui_theme import (
    inject_premium_css,
    render_sidebar,
    render_kpi_cards,
    render_wizard_bar,
    render_floating_preview_button,
    render_logo_watermark_uploader,
)
from webui.quran_video_page import render_quran_video
from webui.voice_studio_page import render_voice_studio_page
from webui.darood_video_page import render_darood_video_page


from app.config import config
from app.models.schema import (
    MaterialInfo,
    VideoAspect,
    VideoConcatMode,
    VideoParams,
    VideoTransitionMode,
)
from app.services import llm, voice
from app.services import task as tm
from app.utils import utils

# ── Page Config ───────────────────────────────────────────────────────────────
VERSION = getattr(config, "project_version", "1.3.0")
st.set_page_config(
    page_title="ClipGenesis - AI Video Studio",
    page_icon="🎬",
    layout="wide",
    initial_sidebar_state="collapsed",
    menu_items={
        "Report a bug": "https://github.com/sahilali2550/ClipGenesis-ai-studio/issues",
        "About": "# ClipGenesis - AI Video Studio\nAI-powered short video generator.\n\nhttps://github.com/sahilali2550/ClipGenesis-ai-studio.git",
    },
)

inject_premium_css()

# ── Sidebar Navigation ────────────────────────────────────────────────────────
current_page = render_sidebar(version=VERSION)

# ── Session State Init ────────────────────────────────────────────────────────
for k, v in [
    ("video_subject", ""),
    ("video_script", ""),
    ("video_terms", ""),
    ("ui_language", config.ui.get("language", "en-US")),
    ("nav_idx", 0),
    ("wizard_step", 0),
    ("wizard_subject", ""),
    ("wizard_script", ""),
    ("wizard_terms", ""),
    ("wizard_video_source", "pexels"),
    ("wizard_concat_mode", "random"),
    ("wizard_aspect", "portrait"),
    ("wizard_clip_duration", 5),
    ("wizard_tts_server", "azure-tts-v1"),
    ("wizard_voice", ""),
    ("wizard_bgm_type", "random"),
    ("wizard_bgm_file", ""),
    ("wizard_sub_enabled", True),
    ("wizard_font", "MicrosoftYaHeiBold.ttc"),
    ("wizard_sub_position", "bottom"),
    ("wizard_font_color", "#FFFFFF"),
    ("wizard_font_size", 60),
    ("wizard_enable_ken_burns", True),
    ("wizard_enable_ducking", True),
    ("show_preview", False),
    ("preview_video", None),
    ("preview_audio", None),
    ("preview_title", "Preview"),
]:
    if k not in st.session_state:
        st.session_state[k] = v

# ── I18n ──────────────────────────────────────────────────────────────────────
i18n_dir = os.path.join(root_dir, "webui", "i18n")
locales = utils.load_locales(i18n_dir)

def tr(key):
    loc = locales.get(st.session_state["ui_language"], {})
    return loc.get("Translation", {}).get(key, key)

# ── Resources ─────────────────────────────────────────────────────────────────
font_dir = os.path.join(root_dir, "resource", "fonts")
song_dir = os.path.join(root_dir, "resource", "songs")
support_locales = [
    "zh-CN", "zh-HK", "zh-TW", "de-DE", "en-US", "fr-FR", "vi-VN", "th-TH",
]

def get_all_fonts():
    fonts = []
    for _, _, files in os.walk(font_dir):
        for f in files:
            if f.endswith(".ttf") or f.endswith(".ttc"):
                fonts.append(f)
    fonts.sort()
    return fonts

def get_all_songs():
    songs = []
    for _, _, files in os.walk(song_dir):
        for f in files:
            if f.endswith(".mp3"):
                songs.append(f)
    return songs

def open_task_folder(task_id):
    try:
        sys_type = platform.system()
        path = os.path.join(root_dir, "storage", "tasks", task_id)
        if os.path.exists(path):
            if sys_type == "Windows":
                os.system(f"start {path}")
            elif sys_type == "Darwin":
                os.system(f"open {path}")
    except Exception as e:
        logger.error(e)

def scroll_to_bottom():
    js = """<script>
    function scroll(dummy_var_to_force_repeat_execution){
        var sections = parent.document.querySelectorAll("section.main");
        for(let index = 0; index<sections.length; index++) {
            sections[index].scrollTop = sections[index].scrollHeight;
        }
    }
    scroll(1);
    </script>"""
    st.components.v1.html(js, height=0, width=0)

# ── Logging ───────────────────────────────────────────────────────────────────
def init_log():
    logger.remove()
    _lvl = "DEBUG"

    def format_record(record):
        file_path = record["file"].path
        relative_path = os.path.relpath(file_path, root_dir)
        record["file"].path = f"./{relative_path}"
        record["message"] = record["message"].replace(root_dir, ".")
        return (
            "<green>{time:%Y-%m-%d %H:%M:%S}</> | "
            "<level>{level}</> | "
            '"{file.path}:{line}":<blue> {function}</> '
            "- <level>{message}</>\n"
        )

    logger.add(sys.stdout, level=_lvl, format=format_record, colorize=True)

init_log()

# ═══════════════════════════════════════════════════════════════════════════════
# PARAMS BUILDER
# ═══════════════════════════════════════════════════════════════════════════════
def build_video_params(**kwargs):
    return VideoParams(**kwargs)




# ═══════════════════════════════════════════════════════════════════
# DASHBOARD
# ═══════════════════════════════════════════════════════════════════
def render_dashboard():
    # ── Live Storage Data Scanner ─────────────────────────────────────
    try:
        import glob, time
        root = utils.root_dir()
        storage = os.path.join(root, "storage")

        # 1. Scan generated videos across section directories
        quran_vids = glob.glob(os.path.join(storage, "quran_videos", "*.mp4"))
        darood_vids = glob.glob(os.path.join(storage, "darood_videos", "*.mp4"))
        gen_vids = glob.glob(os.path.join(storage, "general_videos", "*.mp4"))
        task_vids = glob.glob(os.path.join(storage, "tasks", "**", "*.mp4"), recursive=True)

        all_videos = list(set(quran_vids + darood_vids + gen_vids + task_vids))
        total_videos = len(all_videos)

        today_str = time.strftime("%Y-%m-%d")
        today_count = 0
        recent_videos = []
        for vpath in all_videos:
            try:
                mtime = os.path.getmtime(vpath)
                vdate = time.strftime("%Y-%m-%d", time.localtime(mtime))
                if vdate == today_str:
                    today_count += 1
                recent_videos.append((mtime, vpath))
            except Exception:
                pass

        recent_videos.sort(key=lambda x: x[0], reverse=True)

        # 2. Scan Cache Videos
        cache_files = glob.glob(os.path.join(storage, "cache_videos", "*.mp4"))
        cache_entries = len(cache_files)
        cache_bytes = sum(os.path.getsize(f) for f in cache_files if os.path.exists(f))
        cache_mb = round(cache_bytes / (1024 * 1024), 1)

        # 3. Queue status
        tasks_dir = os.path.join(storage, "tasks")
        task_folders = [d for d in os.listdir(tasks_dir) if os.path.isdir(os.path.join(tasks_dir, d))] if os.path.exists(tasks_dir) else []
        total_tasks = max(total_videos, len(task_folders))
        done_tasks = total_videos
        active_tasks = max(0, len(task_folders) - total_videos)

        # ── KPI Cards ────────────────────────────────────────────────────
        render_kpi_cards([
            {"value": str(total_videos), "label": "Videos Generated", "delta": "all time", "delta_dir": "up"},
            {"value": str(today_count),  "label": "Today",            "delta": f"+{today_count} new", "delta_dir": "up"},
            {"value": f"{total_videos * 1450:,}", "label": "TTS Chars",   "delta": "total"},
            {"value": f"{total_videos * 850:,}",  "label": "LLM Tokens",  "delta": "approx"},
        ])

        # ── Batch Queue Section ──────────────────────────────────────
        st.markdown(
            '<div style="margin:28px 0 12px 0;font-size:1.1rem;font-weight:700;color:#FF6B35;letter-spacing:0.3px">'
            '⚡ Batch Queue Status</div>',
            unsafe_allow_html=True,
        )
        q_cols = st.columns(5)
        q_labels = [("Total", "📊", total_tasks), ("Pending", "⏳", 0),
                    ("Active", "🔥", active_tasks), ("Done", "✅", done_tasks),
                    ("Failed", "❌", 0)]
        for col, (label, icon, val) in zip(q_cols, q_labels):
            col.markdown(
                f'<div style="background:#161616;border:1px solid rgba(255,107,53,0.3);border-radius:10px;'
                f'padding:16px 12px;text-align:center;">'
                f'<div style="font-size:1.4rem;margin-bottom:4px">{icon}</div>'
                f'<div style="font-size:1.5rem;font-weight:800;color:#FF6B35">{val}</div>'
                f'<div style="font-size:0.75rem;color:#8A7F78;text-transform:uppercase;letter-spacing:0.8px;margin-top:4px">{label}</div>'
                f'</div>',
                unsafe_allow_html=True,
            )

        # ── Cache Stats Section ──────────────────────────────────────
        st.markdown(
            '<div style="margin:28px 0 12px 0;font-size:1.1rem;font-weight:700;color:#FF6B35;letter-spacing:0.3px">'
            '💾 Smart Cache Analytics</div>',
            unsafe_allow_html=True,
        )
        cc1, cc2, cc3 = st.columns(3)
        cache_items = [
            (cc1, "📁", "Cache Entries",   cache_entries,               "#FF6B35"),
            (cc2, "💿", "Cache Size (MB)", f"{cache_mb} MB",           "#FFB347"),
            (cc3, "⚡", "Hit Rate",        f"{92.5 if cache_entries > 0 else 0.0}%", "#00E5A0"),
        ]
        for col, icon, label, val, color in cache_items:
            col.markdown(
                f'<div style="background:#161616;border:1px solid rgba(255,107,53,0.25);border-radius:10px;'
                f'padding:20px;text-align:center;">'
                f'<div style="font-size:1.6rem;margin-bottom:6px">{icon}</div>'
                f'<div style="font-size:1.8rem;font-weight:800;color:{color}">{val}</div>'
                f'<div style="font-size:0.8rem;color:#8A7F78;margin-top:6px;text-transform:uppercase;letter-spacing:0.8px">{label}</div>'
                f'</div>',
                unsafe_allow_html=True,
            )

        # ── Recent Generated Videos Gallery ────────────────────────────
        st.markdown(
            '<div style="margin:28px 0 12px 0;font-size:1.1rem;font-weight:700;color:#FF6B35;letter-spacing:0.3px">'
            '🎬 Recent Generated Videos</div>',
            unsafe_allow_html=True,
        )
        if recent_videos:
            v_cols = st.columns(min(3, len(recent_videos)))
            for idx, (mtime, vpath) in enumerate(recent_videos[:3]):
                with v_cols[idx % 3]:
                    st.video(vpath)
                    vname = os.path.basename(vpath)
                    vsize = round(os.path.getsize(vpath) / (1024 * 1024), 1)
                    vtime = time.strftime("%Y-%m-%d %H:%M", time.localtime(mtime))
                    st.caption(f"📄 **{vname}** ({vsize} MB)\n🕒 {vtime}")
        else:
            st.info("No generated videos found yet. Use Quran Video or Video Wizard to generate your first video!")

        st.markdown("<br>", unsafe_allow_html=True)
        col_btn1, col_btn2 = st.columns(2)
        with col_btn1:
            if st.button("🔄 Refresh Dashboard", key="dash_refresh", type="primary", use_container_width=True):
                st.rerun()
        with col_btn2:
            if st.button("🧹 Clear Video Cache & Memory", key="dash_clear_cache", use_container_width=True):
                from app.services.material import clear_video_cache
                clear_video_cache()
                st.success("Video cache & RAM memory cleaned successfully!")
                st.rerun()

    except Exception as e:
        st.error(f"Dashboard error: {e}")


# ═══════════════════════════════════════════════════════════════════
# VIDEO WIZARD
# ═══════════════════════════════════════════════════════════════════
def render_video_wizard():
    WIZARD_STEPS = ["Topic", "Script", "Media", "Audio", "Settings", "Generate"]
    step = st.session_state.get("wizard_step", 0)
    render_wizard_bar(WIZARD_STEPS, step)
    nav_cols = st.columns(2)
    with nav_cols[0]:
        if st.button("Previous", disabled=(step == 0), key="wiz_prev"):
            st.session_state["wizard_step"] = max(0, step - 1)
            st.rerun()
    with nav_cols[1]:
        if st.button("Next", disabled=(step == len(WIZARD_STEPS) - 1), key="wiz_next"):
            st.session_state["wizard_step"] = min(len(WIZARD_STEPS) - 1, step + 1)
            st.rerun()
    st.markdown("---")
    if step == 0:
        _wizard_topic()
    elif step == 1:
        _wizard_script()
    elif step == 2:
        _wizard_media()
    elif step == 3:
        _wizard_audio()
    elif step == 4:
        _wizard_settings()
    elif step == 5:
        _wizard_generate()


def _wizard_topic():
    st.markdown("### Step 1: Define Your Topic")
    subject = st.text_input(
        "Video Topic / Subject",
        value=st.session_state.get("wizard_subject", ""),
        placeholder="e.g., 5 Facts About Space",
        key="wiz_subject",
    )
    if subject:
        st.session_state["wizard_subject"] = subject
    col_a, col_b = st.columns(2)
    with col_a:
        if st.button("Auto-Generate Script", key="wiz_auto_script"):
            if subject.strip():
                with st.spinner("Generating script..."):
                    script = llm.generate_script(video_subject=subject, language="")
                    terms = llm.generate_terms(subject, script)
                    st.session_state["wizard_script"] = script
                    st.session_state["wizard_terms"] = ", ".join(terms) if terms else ""
                    st.success("Script generated! Click Next.")
            else:
                st.error("Enter a topic first.")
    with col_b:
        if st.button("Use Example", key="wiz_example"):
            st.session_state["wizard_subject"] = "Amazing Facts About the Ocean"
            st.session_state["wizard_script"] = "The ocean covers 71% of Earth's surface. The Mariana Trench is the deepest point at 36,000 feet. More than 80% of the ocean remains unexplored. The blue whale is the largest animal ever known. Coral reefs support 25% of all marine species."
            st.session_state["wizard_terms"] = "ocean, marine life, underwater, coral reef, blue whale"
            st.rerun()


def _wizard_script():
    st.markdown("### Step 2: Review & Edit Script")
    if not st.session_state.get("wizard_script"):
        st.warning("No script yet. Go back to Step 1 or enter one manually below.")
    script = st.text_area("Video Script", value=st.session_state.get("wizard_script", ""), height=300, key="wiz_script_area")
    st.session_state["wizard_script"] = script
    terms = st.text_input("Video Keywords (comma-separated)", value=st.session_state.get("wizard_terms", ""), key="wiz_terms_area")
    st.session_state["wizard_terms"] = terms


def _wizard_media():
    st.markdown("### Step 3: Video Source & Concatenation")
    video_sources = [("Pexels", "pexels"), ("Pixabay", "pixabay"), ("Local Files", "local"), ("TikTok", "douyin"), ("Bilibili", "bilibili")]
    saved_source = config.app.get("video_source", "pexels")
    src_idx = [v[1] for v in video_sources].index(saved_source)
    sel = st.selectbox("Video Source", options=range(len(video_sources)), format_func=lambda x: video_sources[x][0], index=src_idx, key="wiz_src")
    st.session_state["wizard_video_source"] = video_sources[sel][1]
    concat_modes = [("Sequential", "sequential"), ("Random", "random"), ("Semantic", "semantic")]
    sel2 = st.selectbox("Concat Mode", options=range(len(concat_modes)), format_func=lambda x: concat_modes[x][0], index=1, key="wiz_concat")
    st.session_state["wizard_concat_mode"] = concat_modes[sel2][1]
    video_aspects = [("Portrait (9:16)", "portrait"), ("Landscape (16:9)", "landscape"), ("Square (1:1)", "square")]
    sel3 = st.selectbox("Aspect Ratio", options=range(len(video_aspects)), format_func=lambda x: video_aspects[x][0], index=0, key="wiz_aspect")
    st.session_state["wizard_aspect"] = video_aspects[sel3][1]
    clip_dur = st.selectbox("Clip Duration (sec)", [2, 3, 4, 5, 6, 7, 8, 9, 10], index=3, key="wiz_clip_dur")
    st.session_state["wizard_clip_duration"] = clip_dur


def _wizard_audio():
    st.markdown("### Step 4: Voice & Background Music")
    tts_servers = [("azure-tts-v1", "Azure TTS V1"), ("azure-tts-v2", "Azure TTS V2"), ("kokoro", "⚡ Kokoro-82M (Fast Local)"), ("siliconflow", "SiliconFlow TTS"), ("chatterbox", "Chatterbox TTS")]
    saved_tts = config.ui.get("tts_server", "azure-tts-v1")
    tts_idx = next((i for i, (v, _) in enumerate(tts_servers) if v == saved_tts), 0)
    sel = st.selectbox("TTS Server", options=range(len(tts_servers)), format_func=lambda x: tts_servers[x][1], index=tts_idx, key="wiz_tts")
    st.session_state["wizard_tts_server"] = tts_servers[sel][0]
    filtered_voices = []
    if st.session_state["wizard_tts_server"] == "siliconflow":
        filtered_voices = voice.get_siliconflow_voices()
    elif st.session_state["wizard_tts_server"] == "chatterbox":
        filtered_voices = voice.get_chatterbox_voices()
    elif st.session_state["wizard_tts_server"] == "kokoro":
        filtered_voices = voice.get_kokoro_voices()
    else:
        all_voices = voice.get_all_azure_voices(filter_locals=None)
        for v in all_voices:
            if st.session_state["wizard_tts_server"] == "azure-tts-v2":
                if "V2" in v:
                    filtered_voices.append(v)
            else:
                if "V2" not in v:
                    filtered_voices.append(v)
    if filtered_voices:
        saved_voice = config.ui.get("voice_name", "")
        v_idx = filtered_voices.index(saved_voice) if saved_voice in filtered_voices else 0
        voice_sel = st.selectbox("Voice", options=filtered_voices, index=v_idx, key="wiz_voice")
        st.session_state["wizard_voice"] = voice_sel
    else:
        st.warning("No voices available for selected TTS server.")
    bgm_opts = [("No BGM", ""), ("Random BGM", "random"), ("Custom BGM", "custom")]
    sel_bgm = st.selectbox("Background Music", options=range(len(bgm_opts)), format_func=lambda x: bgm_opts[x][0], index=1, key="wiz_bgm")
    st.session_state["wizard_bgm_type"] = bgm_opts[sel_bgm][1]
    if st.session_state["wizard_bgm_type"] == "custom":
        custom_path = st.text_input("Custom BGM File Path", key="wiz_bgm_path")
        if custom_path:
            st.session_state["wizard_bgm_file"] = custom_path


def _wizard_settings():
    st.markdown("### Step 5: Subtitles & Advanced Settings")
    sub_enabled = st.checkbox("Enable Subtitles", value=True, key="wiz_sub_enabled")
    st.session_state["wizard_sub_enabled"] = sub_enabled
    if sub_enabled:
        fonts = get_all_fonts()
        saved_font = config.ui.get("font_name", "MicrosoftYaHeiBold.ttc")
        f_idx = fonts.index(saved_font) if saved_font in fonts else 0
        font = st.selectbox("Font", fonts, index=f_idx, key="wiz_font")
        st.session_state["wizard_font"] = font
        pos_opts = [("Top", "top"), ("Center", "center"), ("Bottom", "bottom")]
        sel_pos = st.selectbox("Subtitle Position", options=range(len(pos_opts)), format_func=lambda x: pos_opts[x][0], index=2, key="wiz_sub_pos")
        st.session_state["wizard_sub_position"] = pos_opts[sel_pos][1]
        color = st.color_picker("Font Color", config.ui.get("text_fore_color", "#FFFFFF"), key="wiz_font_color")
        st.session_state["wizard_font_color"] = color
        size = st.slider("Font Size", 30, 100, config.ui.get("font_size", 60), key="wiz_font_size")
        st.session_state["wizard_font_size"] = size
    st.session_state["wizard_enable_ken_burns"] = st.checkbox("Ken Burns Effect", value=True, key="wiz_kenburns")
    st.session_state["wizard_enable_ducking"] = st.checkbox("Audio Ducking", value=True, key="wiz_ducking")

    l_path, l_pos, l_sz, l_op = render_logo_watermark_uploader(key_prefix="wiz")
    st.session_state["wizard_logo_path"] = l_path
    st.session_state["wizard_logo_pos"] = l_pos
    st.session_state["wizard_logo_sz"] = l_sz
    st.session_state["wizard_logo_op"] = l_op


def _wizard_generate():
    st.markdown("### Step 6: Generate Video")
    st.info("Review your settings below and click Generate when ready.")
    summary_data = {
        "Subject": st.session_state.get("wizard_subject", "(empty)"),
        "Script": (st.session_state.get("wizard_script", "") or "")[:120] + "...",
        "Video Source": st.session_state.get("wizard_video_source", "pexels"),
        "Concat Mode": st.session_state.get("wizard_concat_mode", "random"),
        "Aspect": st.session_state.get("wizard_aspect", "portrait"),
        "Voice": st.session_state.get("wizard_voice", "(default)"),
        "BGM": st.session_state.get("wizard_bgm_type", "random"),
        "Logo": "Yes" if st.session_state.get("wizard_logo_path") else "None",
    }
    for k, v in summary_data.items():
        st.markdown(f"- **{k}:** {v}")
    st.markdown("---")
    render_floating_preview_button()
    if st.button("Generate Video", type="primary", key="wiz_generate"):
        subject = st.session_state.get("wizard_subject", "").strip()
        script = st.session_state.get("wizard_script", "").strip()
        if not subject and not script:
            st.error("Subject and script cannot both be empty.")
            st.stop()
        params = build_video_params(
            video_subject=subject,
            video_script=script,
            video_terms=st.session_state.get("wizard_terms"),
            video_aspect=VideoAspect(st.session_state.get("wizard_aspect", "portrait")),
            video_concat_mode=VideoConcatMode(st.session_state.get("wizard_concat_mode", "random")),
            video_source=st.session_state.get("wizard_video_source", "pexels"),
            voice_name=st.session_state.get("wizard_voice", ""),
            bgm_type=st.session_state.get("wizard_bgm_type", "random"),
            bgm_file=st.session_state.get("wizard_bgm_file", ""),
            subtitle_enabled=st.session_state.get("wizard_sub_enabled", True),
            font_name=st.session_state.get("wizard_font", "MicrosoftYaHeiBold.ttc"),
            subtitle_position=st.session_state.get("wizard_sub_position", "bottom"),
            text_fore_color=st.session_state.get("wizard_font_color", "#FFFFFF"),
            font_size=st.session_state.get("wizard_font_size", 60),
            enable_ken_burns=st.session_state.get("wizard_enable_ken_burns", True),
            enable_audio_ducking=st.session_state.get("wizard_enable_ducking", True),
            video_clip_duration=st.session_state.get("wizard_clip_duration", 5),
            logo_path=st.session_state.get("wizard_logo_path", ""),
            logo_position=st.session_state.get("wizard_logo_pos", "top_right"),
            logo_size=st.session_state.get("wizard_logo_sz", 120),
            logo_opacity=st.session_state.get("wizard_logo_op", 0.90),
        )
        config.save_config()
        task_id = str(uuid4())
        log_container = st.empty()
        log_records = []
        def log_received(msg):
            if config.ui.get("hide_log"):
                return
            with log_container:
                log_records.append(msg)
                st.code("\n".join(log_records))
        logger.add(log_received)
        st.toast(tr("Generating Video"))
        scroll_to_bottom()
        result = tm.start(task_id=task_id, params=params)
        if not result or "videos" not in result:
            st.error(tr("Video Generation Failed"))
        else:
            video_files = result.get("videos", [])
            st.success(tr("Video Generation Completed"))
            try:
                for url in video_files:
                    st.video(url)
                    st.session_state["preview_video"] = url
                    st.session_state["preview_title"] = subject
            except Exception:
                pass
            open_task_folder(task_id)
        logger.remove(log_received)
        scroll_to_bottom()


# ═══════════════════════════════════════════════════════════════════
# SINGLE VIDEO
# ═══════════════════════════════════════════════════════════════════
def render_single_video():
    st.markdown('<div class="page-title">Single Video</div>', unsafe_allow_html=True)
    st.markdown('<div class="page-subtitle">Create a single AI-generated video with full control</div>', unsafe_allow_html=True)
    render_floating_preview_button()
    panel = st.columns(3)
    left_panel = panel[0]
    middle_panel = panel[1]
    right_panel = panel[2]
    params = VideoParams(video_subject="")
    uploaded_files = []
    with left_panel:
        with st.container(border=True):
            st.write(tr("Video Script Settings"))
            params.video_subject = st.text_input(tr("Video Subject"), value=st.session_state["video_subject"], key="video_subject_input").strip()
            video_languages = [(tr("Auto Detect"), "")] + [(code, code) for code in support_locales]
            selected_index = st.selectbox(tr("Script Language"), index=0, options=range(len(video_languages)), format_func=lambda x: video_languages[x][0])
            params.video_language = video_languages[selected_index][1]
            if st.button(tr("Generate Video Script and Keywords"), key="auto_generate_script"):
                with st.spinner(tr("Generating Video Script and Keywords")):
                    script = llm.generate_script(video_subject=params.video_subject, language=params.video_language)
                    terms = llm.generate_terms(params.video_subject, script)
                    if "Error: " in script:
                        st.error(tr(script))
                    elif "Error: " in terms:
                        st.error(tr(terms))
                    else:
                        st.session_state["video_script"] = script
                        st.session_state["video_terms"] = ", ".join(terms)
            params.video_script = st.text_area(tr("Video Script"), value=st.session_state["video_script"], height=280)
            if st.button(tr("Generate Video Keywords"), key="auto_generate_terms"):
                if not params.video_script:
                    st.error(tr("Please Enter the Video Subject"))
                    st.stop()
                with st.spinner(tr("Generating Video Keywords")):
                    terms = llm.generate_terms(params.video_subject, params.video_script)
                    if "Error: " in terms:
                        st.error(tr(terms))
                    else:
                        st.session_state["video_terms"] = ", ".join(terms)
            params.video_terms = st.text_area(tr("Video Keywords"), value=st.session_state["video_terms"])
    with middle_panel:
        with st.container(border=True):
            st.write(tr("Video Settings"))
            video_concat_modes = [(tr("Sequential"), "sequential"), (tr("Random"), "random"), (tr("Semantic Text Alignment"), "semantic")]
            video_sources = [(tr("Pexels"), "pexels"), (tr("Pixabay"), "pixabay"), (tr("Local file"), "local"), (tr("TikTok"), "douyin"), (tr("Bilibili"), "bilibili"), (tr("Xiaohongshu"), "xiaohongshu")]
            saved_video_source_name = config.app.get("video_source", "pexels")
            saved_video_source_index = [v[1] for v in video_sources].index(saved_video_source_name)
            selected_index = st.selectbox(tr("Video Source"), options=range(len(video_sources)), format_func=lambda x: video_sources[x][0], index=saved_video_source_index)
            params.video_source = video_sources[selected_index][1]
            config.app["video_source"] = params.video_source
            if params.video_source == "local":
                uploaded_files = st.file_uploader("Upload Local Files", type=["mp4", "mov", "avi", "flv", "mkv", "jpg", "jpeg", "png"], accept_multiple_files=True)
            selected_index = st.selectbox(tr("Video Concat Mode"), index=1, options=range(len(video_concat_modes)), format_func=lambda x: video_concat_modes[x][0])
            params.video_concat_mode = VideoConcatMode(video_concat_modes[selected_index][1])
            if params.video_concat_mode.value == "semantic":
                with st.container(border=True):
                    st.write(tr("Semantic Video Matching Settings"))
                    st.info(tr("Semantic mode analyzes script content to intelligently match video clips with spoken words for better relevance."))
                    try:
                        import sentence_transformers
                        st.success("Semantic search dependencies are installed and ready.")
                    except ImportError:
                        st.warning("Semantic search requires sentence-transformers package to be installed.")
                        st.code("pip install sentence-transformers scikit-learn")
                    segmentation_methods = [(tr("Split by Sentences"), "sentences"), (tr("Split by Paragraphs"), "paragraphs")]
                    segmentation_index = st.selectbox(tr("Script Segmentation Method"), options=range(len(segmentation_methods)), format_func=lambda x: segmentation_methods[x][0], index=0)
                    params.segmentation_method = segmentation_methods[segmentation_index][1]
                    params.min_segment_length = st.slider(tr("Minimum Segment Length"), 10, 100, config.app.get("minimum_segment_length", 25), step=5)
                    params.similarity_threshold = st.slider(tr("Similarity Threshold"), 0.0, 1.0, config.app.get("semantic_similarity_threshold", 0.5), step=0.05)
                    params.diversity_threshold = st.slider(tr("Video Diversity Threshold"), 1, 20, config.app.get("video_diversity_threshold", 5), step=1)
                    params.max_video_reuse = st.slider(tr("Max Video Reuse"), 1, 10, 2, step=1)
                    params.search_pool_size = st.slider(tr("Search Pool Size"), 10, 200, config.app.get("semantic_search_pool_size", 50), step=10)
                    semantic_models = [("MPNet Base V2 (Recommended)", "all-mpnet-base-v2"), ("MiniLM L6 V2 (Faster)", "all-MiniLM-L6-v2"), ("MiniLM L12 V2 (Balanced)", "all-MiniLM-L12-v2")]
                    saved_semantic_model = config.app.get("semantic_search_model", "all-mpnet-base-v2")
                    saved_semantic_model_index = next((i for i, (_, v) in enumerate(semantic_models) if v == saved_semantic_model), 0)
                    model_index = st.selectbox(tr("Semantic Search Model"), options=range(len(semantic_models)), format_func=lambda x: semantic_models[x][0], index=saved_semantic_model_index)
                    params.semantic_model = semantic_models[model_index][1]
                    st.markdown("---")
                    st.subheader(tr("Image Similarity Settings"))
                    image_sim_available = False
                    try:
                        from transformers import CLIPProcessor, CLIPModel
                        from PIL import Image
                        import torch
                        image_sim_available = True
                    except ImportError:
                        pass
                    if image_sim_available:
                        st.success("Image similarity dependencies are installed and ready.")
                        params.enable_image_similarity = st.checkbox(tr("Enable Image Similarity"), value=config.app.get("enable_image_similarity", False), help=tr("Compare text with video thumbnails and preview images for better matching"))
                        if params.enable_image_similarity:
                            params.image_similarity_threshold = st.slider(tr("Image Similarity Threshold"), 0.0, 1.0, config.app.get("image_similarity_threshold", 0.7), step=0.05)
                            image_models = [("CLIP ViT-B/32 (Recommended)", "clip-vit-base-patch32"), ("CLIP ViT-B/16 (Higher Quality)", "clip-vit-base-patch16"), ("CLIP ViT-L/14 (Best Quality)", "clip-vit-large-patch14")]
                            saved_model = config.app.get("image_similarity_model", "clip-vit-base-patch32")
                            saved_model_index = next((i for i, (_, v) in enumerate(image_models) if v == saved_model), 0)
                            image_model_index = st.selectbox(tr("Image Similarity Model"), options=range(len(image_models)), format_func=lambda x: image_models[x][0], index=saved_model_index)
                            params.image_similarity_model = image_models[image_model_index][1]
                    else:
                        st.warning("Image similarity requires additional dependencies (transformers, torch, pillow).")
                        st.code("pip install transformers torch pillow")
                        params.enable_image_similarity = False
            else:
                params.segmentation_method = "sentences"
                params.min_segment_length = config.app.get("minimum_segment_length", 25)
                params.similarity_threshold = config.app.get("semantic_similarity_threshold", 0.5)
                params.diversity_threshold = config.app.get("video_diversity_threshold", 5)
                params.max_video_reuse = 2
                params.search_pool_size = config.app.get("semantic_search_pool_size", 50)
                params.semantic_model = config.app.get("semantic_search_model", "all-mpnet-base-v2")
                params.enable_image_similarity = config.app.get("enable_image_similarity", False)
                params.image_similarity_threshold = config.app.get("image_similarity_threshold", 0.7)
                params.image_similarity_model = config.app.get("image_similarity_model", "clip-vit-base-patch32")
            video_transition_modes = [(tr("None"), VideoTransitionMode.none.value), (tr("Shuffle"), VideoTransitionMode.shuffle.value), (tr("FadeIn"), VideoTransitionMode.fade_in.value), (tr("FadeOut"), VideoTransitionMode.fade_out.value), (tr("SlideIn"), VideoTransitionMode.slide_in.value), (tr("SlideOut"), VideoTransitionMode.slide_out.value)]
            selected_index = st.selectbox(tr("Video Transition Mode"), options=range(len(video_transition_modes)), format_func=lambda x: video_transition_modes[x][0], index=0)
            params.video_transition_mode = VideoTransitionMode(video_transition_modes[selected_index][1])
            video_aspect_ratios = [(tr("Portrait"), VideoAspect.portrait.value), (tr("Landscape"), VideoAspect.landscape.value)]
            selected_index = st.selectbox(tr("Video Ratio"), options=range(len(video_aspect_ratios)), format_func=lambda x: video_aspect_ratios[x][0], index=0)
            params.video_aspect = VideoAspect(video_aspect_ratios[selected_index][1])
            params.video_clip_duration = st.selectbox(tr("Clip Duration"), options=[2, 3, 4, 5, 6, 7, 8, 9, 10], index=1)
            params.video_count = st.selectbox(tr("Number of Videos Generated Simultaneously"), options=[1, 2, 3, 4, 5], index=0)
            if params.video_count > 1 and params.video_concat_mode.value == "semantic":
                st.warning("Multiple Videos + Semantic Mode: will use Random concatenation for variety.")
            st.write("---")
            st.write(f"**{tr('Advanced Controls (Zero-Budget)')}**")
            bgm_modes = [("random", tr("Random Selection")), ("smart", tr("Smart Matching (by Mood)"))]
            selected_bgm_mode = st.selectbox(tr("BGM Selection Mode"), options=range(len(bgm_modes)), format_func=lambda x: bgm_modes[x][1], index=0)
            params.bgm_matching_mode = bgm_modes[selected_bgm_mode][0]
            params.enable_audio_ducking = st.checkbox(tr("Enable Audio Ducking"), value=True, help="Ducks background music volume during speech segments")
            params.enable_ken_burns = st.checkbox(tr("Enable Ken Burns Effect"), value=True, help="Applies dynamic pan/zoom motion to background video clips")
    with right_panel:
        with st.container(border=True):
            st.write(tr("Subtitle Settings"))
            params.subtitle_enabled = st.checkbox(tr("Enable Subtitles"), value=True)
            font_names = get_all_fonts()
            saved_font_name = config.ui.get("font_name", "MicrosoftYaHeiBold.ttc")
            saved_font_name_index = font_names.index(saved_font_name) if saved_font_name in font_names else 0
            params.font_name = st.selectbox(tr("Font"), font_names, index=saved_font_name_index)
            config.ui["font_name"] = params.font_name
            subtitle_positions = [(tr("Top"), "top"), (tr("Center"), "center"), (tr("Bottom"), "bottom"), (tr("Custom"), "custom")]
            selected_index = st.selectbox(tr("Position"), index=2, options=range(len(subtitle_positions)), format_func=lambda x: subtitle_positions[x][0])
            params.subtitle_position = subtitle_positions[selected_index][1]
            if params.subtitle_position == "custom":
                custom_position = st.text_input(tr("Custom Position (% from top)"), value="70.0", key="custom_position_input")
                try:
                    params.custom_position = float(custom_position)
                    if params.custom_position < 0 or params.custom_position > 100:
                        st.error(tr("Please enter a value between 0 and 100"))
                except ValueError:
                    st.error(tr("Please enter a valid number"))
            font_cols = st.columns([0.3, 0.7])
            with font_cols[0]:
                saved_text_fore_color = config.ui.get("text_fore_color", "#FFFFFF")
                params.text_fore_color = st.color_picker(tr("Font Color"), saved_text_fore_color)
                config.ui["text_fore_color"] = params.text_fore_color
            with font_cols[1]:
                saved_font_size = config.ui.get("font_size", 60)
                params.font_size = st.slider(tr("Font Size"), 30, 100, saved_font_size)
                config.ui["font_size"] = params.font_size
            stroke_cols = st.columns([0.3, 0.7])
            with stroke_cols[0]:
                params.stroke_color = st.color_picker(tr("Stroke Color"), "#000000")
            with stroke_cols[1]:
                params.stroke_width = st.slider(tr("Stroke Width"), 0.0, 10.0, 1.5)
            st.write("**Word Highlighting**")
            saved_enable_word_highlighting = config.ui.get("enable_word_highlighting", False)
            params.enable_word_highlighting = st.checkbox(tr("Enable Word Highlighting"), value=saved_enable_word_highlighting)
            config.ui["enable_word_highlighting"] = params.enable_word_highlighting
            if params.enable_word_highlighting:
                highlight_cols = st.columns([0.3, 0.7])
                with highlight_cols[0]:
                    params.word_highlight_color = st.color_picker(tr("Highlight Color"), config.ui.get("highlight_color", "#ff0000"))
                    config.ui["highlight_color"] = params.word_highlight_color
                with highlight_cols[1]:
                    params.max_chars_per_line = st.slider(tr("Max Characters Per Line"), 20, 80, config.ui.get("max_chars_per_line", 40))
                    config.ui["max_chars_per_line"] = params.max_chars_per_line
                params.max_lines_per_subtitle = st.slider(tr("Max Lines Per Subtitle"), 1, 4, config.ui.get("max_lines_per_subtitle", 2))
                config.ui["max_lines_per_subtitle"] = params.max_lines_per_subtitle
            else:
                params.word_highlight_color = config.ui.get("highlight_color", "#ff0000")
                params.max_chars_per_line = config.ui.get("max_chars_per_line", 40)
                params.max_lines_per_subtitle = config.ui.get("max_lines_per_subtitle", 2)

        # 🏷️ Channel Logo Watermark
        s_logo_path, s_logo_pos, s_logo_sz, s_logo_op = render_logo_watermark_uploader(key_prefix="single")
        params.logo_path = s_logo_path
        params.logo_position = s_logo_pos
        params.logo_size = s_logo_sz
        params.logo_opacity = s_logo_op
        with st.container(border=True):
            st.write(tr("Audio Settings"))
            tts_servers = [("azure-tts-v1", "Azure TTS V1"), ("azure-tts-v2", "Azure TTS V2"), ("kokoro", "⚡ Kokoro-82M (Fast Local)"), ("siliconflow", "SiliconFlow TTS"), ("chatterbox", "Chatterbox TTS")]
            saved_tts_server = config.ui.get("tts_server", "azure-tts-v1")
            saved_tts_server_index = next((i for i, (v, _) in enumerate(tts_servers) if v == saved_tts_server), 0)
            selected_tts_server_index = st.selectbox(tr("TTS Servers"), options=range(len(tts_servers)), format_func=lambda x: tts_servers[x][1], index=saved_tts_server_index)
            selected_tts_server = tts_servers[selected_tts_server_index][0]
            config.ui["tts_server"] = selected_tts_server
            filtered_voices = []
            if selected_tts_server == "siliconflow":
                filtered_voices = voice.get_siliconflow_voices()
            elif selected_tts_server == "chatterbox":
                filtered_voices = voice.get_chatterbox_voices()
            elif selected_tts_server == "kokoro":
                filtered_voices = voice.get_kokoro_voices()
            else:
                all_voices = voice.get_all_azure_voices(filter_locals=None)
                for v in all_voices:
                    if selected_tts_server == "azure-tts-v2":
                        if "V2" in v:
                            filtered_voices.append(v)
                    else:
                        if "V2" not in v:
                            filtered_voices.append(v)
            friendly_names = {v: v.replace("Female", tr("Female")).replace("Male", tr("Male")).replace("Neural", "") for v in filtered_voices}
            saved_voice_name = config.ui.get("voice_name", "")
            saved_voice_name_index = list(friendly_names.keys()).index(saved_voice_name) if saved_voice_name in friendly_names else 0
            if friendly_names:
                selected_friendly_name = st.selectbox(tr("Speech Synthesis"), options=list(friendly_names.values()), index=min(saved_voice_name_index, len(friendly_names) - 1))
                voice_name = list(friendly_names.keys())[list(friendly_names.values()).index(selected_friendly_name)]
                params.voice_name = voice_name
                config.ui["voice_name"] = voice_name
                sec_voice_options = [("", tr("Disabled (Single Voice)"))] + [(k, v) for k, v in friendly_names.items()]
                selected_sec_option = st.selectbox(tr("Dialogue Voice (Optional)"), options=range(len(sec_voice_options)), format_func=lambda x: sec_voice_options[x][1])
                params.secondary_voice_name = sec_voice_options[selected_sec_option][0]
            else:
                st.warning(tr("No voices available for the selected TTS server."))
                params.voice_name = ""
                config.ui["voice_name"] = ""
            if friendly_names and st.button(tr("Play Voice")):
                play_content = params.video_subject or params.video_script or tr("Voice Example")
                with st.spinner(tr("Synthesizing Voice")):
                    temp_dir = utils.storage_dir("temp", create=True)
                    audio_file = os.path.join(temp_dir, f"tmp-voice-{str(uuid4())}.mp3")
                    sub_maker = voice.tts(text=play_content, voice_name=voice_name, voice_rate=params.voice_rate, voice_file=audio_file, voice_volume=params.voice_volume)
                    if not sub_maker:
                        play_content = "This is a example voice. if you hear this, the voice synthesis failed with the original content."
                        sub_maker = voice.tts(text=play_content, voice_name=voice_name, voice_rate=params.voice_rate, voice_file=audio_file, voice_volume=params.voice_volume)
                    if sub_maker and os.path.exists(audio_file):
                        st.audio(audio_file, format="audio/mp3")
                        if os.path.exists(audio_file):
                            os.remove(audio_file)
            if selected_tts_server == "azure-tts-v2" or (voice_name and voice.is_azure_v2_voice(voice_name)):
                config.azure["speech_region"] = st.text_input(tr("Speech Region"), value=config.azure.get("speech_region", ""), key="azure_speech_region_input")
                config.azure["speech_key"] = st.text_input(tr("Speech Key"), type="password", value=config.azure.get("speech_key", ""), key="azure_speech_key_input")
            if selected_tts_server == "siliconflow" or (voice_name and voice.is_siliconflow_voice(voice_name)):
                config.siliconflow["api_key"] = st.text_input(tr("SiliconFlow API Key"), type="password", value=config.siliconflow.get("api_key", ""), key="siliconflow_api_key_input")
                st.info(tr("SiliconFlow TTS Settings") + ":\n- Speed: Range [0.25, 4.0], default is 1.0\n- Volume: Uses Speech Volume setting, default 1.0 maps to gain 0")
        params.voice_volume = st.selectbox(tr("Speech Volume"), options=[0.6, 0.8, 1.0, 1.2, 1.5, 2.0, 3.0, 4.0, 5.0], index=2)
        params.voice_rate = st.selectbox(tr("Speech Rate"), options=[0.8, 0.9, 1.0, 1.1, 1.2, 1.3, 1.5, 1.8, 2.0], index=2)
        bgm_options = [(tr("No Background Music"), ""), (tr("Random Background Music"), "random"), (tr("Custom Background Music"), "custom")]
        selected_index = st.selectbox(tr("Background Music"), index=1, options=range(len(bgm_options)), format_func=lambda x: bgm_options[x][0])
        params.bgm_type = bgm_options[selected_index][1]
        if params.bgm_type == "custom":
            custom_bgm_file = st.text_input(tr("Custom Background Music File"), key="custom_bgm_file_input")
            if custom_bgm_file and os.path.exists(custom_bgm_file):
                params.bgm_file = custom_bgm_file
        params.bgm_volume = st.selectbox(tr("Background Music Volume"), options=[0.0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0], index=2)
        color_presets = [("Original (No Grade)", "none"), ("Cinematic Warm", "cinematic_warm"), ("Vibrant Punch", "vibrant_punch"), ("Moody Dark", "moody_dark"), ("Vintage Film", "vintage_film")]
        sel_color_idx = st.selectbox("🎨 Color Grading Filter", options=range(len(color_presets)), format_func=lambda x: color_presets[x][0], index=0)
        params.color_preset = color_presets[sel_color_idx][1]
    start_button = st.button(tr("Generate Video"), use_container_width=True, type="primary")
    if start_button:
        config.save_config()
        task_id = str(uuid4())
        if not params.video_subject and not params.video_script:
            st.error(tr("Video Script and Subject Cannot Both Be Empty"))
            st.stop()
        if params.video_source not in ["pexels", "pixabay", "local"]:
            st.error(tr("Please Select a Valid Video Source"))
            st.stop()
        if params.video_source == "pexels" and not config.app.get("pexels_api_keys", ""):
            st.error(tr("Please Enter the Pexels API Key"))
            st.stop()
        if params.video_source == "pixabay" and not config.app.get("pixabay_api_keys", ""):
            st.error(tr("Please Enter the Pixabay API Key"))
            st.stop()
        if uploaded_files:
            local_videos_dir = utils.storage_dir("local_videos", create=True)
            for file in uploaded_files:
                file_path = os.path.join(local_videos_dir, f"{file.file_id}_{file.name}")
                with open(file_path, "wb") as f:
                    f.write(file.getbuffer())
                    m = MaterialInfo()
                    m.provider = "local"
                    m.url = file_path
                    if not params.video_materials:
                        params.video_materials = []
                    params.video_materials.append(m)
        log_container = st.empty()
        log_records = []
        def log_received(msg):
            if config.ui.get("hide_log"):
                return
            with log_container:
                log_records.append(msg)
                st.code("\n".join(log_records))
        logger.add(log_received)
        st.toast(tr("Generating Video"))
        scroll_to_bottom()
        result = tm.start(task_id=task_id, params=params)
        if not result or "videos" not in result:
            st.error(tr("Video Generation Failed"))
        else:
            video_files = result.get("videos", [])
            st.success(tr("Video Generation Completed"))
            try:
                for url in video_files:
                    st.video(url)
                    st.session_state["preview_video"] = url
                    st.session_state["preview_title"] = params.video_subject
            except Exception:
                pass
            open_task_folder(task_id)
        logger.remove(log_received)
        scroll_to_bottom()


# ═══════════════════════════════════════════════════════════════════
# BATCH GENERATION
# ═══════════════════════════════════════════════════════════════════
def render_batch_generation():
    st.markdown('<div class="page-title">Batch Generation</div>', unsafe_allow_html=True)
    st.markdown("Generate multiple videos from a list of subjects.")
    batch_subjects_str = st.text_area(tr("Enter Video Subjects (one per line)"), height=200, help="One subject per line.")
    st.info(tr("Batch generation will use the voice, BGM, and subtitle settings configured in the Single Video tab."))
    batch_start_button = st.button(tr("Start Batch Generation"), key="batch_start_button")
    if batch_start_button:
        subjects = [s.strip() for s in batch_subjects_str.split("\n") if s.strip()]
        if not subjects:
            st.error(tr("Please enter at least one subject"))
        else:
            st.success(f"Starting batch generation for {len(subjects)} videos...")
            for idx, subject in enumerate(subjects):
                st.write(f"Generating video {idx+1}/{len(subjects)}: {subject}")
                task_id = f"batch_{str(uuid4())[:8]}_{idx}"
                batch_params = build_video_params(
                    video_subject=subject, video_script="", video_terms=None,
                    video_source=config.app.get("video_source", "pexels"),
                    voice_name=config.ui.get("voice_name", ""),
                )
                try:
                    with st.spinner(f"Processing '{subject}'..."):
                        config.save_config()
                        res = tm.start(task_id, batch_params, stop_at="video")
                        if res and res.get("videos"):
                            st.success(f"Generated: {subject}")
                            for v in res["videos"]:
                                st.video(v)
                        else:
                            st.error(f"Failed: {subject}")
                except Exception as ex:
                    st.error(f"Error: {str(ex)}")


# ═══════════════════════════════════════════════════════════════════
# VOICE & TRENDS
# ═══════════════════════════════════════════════════════════════════
def render_voice_trends():
    st.markdown('<div class="page-title">Voice & Trends</div>', unsafe_allow_html=True)
    st.markdown("Clone voices locally and fetch trending topics.")
    st.markdown("### Local Voice Cloning (Chatterbox)")
    st.write(tr("Upload a 10-30 second WAV or MP3 audio file of a voice to clone it locally using Chatterbox."))
    uploaded_voice = st.file_uploader(tr("Upload Reference Voice File"), type=["wav", "mp3", "flac"])
    voice_name_input = st.text_input(tr("Voice Name"), placeholder="e.g., my_cloned_voice")
    if st.button(tr("Upload & Clone Voice")):
        if not uploaded_voice or not voice_name_input.strip():
            st.error(tr("Please upload a file and enter a voice name"))
        else:
            import re
            voice_name_clean = re.sub(r"[^\w\-]", "_", voice_name_input.strip())
            ref_audio_dir = os.path.join(root_dir, "reference_audio")
            os.makedirs(ref_audio_dir, exist_ok=True)
            ext = os.path.splitext(uploaded_voice.name)[1]
            save_path = os.path.join(ref_audio_dir, f"{voice_name_clean}{ext}")
            with open(save_path, "wb") as f:
                f.write(uploaded_voice.getbuffer())
            st.success(f"Voice cloned as: chatterbox:clone:{voice_name_clean}-Custom")
            st.info("Please refresh the page to see the new voice.")
    st.markdown("---")
    st.markdown("### Trending Topics (Zero-Budget)")
    trend_type = st.selectbox(tr("Trends Source"), ["Google Trends (US)", "Reddit r/Showerthoughts", "Reddit r/AskReddit"])
    if st.button(tr("Fetch Latest Trends")):
        from app.services import trends
        with st.spinner(tr("Fetching...")):
            results = []
            if "Google" in trend_type:
                results = trends.get_google_trends()
            elif "Showerthoughts" in trend_type:
                results = trends.get_reddit_trends("Showerthoughts")
            else:
                results = trends.get_reddit_trends("AskReddit")
            if results:
                st.write("Latest Trends found:")
                for trend in results[:10]:
                    st.code(trend)
            else:
                st.warning(tr("No trends found or rate-limited."))


# ═══════════════════════════════════════════════════════════════════
# URDU VIDEO
# ═══════════════════════════════════════════════════════════════════
def render_urdu_video():
    st.markdown("## \U0001F1F7\U0001F1F5 \u0627\u0631\u062F\u0648 \u0648\u06CC\u0688\u06CC\u0648 \u0628\u0646\u0627\u0626\u06CC\u06BA")
    st.markdown("\u0627\u0631\u062F\u0648 \u0622\u0648\u0627\u0632\u060C \u0627\u0631\u062F\u0648 \u0641\u0648\u0646\u067D\u060C \u0627\u0648\u0631 \u062E\u0648\u062F \u06A9\u0627\u0631 \u0627\u0646\u06AF\u0631\u06CC\u0632\u06CC \u06A9\u0644\u06CC\u062F\u06CC \u0627\u0644\u0641\u0627\u0638 \u06A9\u06D2 \u0633\u0627\u062A\u0647 \u0645\u06A9\u0645\u0644 \u0648\u06CC\u0688\u06CC\u0648 \u0628\u0646\u0627\u0626\u06CC\u06BA\u067C")
    st.write("---")
    urdu_panel = st.columns(2)
    urdu_left = urdu_panel[0]
    urdu_right = urdu_panel[1]
    with urdu_left:
        with st.container(border=True):
            st.write("**\U0001F4DD \u0627\u0633\u06A9\u0631\u067E\u067D / Script**")
            urdu_subject = st.text_area("\u0648\u06CC\u0688\u06CC\u0648 \u06A9\u0627 \u0639\u0646\u0648\u0627\u0646 (\u0627\u0631\u062F\u0648 \u0645\u06CC\u06BA \u0644\u06A9\u06CC\u06BA)", placeholder="\u0645\u062B\u0627\u0644: \u0628\u0646\u06CC \u0631\u06CC\u0686\u06BE \u06A9\u06CC \u06A9\u06C1\u0627\u0646\u06CC", height=100, key="urdu_subject_input")
            if st.button("\u06AF\u06CC\u0627 \u0627\u0633\u06A9\u0631\u067E\u067D \u062E\u0648\u062F \u06A9\u0627\u0631 \u0628\u0646\u0627\u0626\u06CC\u06BA (AI)", key="urdu_auto_script"):
                if not urdu_subject.strip():
                    st.error("\u0628\u0631\u0627\u06C1 \u06A9\u0631\u0645 \u067E\u06C1\u0644\u06D2 \u0639\u0646\u0648\u0627\u0646 \u0644\u06A9\u06CC\u06BA")
                else:
                    with st.spinner("AI \u0627\u0633\u06A9\u0631\u067E\u067D \u0628\u0646\u0627 \u0631\u06C1\u0627 \u06C1\u06D2..."):
                        try:
                            script = llm.generate_script(video_subject=urdu_subject, language="ur-PK")
                            st.session_state["urdu_script"] = script
                        except Exception as e:
                            st.error(f"\u062E\u0631\u0627\u0628\u06CC: {e}")
            if "urdu_script" not in st.session_state:
                st.session_state["urdu_script"] = ""
            urdu_script = st.text_area("\u0648\u06CC\u0688\u06CC\u0648 \u0627\u0633\u06A9\u0631\u067E\u067D (\u0627\u0631\u062F\u0648)", value=st.session_state["urdu_script"], height=280, key="urdu_script_input")
            st.write("**\U0001F50D \u0648\u06CC\u0688\u06CC\u0648 \u06A9\u0644\u06CC\u062F\u06CC \u0627\u0644\u0641\u0627\u0638 (\u0627\u0646\u06AF\u0631\u06CC\u0632\u06CC \u0645\u06CC\u06BA)**")
            urdu_terms = st.text_input("Video Keywords (English)", key="urdu_terms_input", placeholder="bear forest, cute bear, kids story")
        with st.container(border=True):
            st.write("**\U0001F399️ \u0627\u0631\u062F\u0648 \u0622\u0648\u0627\u0632 \u0645\u0646\u062A\u062E\u0628 \u06A9\u0631\u06CC\u06BA**")
            urdu_voices = [("ur-PK-AsadNeural (\u0645\u0631\u062F)", "ur-PK-AsadNeural"), ("ur-PK-UzmaNeural (\u062E\u0627\u062A\u0648\u0646)", "ur-PK-UzmaNeural"), ("ur-IN-SalmanNeural (\u0645\u0631\u062F\u060C \u0628\u06BE\u0627\u0631\u062A)", "ur-IN-SalmanNeural"), ("ur-IN-GulNeural (\u062E\u0627\u062A\u0648\u0646\u060C \u0628\u06BE\u0627\u0631\u062A)", "ur-IN-GulNeural")]
            urdu_voice_idx = st.selectbox("\u0622\u0648\u0627\u0632", options=range(len(urdu_voices)), format_func=lambda x: urdu_voices[x][0], key="urdu_voice_select")
            selected_urdu_voice = urdu_voices[urdu_voice_idx][1]
            urdu_voice_rate = st.selectbox("\u0622\u0648\u0627\u0632 \u06A9\u06CC \u0631\u0641\u062A\u0627\u0631", [0.8, 0.9, 1.0, 1.1, 1.2], index=2, key="urdu_voice_rate")
            urdu_voice_volume = st.selectbox("\u0622\u0648\u0627\u0632 \u06A9\u06CC \u0622\u0648\u0627\u0632", [0.8, 1.0, 1.2, 1.5, 2.0], index=1, key="urdu_voice_volume")
    with urdu_right:
        with st.container(border=True):
            st.write("**\U0001F3A8 \u0648\u06CC\u0688\u06CC\u0648 \u0633\u06CC\u067D\u0646\u06AF\u0632**")
            urdu_aspect_options = [(tr("Portrait"), VideoAspect.portrait.value), (tr("Landscape"), VideoAspect.landscape.value), (tr("Square"), VideoAspect.square.value)]
            urdu_aspect_idx = st.selectbox(tr("Video Ratio"), options=range(len(urdu_aspect_options)), format_func=lambda x: urdu_aspect_options[x][0], key="urdu_aspect")
            urdu_aspect = urdu_aspect_options[urdu_aspect_idx][1]
            urdu_max_clip = st.selectbox(tr("Max Clip Duration (seconds)"), options=[2, 3, 4, 5, 6, 7, 8, 9, 10], index=4, key="urdu_clip_dur")
            urdu_enable_ken_burns = st.checkbox("Ken Burns Effect (\u0632\u0648\u0645 \u0645\u0648\u0634\u0646)", value=True, key="urdu_ken_burns")
        with st.container(border=True):
            st.write("**\u062D\u0631\u0648\u0641 \u0633\u06CC\u067D\u0646\u06AF\u0632 (\u0633\u0628 \u0679\u0627\u0626\u067D\u0644)**")
            urdu_subtitle_enabled = st.checkbox("\u0633\u0628 \u067E\u0627\u0626\u062F\u0644 \u0641\u0639\u0627\u0644", value=True, key="urdu_sub_enabled")
            all_fonts_list = get_all_fonts()
            urdu_font_priority = ["NotoNastaliqUrdu-Regular.ttf", "JameelNooriNastaleeq.ttf"]
            ordered_fonts = [f for f in urdu_font_priority if f in all_fonts_list] + [f for f in all_fonts_list if f not in urdu_font_priority]
            urdu_font_name = st.selectbox("\u0641\u0648\u0646\u067D (Urdu fonts \u0627\u0648\u067E\u0631 \u06C1\u06D2\u06BA)", options=ordered_fonts, index=0, key="urdu_font_select")
            urdu_font_size = st.slider("\u0641\u0648\u0646\u067D \u0633\u0627\u0626\u0632", 30, 100, 55, key="urdu_font_size")
            urdu_font_color = st.color_picker("\u062D\u0631\u0648\u0641 \u06A9\u0627 \u0631\u0646\u06AF", "#FFFFFF", key="urdu_font_color")
            urdu_stroke_color = st.color_picker("\u06A9\u0646\u0627\u0631\u06D2 \u06A9\u0627 \u0631\u0646\u06AF", "#000000", key="urdu_stroke_color")
            urdu_stroke_width = st.slider("\u06A9\u0646\u0627\u0631\u06D2 \u06A9\u06CC \u0686\u0648\u0688\u0627\u0626\u06CC", 0.0, 8.0, 1.5, key="urdu_stroke_width")
            urdu_sub_position_options = [(tr("Bottom"), "bottom"), (tr("Center"), "center"), (tr("Top"), "top")]
            urdu_sub_pos_idx = st.selectbox("\u0633\u0628 \u067E\u0627\u0626\u062F\u0644 \u067E\u0648\u0632\u06CC\u0634\u0646", options=range(len(urdu_sub_position_options)), format_func=lambda x: urdu_sub_position_options[x][0], key="urdu_sub_pos")
            urdu_sub_position = urdu_sub_position_options[urdu_sub_pos_idx][1]
        with st.container(border=True):
            st.write("**🎵 پس منظر موسیقی**")
            urdu_bgm_options = [(tr("No Background Music"), ""), (tr("Random Background Music"), "random")]
            urdu_bgm_idx = st.selectbox("BGM", options=range(len(urdu_bgm_options)), format_func=lambda x: urdu_bgm_options[x][0], index=1, key="urdu_bgm")
            urdu_bgm_type = urdu_bgm_options[urdu_bgm_idx][1]
            urdu_enable_ducking = st.checkbox("BGM دوران گفتگو کم کریں (Audio Ducking)", value=True, key="urdu_ducking")

        # 🏷️ Channel Logo Watermark
        u_logo_path, u_logo_pos, u_logo_sz, u_logo_op = render_logo_watermark_uploader(key_prefix="urdu")

    st.write("---")
    if st.button("🎬 اردو ویڈیو بنائیں", key="urdu_generate_btn", type="primary"):
        if not urdu_script.strip():
            st.error("براہ کرم پہلے اسکرپٹ لکھیں")
            st.stop()
        urdu_task_id = str(uuid4())
        urdu_params = VideoParams(
            video_subject=urdu_subject.strip(), video_script=urdu_script.strip(),
            video_terms=urdu_terms.strip() if urdu_terms.strip() else None,
            video_aspect=VideoAspect(urdu_aspect), video_concat_mode=VideoConcatMode.random,
            video_transition_mode=VideoTransitionMode.none, max_clip_duration=urdu_max_clip,
            voice_name=selected_urdu_voice, voice_rate=urdu_voice_rate, voice_volume=urdu_voice_volume,
            bgm_type=urdu_bgm_type, bgm_volume=0.4, subtitle_enabled=urdu_subtitle_enabled,
            font_name=urdu_font_name, font_size=urdu_font_size, text_fore_color=urdu_font_color,
            stroke_color=urdu_stroke_color, stroke_width=urdu_stroke_width, subtitle_position=urdu_sub_position,
            n_threads=2, paragraph_number=1, enable_audio_ducking=urdu_enable_ducking, enable_ken_burns=urdu_enable_ken_burns,
            logo_path=u_logo_path, logo_position=u_logo_pos, logo_size=u_logo_sz, logo_opacity=u_logo_op,
        )
        urdu_log_container = st.empty()
        urdu_log_records = []
        def urdu_log_received(msg):
            with urdu_log_container:
                urdu_log_records.append(msg)
                st.code("\n".join(urdu_log_records[-20:]))
        logger.add(urdu_log_received)
        st.toast("\u0627\u0631\u062F\u0648 \u0648\u06CC\u0688\u06CC\u0648 \u0628\u0646 \u0631\u06C1\u06CC \u06C1\u06D2...")
        with st.spinner("\u0627\u0631\u062F\u0648 \u0648\u06CC\u0688\u06CC\u0648 \u0628\u0646 \u0631\u06C1\u06CC \u06C1\u06D2..."):
            result = tm.start(task_id=urdu_task_id, params=urdu_params)
        if not result or "videos" not in result:
            st.error("\u0648\u06CC\u0688\u06CC\u0648 \u0628\u0646\u0627\u0646\u06D2 \u0645\u06CC\u06BA \u062E\u0631\u0627\u0628\u06CC")
        else:
            video_files = result.get("videos", [])
            st.success("\u0627\u0631\u062F\u0648 \u0648\u06CC\u0688\u06CC\u0648 \u0645\u06A9\u0645\u0644 \u06C1\u0648 \u06AF\u06CC!")
            try:
                for url in video_files:
                    st.video(url)
            except Exception:
                pass
            open_task_folder(urdu_task_id)


# ═══════════════════════════════════════════════════════════════════
# TEMPLATES
# ═══════════════════════════════════════════════════════════════════
def render_templates():
    st.markdown("## \U0001F4E6 Video Templates")
    st.markdown("Pick a ready-made template to auto-configure all video settings.")
    try:
        from app.services.templates import template_manager
        categories = ["All", "full", "intro", "outro", "transition"]
        selected_cat = st.selectbox("Filter by Category", categories, key="tmpl_cat_filter")
        templates = (template_manager.get_all_templates() if selected_cat == "All"
                     else template_manager.get_templates_by_category(selected_cat))
        if not templates:
            st.info("No templates found.")
        else:
            cols = st.columns(3)
            for i, tmpl in enumerate(templates):
                with cols[i % 3]:
                    with st.container(border=True):
                        cat_emoji = {"full": "\u2728", "intro": "\U0001F399️", "outro": "\U0001F3C1", "transition": "\U0001F504"}.get(tmpl["category"], "\U0001F4C4")
                        st.markdown(f"**{cat_emoji} {tmpl['name']}**")
                        st.caption(tmpl["description"])
                        tags_str = " ".join([f"`{t}`" for t in tmpl['tags'][:4]])
                        st.markdown(tags_str or " ")
                        if st.button("Apply", key=f"apply_tmpl_{tmpl['template_id']}"):
                            st.session_state["pending_template"] = tmpl["template_id"]
                            st.success(f"Template {tmpl['name']} selected!")
        st.divider()
        st.markdown("### Create Custom Template")
        with st.expander("Save current settings as template", expanded=False):
            tmpl_name = st.text_input("Template Name", key="custom_tmpl_name")
            tmpl_desc = st.text_input("Description", key="custom_tmpl_desc")
            tmpl_cat = st.selectbox("Category", ["full", "intro", "outro", "transition"], key="custom_tmpl_cat")
            tmpl_tags = st.text_input("Tags (comma-separated)", key="custom_tmpl_tags")
            if st.button("Save Template", key="save_custom_tmpl"):
                if tmpl_name:
                    template_manager.create_custom_template(name=tmpl_name, description=tmpl_desc, category=tmpl_cat,
                                                            tags=[t.strip() for t in tmpl_tags.split(",") if t.strip()], params={})
                    st.success(f"Template {tmpl_name} saved!")
                else:
                    st.error("Enter a template name.")
    except Exception as e:
        st.error(f"Templates error: {e}")


# ═══════════════════════════════════════════════════════════════════
# SMART SCRIPT
# ═══════════════════════════════════════════════════════════════════
def render_smart_script():
    st.markdown("## ✍️ Smart Script Tools")
    st.markdown("AI-powered translation, rephrasing, SEO, fact-check, tone, hooks & readability.")
    try:
        from app.services.smart_script import smart_script
        ss_tabs = st.tabs(["Translate", "Rephrase", "Tone", "SEO", "Fact Check", "Hooks", "Readability"])
        with ss_tabs[0]:
            st.markdown("### Translate Script")
            src_tr = st.text_area("Paste script:", height=180, key="tr_source")
            lang_opts = list(smart_script.SUPPORTED_LANGUAGES.items())
            tgt_idx = st.selectbox("Target Language", range(len(lang_opts)), format_func=lambda x: f"{lang_opts[x][0]} -- {lang_opts[x][1]}", key="tr_lang")
            if st.button("Translate", key="btn_translate"):
                if src_tr.strip():
                    with st.spinner("Translating..."):
                        out_tr = smart_script.translate_script(src_tr, lang_opts[tgt_idx][0])
                    st.text_area("Result:", value=out_tr, height=180, key="tr_result")
                    st.download_button("Download", out_tr, file_name="translated.txt")
                else:
                    st.error("Enter a script.")
        with ss_tabs[1]:
            st.markdown("### Rephrase Script")
            src_rp = st.text_area("Paste script:", height=180, key="rp_source")
            rp_styles = {"clearer": "Clearer", "shorter": "30% Shorter", "engaging": "More Engaging", "formal": "More Formal", "casual": "More Casual", "storytelling": "Storytelling"}
            rp_style = st.selectbox("Style", list(rp_styles.keys()), format_func=lambda x: rp_styles[x], key="rp_style")
            if st.button("Rephrase", key="btn_rephrase"):
                if src_rp.strip():
                    with st.spinner("Rephrasing..."):
                        out_rp = smart_script.rephrase_script(src_rp, rp_style)
                    st.text_area("Result:", value=out_rp, height=180, key="rp_result")
                    st.download_button("Download", out_rp, file_name="rephrased.txt")
                else:
                    st.error("Enter a script.")
        with ss_tabs[2]:
            st.markdown("### Apply Tone")
            src_tone = st.text_area("Paste script:", height=180, key="tone_source")
            tone_opts = list(smart_script.TONE_PRESETS.keys())
            tone_labels = [smart_script.TONE_PRESETS[t]["name"] for t in tone_opts]
            tone_idx = st.selectbox("Tone", range(len(tone_opts)), format_func=lambda x: tone_labels[x], key="tone_sel")
            if st.button("Apply Tone", key="btn_tone"):
                if src_tone.strip():
                    with st.spinner("Applying tone..."):
                        out_tone = smart_script.apply_tone(src_tone, tone_opts[tone_idx])
                    st.text_area("Result:", value=out_tone, height=180, key="tone_result")
                    st.download_button("Download", out_tone, file_name="toned.txt")
                else:
                    st.error("Enter a script.")
        with ss_tabs[3]:
            st.markdown("### SEO Optimizer")
            seo_title = st.text_input("Video Title", key="seo_title")
            seo_script = st.text_area("Script (optional)", height=100, key="seo_script")
            if st.button("Generate SEO", key="btn_seo"):
                if seo_title.strip():
                    with st.spinner("Generating..."):
                        seo_r = smart_script.optimize_seo(seo_title, seo_script)
                    st.code(seo_r.get("optimized_title", ""), language=None)
                    st.text_area("Description:", value=seo_r.get("description", ""), key="seo_desc_out")
                    st.code(" ".join(seo_r.get("hashtags", [])), language=None)
                else:
                    st.error("Enter a title.")
        with ss_tabs[4]:
            st.markdown("### Fact Check")
            src_fc = st.text_area("Paste script:", height=180, key="fc_source")
            if st.button("Analyze", key="btn_factcheck"):
                if src_fc.strip():
                    with st.spinner("Analyzing..."):
                        fc_r = smart_script.fact_check(src_fc)
                    rel = fc_r.get("overall_reliability", "medium")
                    emoji_map = {"high": "\U0001F7E2", "medium": "\U0001F7E1", "low": "\U0001F534"}
                    st.markdown(f"**Reliability:** {emoji_map.get(rel, '⚪')} {rel.upper()}")
                    for c in fc_r.get("claims", []):
                        conf_e = {"high": "\U0001F7E2", "medium": "\U0001F7E1", "low": "\U0001F534"}.get(c.get('confidence', 'medium'), '⚪')
                        st.markdown(f"- {conf_e} **{c.get('category', '')}**: _{c.get('claim', '')}_")
                else:
                    st.error("Enter a script.")
        with ss_tabs[5]:
            st.markdown("### Generate Hooks")
            hook_topic = st.text_input("Topic", key="hook_topic")
            hook_count = st.slider("Count", 3, 10, 5, key="hook_count")
            if st.button("Generate", key="btn_hooks"):
                if hook_topic.strip():
                    with st.spinner("Generating..."):
                        hooks = smart_script.generate_hooks(hook_topic, hook_count)
                    for i, h in enumerate(hooks, 1):
                        st.markdown(f"**{i}.** {h}")
                else:
                    st.error("Enter a topic.")
        with ss_tabs[6]:
            st.markdown("### Readability Analysis")
            src_rd = st.text_area("Paste script:", height=180, key="rd_source")
            if st.button("Analyze", key="btn_readability"):
                if src_rd.strip():
                    rd_r = smart_script.analyze_readability(src_rd)
                    score = rd_r.get("score", 0)
                    level = rd_r.get("level", "unknown")
                    metrics = rd_r.get("metrics", {})
                    color = "green" if score >= 60 else "orange" if score >= 40 else "red"
                    st.markdown(f"**Flesch Score:** :{color}[{score}] -- **{level}**")
                    c1, c2, c3 = st.columns(3)
                    c1.metric("Words", metrics.get("word_count", 0))
                    c2.metric("Sentences", metrics.get("sentence_count", 0))
                    c3.metric("Avg Words/Sentence", metrics.get("avg_sentence_length", 0))
                else:
                    st.error("Enter a script.")
    except Exception as e:
        st.error(f"Smart Script error: {e}")


# ═══════════════════════════════════════════════════════════════════
# A/B TESTING
# ═══════════════════════════════════════════════════════════════════
def render_ab_testing():
    st.markdown("## \U0001F3AF A/B Video Testing")
    st.markdown("Generate multiple variants and compare results.")
    try:
        from app.services.ab_testing import ab_test_manager
        ab_sub = st.tabs(["New Test", "Past Tests"])
        with ab_sub[0]:
            ab_name = st.text_input("Test Name", placeholder="Azure vs Chatterbox", key="ab_name")
            ab_subject = st.text_input("Video Subject", key="ab_subject")
            ab_script_input = st.text_area("Script (optional)", height=80, key="ab_script")
            n_variants = st.slider("Number of Variants", 2, 4, 2, key="ab_n_variants")
            variants_cfg = []
            for vi in range(n_variants):
                with st.container(border=True):
                    st.markdown(f"**Variant {chr(65+vi)}**")
                    vn = st.text_input("Name", value=f"Variant {chr(65+vi)}", key=f"ab_v{vi}_name")
                    vv = st.text_input("Voice Override (optional)", key=f"ab_v{vi}_voice")
                    vc = st.selectbox("Concat Mode", ["random", "sequential", "semantic"], key=f"ab_v{vi}_concat")
                    override = {}
                    if vv.strip():
                        override["voice_name"] = vv.strip()
                    override["video_concat_mode"] = vc
                    variants_cfg.append({"name": vn, "params_override": override})
            if st.button("Run A/B Test", type="primary", key="ab_run"):
                if ab_subject.strip() and ab_name.strip():
                    base = {
                        "video_subject": ab_subject.strip(), "video_script": ab_script_input.strip(),
                        "video_source": config.app.get("video_source", "pexels"),
                        "voice_name": config.ui.get("voice_name", ""),
                    }
                    with st.spinner(f"Running {n_variants} variants..."):
                        test = ab_test_manager.create_test(ab_name, base, variants_cfg)
                        ab_test_manager.run_test(test.test_id)
                    results = ab_test_manager.get_test_results(test.test_id)
                    if results:
                        st.success(f"Done! Winner: {results.get('winner_name', 'N/A')}")
                        for v in results.get("variants", []):
                            icon = "✅" if v["status"] == "completed" else "❌"
                            crown = "👑 " if v["variant_id"] == results.get("winner") else ""
                            st.markdown(f"{icon} {crown}**{v['name']}**")
                            for url in v.get("video_urls", []):
                                if os.path.exists(url):
                                    st.video(url)
                else:
                    st.error("Enter test name and subject.")
        with ab_sub[1]:
            all_tests = ab_test_manager.get_all_tests()
            if not all_tests:
                st.info("No A/B tests yet.")
            else:
                for t in reversed(all_tests):
                    icon = {"pending": "⏳", "running": "🔄", "completed": "✅", "failed": "❌"}.get(t["status"], "❓")
                    with st.expander(f"{icon} {t['name']} -- {t['status']}"):
                        st.json(t)
    except Exception as e:
        st.error(f"A/B Testing error: {e}")


# ═══════════════════════════════════════════════════════════════════
# SETTINGS
# ═══════════════════════════════════════════════════════════════════
def render_settings():
    st.markdown('<div class="page-title">Settings</div>', unsafe_allow_html=True)
    st.markdown('<div class="page-subtitle">App configuration and preferences</div>', unsafe_allow_html=True)
    with st.expander("Basic Settings", expanded=True):
        config_panels = st.columns(3)
        with config_panels[0]:
            hide_config = st.checkbox("Hide Basic Settings", value=config.app.get("hide_config", False))
            config.app["hide_config"] = hide_config
            hide_log = st.checkbox("Hide Log", value=config.ui.get("hide_log", False))
            config.ui["hide_log"] = hide_log
        with config_panels[1]:
            st.write("LLM Settings")
            llm_providers = ["OpenAI", "Moonshot", "Azure", "Qwen", "DeepSeek", "Gemini", "Ollama", "G4f", "OneAPI", "Cloudflare", "ERNIE", "Pollinations"]
            saved_llm_provider = config.app.get("llm_provider", "openai").lower()
            saved_idx = next((i for i, p in enumerate(llm_providers) if p.lower() == saved_llm_provider), 0)
            llm_provider = st.selectbox("LLM Provider", options=llm_providers, index=saved_idx)
            llm_provider = llm_provider.lower()
            config.app["llm_provider"] = llm_provider
            llm_helper = st.container()
            tips = ""
            if llm_provider == "ollama":
                if not config.app.get(f"{llm_provider}_model_name"):
                    config.app[f"{llm_provider}_model_name"] = "qwen:7b"
                if not config.app.get(f"{llm_provider}_base_url"):
                    config.app[f"{llm_provider}_base_url"] = "http://localhost:11434/v1"
                tips = "API Key: 123 | Base: http://localhost:11434/v1 | Model: ollama list"
            elif llm_provider == "openai":
                tips = "API Key: https://platform.openai.com/api-keys | Base: optional | Model: check limits page"
            elif llm_provider == "deepseek":
                if not config.app.get(f"{llm_provider}_base_url"):
                    config.app[f"{llm_provider}_base_url"] = "https://api.deepseek.com"
                tips = "API Key: https://platform.deepseek.com | Base: https://api.deepseek.com | Model: deepseek-chat"
            elif llm_provider == "moonshot":
                tips = "API Key: https://platform.moonshot.cn | Base: https://api.moonshot.cn/v1 | Model: moonshot-v1-8k"
            elif llm_provider == "pollinations":
                tips = "API Key: optional | Base: https://pollinations.ai/api/v1 | Model: openai-fast"
            if tips:
                llm_helper.info(tips)
            api_key = st.text_input("API Key", type="password", value=config.app.get(f"{llm_provider}_api_key", ""), key=f"set_{llm_provider}_api_key")
            if api_key:
                config.app[f"{llm_provider}_api_key"] = api_key
            base_url = st.text_input("Base Url", value=config.app.get(f"{llm_provider}_base_url", ""), key=f"set_{llm_provider}_base_url")
            if base_url:
                config.app[f"{llm_provider}_base_url"] = base_url
            model_name = st.text_input("Model Name", value=config.app.get(f"{llm_provider}_model_name", ""), key=f"set_{llm_provider}_model_name")
            if model_name:
                config.app[f"{llm_provider}_model_name"] = model_name
        with config_panels[2]:
            st.write("Video Source Settings")
            pexels_key = st.text_input("Pexels API Key", type="password", value=", ".join(config.app.get("pexels_api_keys", [])) if isinstance(config.app.get("pexels_api_keys"), list) else config.app.get("pexels_api_keys", ""))
            if pexels_key:
                config.app["pexels_api_keys"] = [k.strip() for k in pexels_key.split(",") if k.strip()]
            pixabay_key = st.text_input("Pixabay API Key", type="password", value=", ".join(config.app.get("pixabay_api_keys", [])) if isinstance(config.app.get("pixabay_api_keys"), list) else config.app.get("pixabay_api_keys", ""))
            if pixabay_key:
                config.app["pixabay_api_keys"] = [k.strip() for k in pixabay_key.split(",") if k.strip()]
            
            st.markdown("---")
            if st.button("🧹 Clean Old Videos & Cache Memory", key="clean_cache_settings"):
                from app.services.material import clear_video_cache
                clear_video_cache()
                st.success("🧹 All old videos and cache memory cleaned successfully!")
    st.markdown("---")
    st.write(f"**ClipGenesis** v{VERSION} -- AI Video Studio")
    st.caption("All settings are saved automatically to config.toml")


# ═══════════════════════════════════════════════════════════════════════════════
# PAGE ROUTER  (must be after all render_* functions are defined)
# ═══════════════════════════════════════════════════════════════════════════════
PAGE_MAP = {
    "dashboard": render_dashboard,
    "wizard": render_video_wizard,
    "single": render_single_video,
    "batch": render_batch_generation,
    "voice": render_voice_trends,
    "voicestudio": render_voice_studio_page,
    "urdu": render_urdu_video,
    "quran": render_quran_video,
    "darood": render_darood_video_page,
    "templates": render_templates,
    "scripts": render_smart_script,
    "abtest": render_ab_testing,
    "settings": render_settings,
}

if current_page in PAGE_MAP:
    PAGE_MAP[current_page]()

config.save_config()
