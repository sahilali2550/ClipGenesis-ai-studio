"""
link_recreator_page.py — Streamlit UI page for 🔗 Link-to-Video Re-Creator.
Allows pasting YouTube Shorts, Facebook Reels, TikTok, or Instagram Reels URLs to recreate 100% unique Reels.
"""

import os
import streamlit as st
from loguru import logger

from app.services import link_recreator
from app.utils import utils


def render_link_recreator_page():
    """Render the 🔗 Link-to-Video Re-Creator page."""
    st.markdown("### 🔗 Universal Link-to-Video Re-Creator")
    st.caption("Paste any YouTube Shorts, Facebook Reel, TikTok, or Instagram Reel link to automatically re-create a 100% unique, copyright-safe Reel video.")

    col_left, col_right = st.columns([1, 1], gap="large")

    with col_left:
        with st.container(border=True):
            st.markdown("#### 📥 Paste Video URL")

            video_url = st.text_input(
                "Video Link / URL",
                placeholder="https://www.youtube.com/shorts/... or https://www.facebook.com/reel/...",
                key="url_input_link",
            )

            supported_platforms = ["YouTube Shorts", "Facebook Reels", "TikTok", "Instagram Reels", "Twitter / X"]
            st.caption("Supported: " + " • ".join(supported_platforms))

        with st.container(border=True):
            st.markdown("#### ⚙️ Reel Re-Creation Settings")

            bg_theme = st.selectbox(
                "Background Video Theme",
                options=[
                    "kaaba", "mosque", "quran", "rain", "nature", "galaxy", "driving"
                ],
                format_func=lambda x: {
                    "kaaba":   "🕋 Kaaba / Mecca (Islamic — No People)",
                    "mosque":  "🕌 Mosque Interior Architecture",
                    "quran":   "📖 Quran / Islamic Calligraphy",
                    "rain":    "🌧️ Rain & Storm ASMR",
                    "nature":  "🌿 Nature & Mountain Aerial",
                    "galaxy":  "✨ Galaxy & Stars",
                    "driving": "🚗 Driving POV / Road",
                }.get(x, x),
                key="url_bg_theme",
            )

            aspect = st.selectbox(
                "Video Aspect Ratio",
                options=["portrait", "landscape"],
                format_func=lambda x: "📱 Shorts / Reels (9:16)" if x == "portrait" else "🖥️ YouTube Long (16:9)",
                key="url_aspect",
            )

            custom_sub_text = st.text_area(
                "Custom Subtitles / Caption Text (Optional)",
                placeholder="Enter custom subtitle lines to overlay, or leave blank to use video title.",
                height=90,
                key="url_custom_sub_text",
            )

        with st.container(border=True):
            st.markdown("#### 🏷️ Channel Watermark Logo (Optional)")
            logo_file = st.file_uploader(
                "Upload Watermark PNG",
                type=["png", "jpg", "jpeg"],
                key="url_logo_upload",
            )

            logo_path = ""
            if logo_file is not None:
                temp_logo_dir = os.path.join(utils.root_dir(), "storage", "logos")
                os.makedirs(temp_logo_dir, exist_ok=True)
                logo_path = os.path.join(temp_logo_dir, logo_file.name)
                with open(logo_path, "wb") as f:
                    f.write(logo_file.getbuffer())
                st.success(f"🏷️ Logo Loaded: **{logo_file.name}**")

        if st.button("🚀 Re-Create Unique Reel", type="primary", use_container_width=True):
            if not video_url.strip():
                st.error("⚠️ Please paste a valid video URL link first!")
            else:
                with st.spinner("⏳ Downloading media & re-creating Reel video..."):
                    try:
                        out_path = link_recreator.recreate_video_from_url(
                            url=video_url.strip(),
                            custom_subtitle_text=custom_sub_text,
                            background_theme=bg_theme,
                            aspect_ratio=aspect,
                            logo_path=logo_path,
                        )
                        st.session_state["last_recreated_video"] = out_path
                        st.success("🎉 Unique Reel Video re-created successfully!")
                    except Exception as ex:
                        logger.error(f"Failed to recreate video from URL: {ex}")
                        st.error(f"Generation Error: {ex}")

    with col_right:
        st.markdown("### 🎬 Re-Created Output & Player")

        if "last_recreated_video" in st.session_state and os.path.exists(st.session_state["last_recreated_video"]):
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

            st.markdown(
                """
                <div style="background: rgba(0,229,160,0.1); border: 1px solid rgba(0,229,160,0.3); border-radius: 10px; padding: 14px; margin-top: 15px;">
                    <b style="color: #00E5A0;">✅ 100% Copyright-Free Re-Creation:</b>
                    <ul style="margin-bottom:0; font-size: 0.88rem; color:#D8CFC8;">
                        <li>Original audio merged with 4K motion visuals</li>
                        <li>YouTube Content ID Safe</li>
                        <li>Facebook & TikTok Commercial Safe</li>
                    </ul>
                </div>
                """,
                unsafe_allow_html=True,
            )
        else:
            st.info("Paste a video link on the left panel and click 'Re-Create Unique Reel' to preview the result here.")
