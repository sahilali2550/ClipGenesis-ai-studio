"""
quran_video_page.py — Streamlit UI page for Quran Video Generator.
"""

import os
import streamlit as st
from loguru import logger
from uuid import uuid4
from app.services import quran_api
from app.config import config
from app.utils import utils


def render_quran_video():
    reciters     = quran_api.get_reciters_list()
    translations = quran_api.TRANSLATIONS

    # ── Layout: 2 columns ──────────────────────────────────────────────────────
    left, right = st.columns([1, 1], gap="large")

    # ════════════════════════════════════════════
    # LEFT PANEL
    # ════════════════════════════════════════════
    with left:
        # ── Quran Input ──────────────────────────────────────────────────────
        with st.container(border=True):
            st.markdown("#### 📖 Quran Input")

            surah_num = st.number_input(
                "Surah نمبر (1–114)",
                min_value=1, max_value=114, value=55, step=1,
                key="q_surah",
            )
            surah_info = quran_api.get_surah_info(surah_num)
            total_ayahs = surah_info["ayah_count"]

            st.markdown(
                f'<div style="background:rgba(255,107,53,0.1);border:1px solid rgba(255,107,53,0.3);'
                f'border-radius:8px;padding:8px 14px;margin-bottom:8px;font-size:0.9rem;">'
                f'<b style="color:#FF6B35">Surah {surah_num}:</b> '
                f'<span style="color:#E8E0D8">{surah_info["name"]}</span> '
                f'<span style="color:#8A7F78">— {total_ayahs} Ayahs</span></div>',
                unsafe_allow_html=True,
            )

            col_a, col_b = st.columns(2)
            with col_a:
                from_ayah = st.number_input(
                    "Ayah سے", min_value=1, max_value=total_ayahs, value=1, key="q_from"
                )
            with col_b:
                to_ayah = st.number_input(
                    "Ayah تک", min_value=from_ayah, max_value=total_ayahs,
                    value=min(10, total_ayahs), key="q_to"
                )

            ayah_count = to_ayah - from_ayah + 1
            st.caption(f"📊 مجموعی Ayahs: {ayah_count}")

        # ── Live Quran Text Preview Box ───────────────────────────────────────
        with st.container(border=True):
            st.markdown("#### 📜 Live Arabic & Translation Preview")
            try:
                preview_arabic = quran_api.get_ayahs_arabic(surah_num, from_ayah, min(from_ayah + 1, to_ayah))
                preview_trans = quran_api.get_translations(surah_num, from_ayah, min(from_ayah + 1, to_ayah), "ur.jalandhry")

                if preview_arabic:
                    ar_txt = " ".join([a.get("arabic", "") for a in preview_arabic])
                    tr_txt = " ".join([preview_trans.get(a.get("ayah"), "") for a in preview_arabic])
                    st.markdown(
                        f"""
                        <div style="background: rgba(255,107,53,0.06); border: 1px solid rgba(255,107,53,0.25); border-radius: 12px; padding: 16px; text-align: center;">
                            <div style="font-size: 1.5rem; font-weight: 700; color: #FFD700; line-height: 1.8; margin-bottom: 10px;">
                                {ar_txt}
                            </div>
                            <div style="font-size: 0.95rem; color: #E8E0D8;">
                                <b>اردو ترجمہ:</b> {tr_txt}
                            </div>
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )
                else:
                    st.info("🔄 Live text loading...")
            except Exception as pe:
                st.caption(f"Text preview unavailable: {pe}")

        # ── Reciter ───────────────────────────────────────────────────────────
        with st.container(border=True):
            st.markdown("#### 🎙️ Reciter (قاری)")
            reciter_name = st.selectbox(
                "قاری منتخب کریں",
                options=list(reciters.keys()),
                index=0,
                key="q_reciter",
            )

        # ── Translation ───────────────────────────────────────────────────────
        with st.container(border=True):
            st.markdown("#### 🌐 ترجمہ")
            tr_label = st.selectbox(
                "ترجمہ",
                options=list(translations.keys()),
                index=0,
                key="q_translation",
            )
            translation_edition = translations[tr_label]

        # ── Audio FX ──────────────────────────────────────────────────────────
        with st.container(border=True):
            st.markdown("#### 🔊 Audio Effects")
            from app.services.quran_task import ECHO_PRESETS
            echo_preset = st.selectbox(
                "Echo Effect",
                options=list(ECHO_PRESETS.keys()),
                index=2,  # Medium default
                key="q_echo",
            )
            bgm_volume = st.slider("Background Music Volume", 0.0, 0.5, 0.12, 0.01, key="q_bgm_vol")
            bgm_path = st.text_input("BGM File Path (optional)", placeholder="C:/path/to/nasheed.mp3", key="q_bgm")

    # ════════════════════════════════════════════
    # RIGHT PANEL
    # ════════════════════════════════════════════
    with right:
        # ── Video Settings ────────────────────────────────────────────────────
        with st.container(border=True):
            st.markdown("#### 🎬 Video Settings")
            aspect = st.selectbox(
                "Aspect Ratio",
                ["Portrait 9:16 (TikTok/Reels)", "Landscape 16:9 (YouTube)"],
                index=0, key="q_aspect",
            )
            video_aspect = "9:16" if "9:16" in aspect else "16:9"

            font_script = st.selectbox(
                "🔤 Arabic Font Style / Script",
                options=[
                    "🕋 Uthmanic Hafs (Saudi / Madina Mushaf)",
                    "🇵🇰 Indo-Pak / Jameel Noori Nastaleeq (Pakistani)",
                    "🌟 Kufic Modern Reel Style",
                ],
                index=0,
                key="q_font_script",
            )

            video_sources = ["hybrid", "pexels", "pixabay", "local"]
            video_source = st.selectbox(
                "Background Source",
                video_sources,
                format_func=lambda x: {
                    "hybrid": "🔥 Hybrid (Pexels + Pixabay Combined - Maximum Collection)",
                    "pexels": "Pexels Only",
                    "pixabay": "Pixabay Only",
                    "local": "Local Video Files",
                }.get(x, x),
                index=0,
                key="q_vsource"
            )

            if video_source == "pexels":
                pexels_key = st.text_input(
                    "Pexels API Key",
                    value=", ".join(config.app.get("pexels_api_keys", [])) if isinstance(config.app.get("pexels_api_keys"), list) else config.app.get("pexels_api_keys", ""),
                    type="password", key="q_pexels_key"
                )
            elif video_source == "pixabay":
                pixabay_key = st.text_input(
                    "Pixabay API Key",
                    value=config.app.get("pixabay_api_keys", ""),
                    type="password", key="q_pixabay_key"
                )
            else:
                pexels_key = pixabay_key = ""

        # ── Channel Logo Watermark ──────────────────────────────────────────
        with st.container(border=True):
            st.markdown("#### 🏷️ Channel Logo Watermark")
            q_logo_file = st.file_uploader(
                "Upload Channel Logo / Watermark PNG (Optional)",
                type=["png", "jpg", "jpeg"],
                key="q_logo_upload",
            )
            q_logo_path = ""
            if q_logo_file is not None:
                temp_logo_dir = os.path.join(utils.root_dir(), "storage", "logos")
                os.makedirs(temp_logo_dir, exist_ok=True)
                q_logo_path = os.path.join(temp_logo_dir, q_logo_file.name)
                with open(q_logo_path, "wb") as f:
                    f.write(q_logo_file.getbuffer())
                st.success(f"🏷️ Logo Loaded: **{q_logo_file.name}**")

            if q_logo_path:
                col_ql1, col_ql2 = st.columns(2)
                with col_ql1:
                    q_logo_pos = st.selectbox(
                        "Logo Position",
                        options=["top_right", "top_left", "top_center", "bottom_right", "bottom_left"],
                        format_func=lambda x: {
                            "top_right": "↗️ Top Right",
                            "top_left": "↖️ Top Left",
                            "top_center": "⏺️ Top Center",
                            "bottom_right": "↘️ Bottom Right",
                            "bottom_left": "↙️ Bottom Left",
                        }.get(x, x),
                        key="q_logo_pos_select",
                    )
                with col_ql2:
                    q_logo_sz = st.slider("Logo Width (px)", 60, 300, 130, 10, key="q_logo_sz_slider")
                q_logo_op = st.slider("Logo Opacity", 0.2, 1.0, 0.90, 0.05, key="q_logo_op_slider")
            else:
                q_logo_pos = "top_right"
                q_logo_sz = 130
                q_logo_op = 0.90

        # ── Subtitle & Styling ────────────────────────────────────────────────
        with st.container(border=True):
            st.markdown("#### 🎨 Subtitle & Styling")
            col_fs1, col_fs2 = st.columns(2)
            with col_fs1:
                arabic_font_size = st.slider("Arabic Font Size", 40, 120, 70, key="q_arabic_size")
            with col_fs2:
                translation_font_size = st.slider("Translation Font Size", 20, 70, 40, key="q_trans_size")

            col_c1, col_c2, col_c3 = st.columns(3)
            with col_c1:
                arabic_color = st.color_picker("Arabic Text", "#FFD700", key="q_arabic_color")
            with col_c2:
                highlight_color = st.color_picker("Highlight", "#00FFC8", key="q_highlight_color")
            with col_c3:
                translation_color = st.color_picker("Translation", "#FFFFFF", key="q_trans_color")

            subtitle_pos = st.slider("Subtitle Vertical Position (%)", 10, 90, 50, key="q_sub_pos")

        # ── Preview ───────────────────────────────────────────────────────────
        with st.container(border=True):
            st.markdown("#### 👁️ Preview (Word Karaoke Highlight)")
            st.markdown(
                f'<div style="background:#0D0D0D;border:1px solid rgba(255,215,0,0.3);'
                f'border-radius:10px;padding:20px;text-align:center;min-height:80px;">'
                f'<div style="font-size:1.8rem;font-family:serif;direction:rtl;margin-bottom:8px;">'
                f'<span style="color:#FFFFFF;">بِسْمِ </span>'
                f'<span style="color:{highlight_color};font-weight:bold;text-shadow: 0 0 12px {highlight_color};">ٱللَّهِ </span>'
                f'<span style="color:#FFFFFF;">ٱلرَّحْمَـٰنِ ٱلرَّحِيمِ</span></div>'
                f'<div style="font-size:1rem;color:{translation_color};opacity:0.85;">'
                f'اللہ کے نام سے جو بڑا مہربان ہے</div>'
                f'<div style="font-size:0.75rem;color:#5A4F48;margin-top:8px;">'
                f'Surah {surah_num}: {surah_info["name"]} — Ayah {from_ayah}–{to_ayah}</div>'
                f'</div>',
                unsafe_allow_html=True,
            )

    # ── Generate Button ────────────────────────────────────────────────────────
    st.markdown("<br>", unsafe_allow_html=True)

    if st.button("🎬 Generate Quran Video", type="primary",
                 use_container_width=True, key="q_generate"):

        # Validate
        if from_ayah > to_ayah:
            st.error("❌ 'Ayah سے' بڑی نہیں ہو سکتی 'Ayah تک' سے!")
            st.stop()

        if video_source == "pexels" and not (pexels_key or config.app.get("pexels_api_keys")):
            st.error("❌ Pexels API Key درج کریں (Settings میں بھی save کر سکتے ہیں)")
            st.stop()

        task_id = str(uuid4())
        log_box    = st.empty()
        prog_bar   = st.progress(0, text="شروع ہو رہا ہے...")
        log_lines  = []

        def log_cb(msg):
            log_lines.append(msg)
            log_box.code("\n".join(log_lines[-20:]))

        def prog_cb(val, msg=""):
            prog_bar.progress(min(val, 1.0), text=msg or "Processing...")

        bgm_file_path = bgm_path.strip() if bgm_path and os.path.exists(bgm_path.strip()) else ""

        from app.services import quran_task
        with st.spinner("⏳ Video بن رہی ہے — براہ کرم انتظار کریں..."):
            result = quran_task.generate_quran_video(
                task_id=task_id,
                surah=surah_num,
                from_ayah=from_ayah,
                to_ayah=to_ayah,
                reciter_name=reciter_name,
                translation_edition=translation_edition,
                video_source=video_source,
                video_aspect=video_aspect,
                arabic_font_size=arabic_font_size,
                translation_font_size=translation_font_size,
                arabic_color=arabic_color,
                highlight_color=highlight_color,
                translation_color=translation_color,
                echo_preset=echo_preset,
                bgm_file=bgm_file_path,
                bgm_volume=bgm_volume,
                subtitle_position_pct=subtitle_pos / 100,
                progress_cb=prog_cb,
                log_cb=log_cb,
                pexels_api_key=pexels_key if video_source == "pexels" else "",
                pixabay_api_key=pixabay_key if video_source == "pixabay" else "",
                logo_path=q_logo_path,
                logo_position=q_logo_pos,
                logo_size=q_logo_sz,
                logo_opacity=q_logo_op,
            )

        if result and os.path.exists(result):
            prog_bar.progress(1.0, text="✅ مکمل!")
            st.success(f"✅ Video تیار ہے!")
            st.video(result)
            with open(result, "rb") as f:
                st.download_button(
                    label="⬇️ Download Video",
                    data=f,
                    file_name=f"quran_{surah_num}_{from_ayah}_{to_ayah}.mp4",
                    mime="video/mp4",
                    key="q_download",
                )
            st.session_state["preview_video"] = result
            st.session_state["preview_title"] = f"Surah {surah_info['name']} {from_ayah}–{to_ayah}"
        else:
            prog_bar.progress(0)
            st.error("❌ Video generation ناکام رہی — اوپر logs دیکھیں")
