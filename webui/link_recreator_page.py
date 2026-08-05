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
            st.markdown("#### ⚙️ Background Settings")

            bg_theme = st.selectbox(
                "Background Video Theme",
                options=["kaaba", "mosque", "quran", "rain", "nature", "galaxy", "driving"],
                format_func=lambda x: {
                    "kaaba":   "🕋 Kaaba / Mecca  (Islamic — architecture only)",
                    "mosque":  "🕌 Mosque Interior  (Islamic — architecture only)",
                    "quran":   "📖 Islamic Calligraphy / Masjid",
                    "rain":    "🌧️ Rain & Storm ASMR",
                    "nature":  "🌿 Mountain & Nature Aerial",
                    "galaxy":  "✨ Galaxy & Stars",
                    "driving": "🚗 Driving POV / Road",
                }.get(x, x),
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

        # ── Generate Button ───────────────────────────────────────────────────
        if st.button("🚀 Re-Create Unique Reel", type="primary", use_container_width=True):
            if not video_url.strip():
                st.error("⚠️ Please paste a valid video URL first!")
            else:
                with st.spinner("⏳ Downloading audio & compositing background video…"):
                    try:
                        out_path = link_recreator.recreate_video_from_url(
                            url=video_url.strip(),
                            background_theme=bg_theme,
                            aspect_ratio=aspect,
                        )
                        st.session_state["last_recreated_video"] = out_path
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

            st.markdown(
                """
                <div style="background:rgba(0,229,160,0.08);border:1px solid rgba(0,229,160,0.25);
                            border-radius:10px;padding:14px;margin-top:12px;">
                    <b style="color:#00E5A0;">✅ What was done:</b>
                    <ul style="margin:6px 0 0 0;font-size:0.87rem;color:#C8C0BA;">
                        <li>Original audio downloaded completely</li>
                        <li>Fresh 4K background composited (Islamic-safe — architecture only)</li>
                        <li>No text, no subtitles, no watermark</li>
                        <li>Ready for Facebook / YouTube / TikTok upload</li>
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
