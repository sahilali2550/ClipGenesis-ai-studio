import os
import streamlit as st
from loguru import logger

from app.services import voice
from app.services.kokoro_engine import get_kokoro_voice_list, generate_kokoro_tts
from app.utils import utils


def render_voice_studio_page():
    """Render the AI Voice Studio & Dubbing Workspace."""
    tab1, tab2, tab3 = st.tabs([
        "⚡ Fast Audio Generator (Kokoro-82M)",
        "🎧 Audio & Video Dubbing",
        "🎭 Multi-Speaker Podcast Creator",
    ])

    # ── TAB 1: Fast Audio Generator ───────────────────────────────────────────
    with tab1:
        st.markdown("### ⚡ Kokoro-82M High-Speed TTS Tester")
        st.info("💡 Kokoro-82M generates audio in milliseconds using local ONNX execution with 0% cloud delay.")

        col_left, col_right = st.columns([1, 1])

        with col_left:
            kokoro_voices = get_kokoro_voice_list()
            selected_voice = st.selectbox(
                "Select Voice",
                options=kokoro_voices,
                index=0,
                format_func=lambda x: x.split(":")[-1] if ":" in x else x,
            )
            speed = st.slider("Speech Speed", min_value=0.5, max_value=2.0, value=1.0, step=0.1)

            sample_text = st.text_area(
                "Text to Synthesize",
                value="Welcome to ClipGenesis AI Studio! Experience ultra-fast, local voice generation without any cloud dependency.",
                height=150,
            )

            if st.button("🔥 Generate Fast Audio", type="primary", use_container_width=True):
                if not sample_text.strip():
                    st.warning("Please enter some text to generate audio.")
                else:
                    output_dir = os.path.join(utils.root_dir(), "storage", "temp_voice_studio")
                    os.makedirs(output_dir, exist_ok=True)
                    out_path = os.path.join(output_dir, "fast_tts_preview.wav")

                    with st.spinner("Generating audio with Kokoro-82M ONNX..."):
                        sub_maker = generate_kokoro_tts(
                            text=sample_text,
                            voice_id=selected_voice,
                            speed=speed,
                            output_file=out_path,
                        )

                    if os.path.exists(out_path):
                        st.success("✅ Audio generated successfully!")
                        st.session_state["last_fast_audio"] = out_path
                        st.session_state["last_sub_maker"] = sub_maker
                    else:
                        st.error("Failed to generate audio.")

        with col_right:
            st.markdown("#### 🎵 Audio Player & Subtitle Timestamps")
            if "last_fast_audio" in st.session_state and os.path.exists(st.session_state["last_fast_audio"]):
                st.audio(st.session_state["last_fast_audio"])
                
                c_btn1, c_btn2 = st.columns(2)
                with c_btn1:
                    with open(st.session_state["last_fast_audio"], "rb") as f:
                        st.download_button(
                            label="⬇️ Download WAV",
                            data=f.read(),
                            file_name="kokoro_tts_preview.wav",
                            mime="audio/wav",
                            use_container_width=True,
                        )
                with c_btn2:
                    if st.button("✂️ Auto-Trim Silence", use_container_width=True):
                        from app.services.audio_enhancer import audio_enhancer
                        trimmed_path = audio_enhancer.trim_silence(st.session_state["last_fast_audio"])
                        if trimmed_path and os.path.exists(trimmed_path):
                            st.session_state["last_fast_audio"] = trimmed_path
                            st.success("✂️ Dead silence trimmed successfully!")
                            st.rerun()

                sub_m = st.session_state.get("last_sub_maker")
                if sub_m and hasattr(sub_m, "subs") and sub_m.subs:
                    with st.expander("📝 Generated Subtitle Timing Breakdown"):
                        st.json({
                            "word_count": len(sub_m.subs),
                            "sample_words": sub_m.subs[:10],
                        })
            else:
                st.info("Click 'Generate Fast Audio' to preview the result here.")

    # ── TAB 2: Audio & Video Dubbing ──────────────────────────────────────────
    with tab2:
        st.markdown("### 🎧 Audio & Video Re-Voicing / Dubbing")
        st.caption("Upload an existing audio file or video narration, and re-voice it using any AI voice.")

        uploaded_file = st.file_uploader(
            "Upload Audio / Video File",
            type=["mp3", "wav", "m4a", "mp4"],
            help="Upload an audio or video clip to re-voice",
        )

        col_d1, col_d2 = st.columns(2)
        with col_d1:
            dub_target_voice = st.selectbox(
                "Target Voice for Dubbing",
                options=get_kokoro_voice_list() + voice.get_chatterbox_voices(),
                format_func=lambda x: x.split(":")[-1] if ":" in x else x,
                key="dub_voice_select",
            )
        with col_d2:
            dub_speed = st.slider("Target Pacing Rate", 0.8, 1.5, 1.0, 0.05, key="dub_speed_slider")

        if uploaded_file and st.button("🎙️ Process & Dub Clip", type="primary", use_container_width=True):
            temp_input = os.path.join(utils.root_dir(), "storage", "temp_voice_studio", uploaded_file.name)
            os.makedirs(os.path.dirname(temp_input), exist_ok=True)
            with open(temp_input, "wb") as f:
                f.write(uploaded_file.getbuffer())
                
            out_name = f"dubbed_{uploaded_file.name}"
            if not out_name.endswith(".mp4") and not out_name.endswith(".mp3") and not out_name.endswith(".wav"):
                out_name += ".mp4"

            with st.spinner("🚀 Running Auto-Dubbing Pipeline (Whisper -> Voice Synthesis -> Video Assembly)..."):
                try:
                    from app.services import dubbing
                    dubbed_media, srt_file = dubbing.auto_dub_media(
                        input_file=temp_input,
                        target_voice=dub_target_voice,
                        speech_rate=dub_speed,
                        model_size="base",
                        output_filename=out_name,
                    )
                    st.success("🎉 Auto-Dubbing completed successfully!")

                    if dubbed_media.endswith(".mp4"):
                        st.video(dubbed_media)
                        with open(dubbed_media, "rb") as vf:
                            st.download_button(
                                label="🎬 Download Dubbed Video MP4",
                                data=vf.read(),
                                file_name=out_name,
                                mime="video/mp4",
                                use_container_width=True,
                            )
                    else:
                        st.audio(dubbed_media)
                        with open(dubbed_media, "rb") as af:
                            st.download_button(
                                label="🎵 Download Dubbed Audio Track",
                                data=af.read(),
                                file_name=out_name,
                                mime="audio/wav",
                                use_container_width=True,
                            )

                    if os.path.exists(srt_file):
                        with open(srt_file, "r", encoding="utf-8") as sf:
                            st.download_button(
                                label="📝 Download Subtitles (.srt)",
                                data=sf.read(),
                                file_name=os.path.basename(srt_file),
                                mime="text/plain",
                            )

                except Exception as ex:
                    logger.error(f"Auto-Dubbing failed: {ex}")
                    st.error(f"Dubbing Error: {ex}")

    # ── TAB 3: Multi-Speaker Podcast Creator ─────────────────────────────────
    with tab3:
        st.markdown("### 🎭 Multi-Speaker Dialogue & Podcast Generator")
        st.caption("Author multi-character scripts (e.g. Host vs Guest) and generate seamless conversational audio clips.")

        col_p1, col_p2 = st.columns(2)
        with col_p1:
            speaker1_voice = st.selectbox(
                "Speaker 1 Voice (Host)",
                options=get_kokoro_voice_list(),
                index=0,
                format_func=lambda x: f"Host: {x.split(':')[-1]}",
                key="spk1_select",
            )
        with col_p2:
            speaker2_voice = st.selectbox(
                "Speaker 2 Voice (Guest)",
                options=get_kokoro_voice_list(),
                index=min(5, len(get_kokoro_voice_list()) - 1),
                format_func=lambda x: f"Guest: {x.split(':')[-1]}",
                key="spk2_select",
            )

        script_text = st.text_area(
            "Dialogue Script (Use 'Host:' and 'Guest:' prefixes)",
            value="Host: Welcome to the AI Future Podcast! Today we are discussing ultra-fast local voice synthesis.\nGuest: Thanks for having me! Kokoro 82M is truly game-changing for content creators.",
            height=200,
        )

        if st.button("🎬 Generate Multi-Speaker Audio", type="primary", use_container_width=True):
            if not script_text.strip():
                st.warning("Please enter a dialogue script.")
            else:
                out_dir = os.path.join(utils.root_dir(), "storage", "temp_voice_studio")
                os.makedirs(out_dir, exist_ok=True)
                podcast_wav = os.path.join(out_dir, "podcast_dialogue.mp3")

                with st.spinner("Generating multi-speaker conversation..."):
                    result_sub_maker = voice.tts(
                        text=script_text,
                        voice_name=speaker1_voice,
                        voice_rate=1.0,
                        voice_file=podcast_wav,
                        secondary_voice_name=speaker2_voice,
                    )

                if os.path.exists(podcast_wav):
                    st.success("✅ Multi-speaker podcast audio generated!")
                    st.audio(podcast_wav)
                else:
                    st.error("Failed to generate dialogue audio.")
