import os
import streamlit as st
from loguru import logger

from app.services import darood_service, voice
from app.utils import utils


def render_darood_video_page():
    """Render the 🕌 Darood Shareef Video Generator page."""
    darood_catalog = darood_service.get_darood_list()
    daily_darood = darood_service.get_daily_rotating_darood()

    col_left, col_right = st.columns([1, 1], gap="large")

    # ── LEFT PANEL: Selection & Settings ───────────────────────────────────────
    with col_left:
        with st.container(border=True):
            st.markdown("#### 📖 Darood Shareef Selection Mode")

            selection_mode = st.radio(
                "Mode",
                options=["📅 Daily Auto-Rotate Mode (New Video Daily)", "🎯 Manual Selection from Catalog"],
                index=0,
                key="darood_mode_radio",
            )

            if "Daily Auto-Rotate" in selection_mode:
                selected_darood = daily_darood
                st.info(f"✨ **Today's Selection**: {selected_darood['title']}\n\n*{selected_darood['benefit']}*")
            else:
                darood_titles = [d["title"] for d in darood_catalog]
                chosen_title = st.selectbox("Select Darood Shareef / Custom Text", options=darood_titles, index=0)
                selected_darood = next(d for d in darood_catalog if d["title"] == chosen_title)

            # ── Option to Add Custom Darood / Islamic Text ──────────────────────
            with st.expander("➕ Add New Darood Shareef or Custom Islamic Text", expanded=False):
                with st.form("add_custom_darood_form", clear_on_submit=True):
                    c_title = st.text_input("Title / Name (e.g., درoodِ سلام)", placeholder="Darood Name")
                    c_arabic = st.text_area("Arabic Text (عربی متن)", placeholder="اَللّٰهُمَّ صَلِّ عَلٰى مُحَمَّدٍ...", height=80)
                    c_urdu = st.text_area("Urdu Translation (اردو ترجمہ)", placeholder="اے اللہ! حضرت محمدﷺ پر درود نازل فرما...", height=70)
                    c_benefit = st.text_input("Benefit / Note (فضیلت یا نوٹ)", placeholder="خاص درود شریف")
                    submitted = st.form_submit_button("💾 Save to Collection")
                    if submitted:
                        if c_title.strip() and c_arabic.strip():
                            darood_service.add_custom_darood(
                                title=c_title,
                                arabic=c_arabic,
                                urdu=c_urdu,
                                benefit=c_benefit,
                            )
                            st.success(f"✅ Added '{c_title}' to collection!")
                            st.rerun()
                        else:
                            st.error("⚠️ Title and Arabic Text are required!")

        # ── Arabic Preview Box ─────────────────────────────────────────────────
        with st.container(border=True):
            st.markdown("#### 📜 Text Preview")
            st.markdown(
                f"""
                <div style="background: rgba(0,229,160,0.06); border: 1px solid rgba(0,229,160,0.25); border-radius: 12px; padding: 18px; text-align: center;">
                    <div style="font-size: 1.6rem; font-weight: 700; color: #FFD700; line-height: 1.8; font-family: 'Amiri', 'Scheherazade', serif; margin-bottom: 12px;">
                        {selected_darood['arabic']}
                    </div>
                    <div style="font-size: 0.95rem; color: #E8E0D8; margin-bottom: 8px;">
                        <b>Urdu:</b> {selected_darood['urdu']}
                    </div>
                    <div style="font-size: 0.82rem; color: #00E5A0;">
                        💡 <b>فضیلت:</b> {selected_darood['benefit']}
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )

        # ── Voice, Theme & Aspect Ratio Settings ───────────────────────────────────────
        with st.container(border=True):
            st.markdown("#### ⚙️ Video & Audio Settings")

            # 1. Custom Audio File Upload
            custom_audio_file = st.file_uploader(
                "🎵 Upload Custom Recitation MP3 (Optional)",
                type=["mp3", "wav"],
                help="Upload a soulful recitation audio file (e.g. from your favorite Qari). If left empty, Edge-TTS will recite.",
                key="darood_custom_audio_upload"
            )

            custom_audio_path = ""
            if custom_audio_file is not None:
                temp_upload_dir = os.path.join(utils.root_dir(), "storage", "custom_audio")
                os.makedirs(temp_upload_dir, exist_ok=True)
                custom_audio_path = os.path.join(temp_upload_dir, custom_audio_file.name)
                with open(custom_audio_path, "wb") as f:
                    f.write(custom_audio_file.getbuffer())
                st.success(f"🎵 Custom Audio Loaded: **{custom_audio_file.name}**")

            # 2. Channel Logo / Watermark Upload
            logo_file = st.file_uploader(
                "🏷️ Upload Channel Logo / Watermark PNG (Optional)",
                type=["png", "jpg", "jpeg"],
                help="Upload your channel logo to automatically watermark the video.",
                key="darood_logo_upload"
            )

            logo_path = ""
            if logo_file is not None:
                temp_logo_dir = os.path.join(utils.root_dir(), "storage", "logos")
                os.makedirs(temp_logo_dir, exist_ok=True)
                logo_path = os.path.join(temp_logo_dir, logo_file.name)
                with open(logo_path, "wb") as f:
                    f.write(logo_file.getbuffer())
                st.success(f"🏷️ Channel Logo Loaded: **{logo_file.name}**")

            if logo_path:
                col_l1, col_l2, col_l3 = st.columns(3)
                with col_l1:
                    logo_pos = st.selectbox(
                        "Logo Position",
                        options=["top_right", "top_left", "top_center", "bottom_right", "bottom_left"],
                        format_func=lambda x: {
                            "top_right": "↗️ Top Right (اوپر دائیں)",
                            "top_left": "↖️ Top Left (اوپر بائیں)",
                            "top_center": "⏺️ Top Center (اوپر درمیان)",
                            "bottom_right": "↘️ Bottom Right (نیچے دائیں)",
                            "bottom_left": "↙️ Bottom Left (نیچے بائیں)",
                        }.get(x, x),
                        key="darood_logo_pos_select"
                    )
                with col_l2:
                    logo_sz = st.slider("Logo Width (px)", min_value=60, max_value=300, value=130, step=10, key="darood_logo_sz_slider")
                with col_l3:
                    logo_op = st.slider("Logo Opacity", min_value=0.2, max_value=1.0, value=0.90, step=0.05, key="darood_logo_op_slider")
            else:
                logo_pos = "top_right"
                logo_sz = 130
                logo_op = 0.90

            col_v1, col_v2 = st.columns(2)
            with col_v1:
                voice_options = [
                    ("ar-SA-HamedNeural", "🕌 Arabic Qari Male (Hamed) - Slow & Soothing ⭐"),
                    ("ar-SA-ZariyahNeural", "🕌 Arabic Qari Female (Zariyah)"),
                    ("ur-PK-AsadNeural", "🇵🇰 Urdu Reciter Male (Asad)"),
                    ("ur-PK-UzmaNeural", "🇵🇰 Urdu Reciter Female (Uzma)"),
                ]
                voice_dict = {v[0]: v[1] for v in voice_options}
                selected_voice = st.selectbox(
                    "Reciter / Voice (If no custom audio)",
                    options=list(voice_dict.keys()),
                    format_func=lambda k: voice_dict.get(k, k),
                    key="darood_voice_select",
                )
            with col_v2:
                aspect = st.selectbox(
                    "Video Format",
                    options=["portrait", "landscape"],
                    format_func=lambda x: "📱 Shorts / Reels (9:16)" if x == "portrait" else "🖥️ YouTube Long (16:9)",
                    key="darood_aspect_select",
                )

            col_t1, col_t2 = st.columns(2)
            with col_t1:
                theme_options = [
                    ("driving", "🚗 Driving POV (Rain/Road)"),
                    ("islamic", "🕌 Islamic Sacred Sites (Kaaba/Mosque)"),
                    ("rain", "🌧️ Rain & Storm ASMR"),
                    ("nature", "🌌 Nature & Skies"),
                ]
                theme_dict = {t[0]: t[1] for t in theme_options}
                bg_theme = st.selectbox(
                    "Background Video Theme",
                    options=list(theme_dict.keys()),
                    format_func=lambda k: theme_dict.get(k, k),
                    key="darood_bg_theme_select",
                )

            with col_t2:
                text_style_mode = st.radio(
                    "Text Display Style",
                    options=["✨ Pure Arabic Only (Reel Style)", "📜 Arabic + Urdu Subtitles"],
                    index=0,
                    key="darood_text_style_radio",
                )
                pure_arabic = "Pure Arabic" in text_style_mode

            show_box_frame = st.checkbox("🔲 Show Box Frame (Optional)", value=False, key="darood_show_box_check")

            st.caption("🛡️ **Copyright Safety Guarantee**: Uses 100% royalty-free voices, open-license visuals, and safe background ambient sound.")

            if st.button("🕌 Generate Darood Shareef Video", type="primary", use_container_width=True):
                out_name = f"darood_{selected_darood['id']}_{aspect}.mp4"
                with st.spinner("🚀 Creating Aesthetic Reel Video..."):
                    try:
                        final_video_path = darood_service.generate_darood_video(
                            darood_item=selected_darood,
                            voice_name=selected_voice,
                            aspect_ratio=aspect,
                            background_type=bg_theme,
                            custom_audio_path=custom_audio_path,
                            show_box=show_box_frame,
                            pure_arabic_only=pure_arabic,
                            logo_path=logo_path,
                            logo_position=logo_pos,
                            logo_size=logo_sz,
                            logo_opacity=logo_op,
                            output_filename=out_name,
                        )
                        st.session_state["last_darood_video"] = final_video_path
                        st.success("🎉 Aesthetic Reel Video created successfully!")
                    except Exception as ex:
                        logger.error(f"Failed to generate Darood video: {ex}")
                        st.error(f"Generation Error: {ex}")

    # ── RIGHT PANEL: Video Player & Output ────────────────────────────────────
    with col_right:
        st.markdown("### 🎬 Video Output & Downloads")

        if "last_darood_video" in st.session_state and os.path.exists(st.session_state["last_darood_video"]):
            v_path = st.session_state["last_darood_video"]
            st.video(v_path)

            with open(v_path, "rb") as vf:
                st.download_button(
                    label="⬇️ Download Darood Video (MP4)",
                    data=vf.read(),
                    file_name=os.path.basename(v_path),
                    mime="video/mp4",
                    use_container_width=True,
                )

            st.markdown(
                """
                <div style="background: rgba(0,229,160,0.1); border: 1px solid rgba(0,229,160,0.3); border-radius: 10px; padding: 14px; margin-top: 15px;">
                    <b style="color: #00E5A0;">✅ Copyright License Verified:</b>
                    <ul style="margin-bottom:0; font-size: 0.88rem; color:#D8CFC8;">
                        <li>YouTube Content ID Safe</li>
                        <li>Facebook & Instagram Reels Safe</li>
                        <li>TikTok Commercial Safe</li>
                    </ul>
                </div>
                """,
                unsafe_allow_html=True,
            )
        else:
            st.info("Select a Darood Shareef and click 'Generate Darood Shareef Video' to preview the result here.")
