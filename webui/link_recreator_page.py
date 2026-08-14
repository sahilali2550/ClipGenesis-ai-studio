"""
link_recreator_page.py — Streamlit UI page for 🔗 Link-to-Video Re-Creator.
Pastes a YouTube Shorts / Facebook Reel / TikTok / Instagram Reel URL and
recreates a 100% unique copyright-safe video — pure audio + background, no text overlay.
"""

import os
import streamlit as st
from loguru import logger

from app.services import link_recreator
from app.utils import utils


def render_link_recreator_page():
    """Render the 🔗 Link-to-Video Re-Creator page."""
    st.markdown("### 🔗 Universal Link-to-Video Re-Creator")
    st.caption(
        "Paste a YouTube Shorts, Facebook Reel, TikTok, or Instagram Reel link — "
        "the app downloads the original audio and replaces the background with a fresh 4K clip. "
        "**No text, no subtitles, no watermarks — pure audio + video only.**"
    )

    col_left, col_right = st.columns([1, 1], gap="large")

    with col_left:
        # ── URL Input ─────────────────────────────────────────────────────────
        with st.container(border=True):
            st.markdown("#### 📥 Paste Video URL")
            video_url = st.text_input(
                "Video Link / URL",
                placeholder="https://www.facebook.com/reel/... or https://youtube.com/shorts/...",
                key="url_input_link",
            )
            st.caption(
                "Supported: **YouTube Shorts** • **Facebook Reels** • "
                "**TikTok** • **Instagram Reels** • **Twitter / X**"
            )

        # ── Settings ──────────────────────────────────────────────────────────
        with st.container(border=True):
            st.markdown("#### ⚙️ Background & Copyright Settings")

            # Anti-Copyright Shield Checkbox
            enable_shield = st.checkbox(
                "🛡️ Enable Maximum Anti-Copyright Shield (Content ID Pitch Shift & ASMR Rain Mix)",
                value=True,
                help="Modulates audio frequencies (0.985x-1.015x) and layers subtle ASMR rain to ensure 100% protection against Facebook & YouTube Content ID matches.",
                key="url_copyright_shield"
            )

            # Automatic Subtitles Overlay Checkbox
            enable_subtitles = st.checkbox(
                "🔤 Enable Dynamic Auto-Subtitles Overlay (آن اسکرین سب ٹائٹلز)",
                value=False,
                help="Automatically extracts audio transcript and overlays animated karaoke subtitles on top of the video.",
                key="url_enable_subtitles"
            )

            subtitle_style = "gold"
            if enable_subtitles:
                sub_style_options = [
                    ("🌟 Golden Yellow Karaoke (سنہری پیلا)", "gold"),
                    ("⚡ Neon Cyan Glow (نیون فیروزی)",     "cyan"),
                    ("🤍 Clean White & Shadow (کلاسک وائٹ)", "white"),
                    ("💚 Emerald Green Reel (زمردی سبز)",    "green"),
                ]
                sel_sub_idx = st.selectbox(
                    "🎨 Subtitle Style & Color",
                    options=range(len(sub_style_options)),
                    format_func=lambda x: sub_style_options[x][0],
                    index=0,
                    key="url_subtitle_style"
                )
                subtitle_style = sub_style_options[sel_sub_idx][1]

            # Audio Mode: Keep Original vs AI Voice Dubbing
            dub_options = [
                ("🎵 Keep Original Video Audio (اصل ویڈیو کی آواز)", "original"),
                ("🎙️ AI Voice / Cloned Voice Dubbing (آواز تبدیل کریں)", "ai_voice"),
            ]
            sel_dub_idx = st.selectbox(
                "🎙️ Audio & Voice Mode (آواز کا انتخاب)",
                options=range(len(dub_options)),
                format_func=lambda x: dub_options[x][0],
                index=0,
                key="url_dub_mode"
            )
            dub_mode = dub_options[sel_dub_idx][1]
            selected_voice = ""

            if dub_mode == "ai_voice":
                from app.services import voice, voice_cloner
                voice_options = voice.get_all_azure_voices()
                cloned_v = voice_cloner.get_cloned_voices()
                
                v_display_map = {}
                for cv in reversed(cloned_v):
                    c_id = cv.get('voice_id')
                    c_label = f"🎙️ Cloned: {cv.get('name')} ({cv.get('language', 'ur').upper()})"
                    v_display_map[c_id] = c_label
                    if c_id not in voice_options:
                        voice_options.insert(0, c_id)

                for vo in voice_options:
                    if vo not in v_display_map:
                        v_display_map[vo] = vo.replace("Female", "Female").replace("Male", "Male").replace("Neural", "")

                selected_voice = st.selectbox(
                    "Choose AI / Cloned Voice",
                    options=voice_options,
                    format_func=lambda x: v_display_map.get(x, x),
                    key="url_selected_voice"
                )

            # ── Video Source ──────────────────────────────────────────────────
            _src_options = [
                ("🔥 Ultimate Hybrid (Pexels + Pixabay + Coverr + Mixkit + Videvo — Max 4K)", "hybrid"),
                ("🤖 9Router AI Images + Motion (Free)",   "9router"),
                ("Pexels Only",                            "pexels"),
                ("Pixabay Only",                           "pixabay"),
            ]
            _src_sel = st.selectbox(
                "Video Source / ویڈیو سورس",
                options=range(len(_src_options)),
                format_func=lambda x: _src_options[x][0],
                index=0,
                key="url_video_source",
            )
            video_source = _src_options[_src_sel][1]
            image_style = "photorealistic"

            if video_source == "9router":
                st.info(
                    "🤖 **9Router AI Images + Motion**: Video URL کے title/topic کے "
                    "مطابق AI تصویر بنائی جائے گی۔"
                )
                style_opts = [
                    ("📸 Photorealistic 8K (سینماٹک رئیلزم)", "photorealistic"),
                    ("🎨 3D Pixar / Disney (3D کارٹون سٹائل)", "3d_pixar"),
                    ("🖌️ Anime / Manga (جاپانی اینیمے آرٹ)", "anime"),
                    ("🌌 Cyberpunk Dark (نیون فیوچرسٹک ڈارک)", "cyberpunk"),
                    ("🖼️ Vintage Oil Painting (کلاسک ائل پینٹنگ)", "oil_painting"),
                ]
                sel_st_idx = st.selectbox(
                    "🎭 AI Image Art Style",
                    options=range(len(style_opts)),
                    format_func=lambda x: style_opts[x][0],
                    index=0,
                    key="url_image_style"
                )
                image_style = style_opts[sel_st_idx][1]

            bg_theme = st.selectbox(
                "Background Video Theme",
                options=[
                    "smart_auto_match", "kaaba", "madinah", "mosque", "quran", "rain", "ocean",
                    "nature", "dark_aesthetic", "autumn", "snow", "space",
                    "candle", "driving", "city"
                ],
                format_func=lambda x: {
                    "smart_auto_match": "✨ Smart Auto-Match (Videos as Script Requirements + 9Router AI)",
                    "kaaba":          "🕋 Kaaba / Mecca (مکہ مکرمہ)",
                    "madinah":        "🕌 Madinah & Green Dome (مدینہ منورہ)",
                    "mosque":         "🏛️ Mosque Interior & Architecture (مسجد)",
                    "quran":          "📖 Islamic Calligraphy & Quran Ambiance (خطاطی)",
                    "rain":           "🌧️ Rain & Storm ASMR (بارش)",
                    "ocean":          "🌊 Ocean Waves & Beach (سمندر کی لہریں)",
                    "nature":         "🌿 Mountain & Nature Aerial (پہاڑ و وادی)",
                    "dark_aesthetic": "🔥 Dark Aesthetic & Gold Glow (ڈارک فریم)",
                    "autumn":         "🍃 Autumn Woods & Falling Leaves (خریف کا موسم)",
                    "snow":           "❄️ Winter Snowfall & Frozen Peaks (برف باری)",
                    "space":          "🌌 Deep Space & Northern Aurora (کہکشان)",
                    "candle":         "🕯️ Candle Glow & Vintage Ambiance (موم بتی)",
                    "driving":        "🚗 Driving POV & Rainy Highway (ڈرائیونگ)",
                    "city":           "🏙️ City Lights & Night Timelapse (نائٹ سٹی)",
                }.get(x, x),
                index=0,
                key="url_bg_theme",
            )

            aspect = st.selectbox(
                "Video Aspect Ratio",
                options=["portrait", "landscape"],
                format_func=lambda x: (
                    "📱 Shorts / Reels (9:16 Portrait)"
                    if x == "portrait"
                    else "🖥️ YouTube / Landscape (16:9)"
                ),
                key="url_aspect",
            )

        # ── Channel Logo / Watermark Upload ──────────────────────────────────
        with st.container(border=True):
            st.markdown("#### 🏷️ Channel Branding (Optional)")
            logo_file = st.file_uploader(
                "Upload Logo / Watermark PNG",
                type=["png", "jpg", "jpeg"],
                key="url_logo_upload"
            )
            logo_path = ""
            if logo_file is not None:
                upload_dir = os.path.join(utils.root_dir(), "storage", "custom_logos")
                os.makedirs(upload_dir, exist_ok=True)
                logo_path = os.path.join(upload_dir, logo_file.name)
                with open(logo_path, "wb") as f:
                    f.write(logo_file.getbuffer())
                st.success(f"🏷️ Logo Loaded: **{logo_file.name}**")

        # ── Generate Button ───────────────────────────────────────────────────
        if st.button("🚀 Re-Create Unique Reel", type="primary", use_container_width=True):
            if not video_url.strip():
                st.error("⚠️ Please paste a valid video URL first!")
            else:
                with st.spinner("⏳ Downloading audio & compositing background video…"):
                    try:
                        res_data = link_recreator.recreate_video_from_url(
                            url=video_url.strip(),
                            background_theme=bg_theme,
                            aspect_ratio=aspect,
                            video_source=video_source,
                            enable_copyright_shield=enable_shield,
                            enable_subtitles=enable_subtitles,
                            subtitle_style=subtitle_style,
                            selected_voice=selected_voice,
                            image_style=image_style,
                            logo_path=logo_path,
                        )
                        st.session_state["last_recreated_res"] = res_data
                        st.session_state["last_recreated_video"] = res_data["video_path"]
                        st.success("🎉 Reel re-created successfully!")
                    except Exception as ex:
                        logger.error(f"Link Re-Creator error: {ex}")
                        st.error(f"❌ Generation Error: {ex}")

    # ── Right Panel: Output Player ─────────────────────────────────────────────
    with col_right:
        st.markdown("### 🎬 Re-Created Output & Player")

        if (
            "last_recreated_video" in st.session_state
            and os.path.exists(st.session_state["last_recreated_video"])
        ):
            v_path = st.session_state["last_recreated_video"]
            st.video(v_path)

            with open(v_path, "rb") as vf:
                st.download_button(
                    label="⬇️ Download Re-Created Reel (MP4)",
                    data=vf.read(),
                    file_name=os.path.basename(v_path),
                    mime="video/mp4",
                    use_container_width=True,
                )

            res_data = st.session_state.get("last_recreated_res", {})
            
            # ── Render AI Auto-Thumbnails ──────────────────────────────────────
            thumbs = res_data.get("thumbnails", [])
            if thumbs:
                st.markdown("#### 🖼️ AI Auto-Thumbnails (High CTR)")
                t_cols = st.columns(len(thumbs))
                for idx, t_path in enumerate(thumbs):
                    if os.path.exists(t_path):
                        with t_cols[idx]:
                            st.image(t_path, caption=f"Thumbnail #{idx+1}")
                            with open(t_path, "rb") as tf:
                                st.download_button(
                                    f"⬇️ Thumb #{idx+1}",
                                    data=tf.read(),
                                    file_name=os.path.basename(t_path),
                                    mime="image/jpeg",
                                    key=f"dl_thumb_{idx}"
                                )

            # ── Render Viral SEO Hashtags & Description ─────────────────────────
            seo_desc = res_data.get("seo_description", "")
            hashtags = res_data.get("hashtags", "")
            if seo_desc or hashtags:
                with st.expander("🏷️ Viral Hashtags & SEO Description (Copy-Paste)", expanded=True):
                    st.text_area("Hashtags & Description", value=seo_desc, height=140)

            st.markdown(
                """
                <div style="background:rgba(0,229,160,0.08);border:1px solid rgba(0,229,160,0.25);
                            border-radius:10px;padding:14px;margin-top:12px;">
                    <b style="color:#00E5A0;">✅ What was done:</b>
                    <ul style="margin:6px 0 0 0;font-size:0.87rem;color:#C8C0BA;">
                        <li>Original audio processed & anti-copyright protected</li>
                        <li>4K AI background composited with Ken Burns motion</li>
                        <li>3 High-CTR Thumbnails generated automatically</li>
                        <li>Viral SEO Hashtags generated for instant posting</li>
                    </ul>
                </div>
                """,
                unsafe_allow_html=True,
            )
        else:
            st.info(
                "Paste a video link on the left and click **'Re-Create Unique Reel'** "
                "to preview the result here."
            )
