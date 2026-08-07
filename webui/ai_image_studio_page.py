"""
ai_image_studio_page.py — Streamlit UI for 🖼️ 9Router AI Image Studio.
Supports Text-to-Image (1-4 images batch), Image-to-Image reference transformation,
1-click Ken Burns motion video conversion, and AI Image History Gallery. 100% Watermark-Free.
"""

import os
import shutil
import streamlit as st
from PIL import Image
from loguru import logger

from app.services import ninerouter_image
from app.utils import utils
from app.models.schema import VideoAspect


AI_IMAGES_DIR = os.path.join(utils.root_dir(), "storage", "ai_images")
os.makedirs(AI_IMAGES_DIR, exist_ok=True)


def _enhance_prompt_llm(user_prompt: str) -> str:
    """Enhance simple prompt or Roman Urdu instruction into a 4K cinematic English image description."""
    try:
        from app.services import llm
        sys_p = (
            "You are a senior AI image prompt engineer. If the user prompt is in Roman Urdu, Urdu, or contains instructions "
            "(e.g., 'moto patlo ki team ka image prompt bana kar do'), translate and convert it into a pure English 4K cinematic image prompt. "
            "Return ONLY the enhanced English prompt string, with no conversational prefix or explanations."
        )
        enhanced = llm.generate_response(user_prompt, system_prompt=sys_p)
        return enhanced.strip() if enhanced else user_prompt
    except Exception:
        return f"{user_prompt}, cinematic golden hour lighting, 4K resolution, ultra-detailed, peaceful ambiance"



def render_ai_image_studio_page():
    """Render the 🖼️ AI Image Studio page."""
    st.markdown("### 🖼️ 9Router AI Image Studio")
    st.caption(
        "Generate **100% Watermark-Free 4K AI Images**, transform reference photos, "
        "and convert any image into a **5-second animated motion video clip** with one click."
    )

    tab_txt2img, tab_img2img, tab_gallery = st.tabs([
        "✍️ Text to Image",
        "🖼️ Image to Image",
        "📂 Gallery & History"
    ])

    # ── SUB-TAB 1: TEXT TO IMAGE ─────────────────────────────────────────────
    with tab_txt2img:
        col_in, col_out = st.columns([1, 1], gap="large")

        with col_in:
            with st.container(border=True):
                st.markdown("#### 📝 Image Prompt & Settings")

                # Preset buttons
                st.markdown("**💡 Quick Presets / پرامپٹ سجیست:**")
                preset_cols = st.columns(3)
                with preset_cols[0]:
                    if st.button("🕌 Mosque Sunset", use_container_width=True):
                        st.session_state["t2i_prompt"] = "Beautiful mosque with golden minarets at sunset, 4k cinematic"
                with preset_cols[1]:
                    if st.button("🕋 Kaaba Mecca", use_container_width=True):
                        st.session_state["t2i_prompt"] = "Kaaba Mecca aerial view golden hour light, peaceful ambiance, 4k"
                with preset_cols[2]:
                    if st.button("📖 Calligraphy", use_container_width=True):
                        st.session_state["t2i_prompt"] = "Peaceful Islamic calligraphy on marble wall, soft lighting, 4k"

                user_prompt = st.text_area(
                    "Prompt / تصویر کا پرامپٹ",
                    value=st.session_state.get("t2i_prompt", "Peaceful mosque dome at golden sunset, 4k cinematic"),
                    height=100,
                    key="t2i_prompt_area"
                )

                if st.button("🪄 Enhance Prompt with AI (پرامپٹ ڈیکوریٹ کریں)", use_container_width=True):
                    with st.spinner("🪄 Enhancing prompt with AI..."):
                        enh = _enhance_prompt_llm(user_prompt)
                        st.session_state["t2i_prompt"] = enh
                        st.rerun()

                st.markdown("---")
                col_cfg1, col_cfg2 = st.columns(2)
                with col_cfg1:
                    aspect = st.selectbox(
                        "Aspect Ratio / سائز",
                        options=["portrait", "landscape", "square"],
                        format_func=lambda x: {
                            "portrait":  "📱 Shorts (9:16)",
                            "landscape": "🖥️ YouTube (16:9)",
                            "square":    "🔲 Square (1:1)",
                        }.get(x, x),
                        key="t2i_aspect"
                    )
                with col_cfg2:
                    num_images = st.selectbox(
                        "Number of Images / تعداد",
                        options=[1, 2, 3, 4],
                        index=0,
                        key="t2i_num_images"
                    )

                st.caption("🛡️ **Watermark Removal Active:** Automatic negative prompt injection filters out logos, text & Gemini watermarks.")

            if st.button("🎨 Generate AI Image(s)", type="primary", use_container_width=True):
                if not user_prompt.strip():
                    st.error("⚠️ Please enter a prompt first!")
                else:
                    generated_list = []
                    progress_bar = st.progress(0, text="🤖 Requesting images from 9Router...")
                    for idx in range(num_images):
                        progress_bar.progress(
                            int((idx / num_images) * 100),
                            text=f"🤖 Generating image {idx + 1}/{num_images} via 9Router..."
                        )
                        raw_p = user_prompt.strip()
                        # Auto-enhance if Roman Urdu instruction detected
                        if any(w in raw_p.lower() for w in ["bana", "chahiey", "banao", "dikhao", "kar do", "ka image", "ki team"]):
                            raw_p = _enhance_prompt_llm(raw_p)

                        clean_prompt = f"{raw_p}, clean unwatermarked, high resolution 4k"
                        img_path = ninerouter_image.generate_9router_image(
                            prompt=clean_prompt,
                            save_dir=AI_IMAGES_DIR,
                        )
                        if img_path and os.path.exists(img_path):
                            generated_list.append(img_path)

                    progress_bar.progress(100, text="✅ Generation complete!")
                    if generated_list:
                        st.session_state["last_studio_images"] = generated_list
                        st.session_state["last_studio_prompt"] = user_prompt
                        st.success(f"🎉 Generated {len(generated_list)} AI Image(s) successfully!")
                    else:
                        st.error("❌ Image generation failed. Please check 9Router Proxy status.")

        with col_out:
            st.markdown("#### 🖼️ Generated Preview")
            img_list = st.session_state.get("last_studio_images", [])

            # Fallback for single image backward compatibility
            if not img_list and "last_studio_image" in st.session_state and os.path.exists(st.session_state["last_studio_image"]):
                img_list = [st.session_state["last_studio_image"]]

            if img_list:
                for img_idx, img_p in enumerate(img_list):
                    if not os.path.exists(img_p):
                        continue
                    with st.container(border=True):
                        st.markdown(f"**Image #{img_idx + 1}**")
                        st.image(img_p, use_container_width=True)

                        c_d1, c_d2 = st.columns(2)
                        with c_d1:
                            with open(img_p, "rb") as f:
                                st.download_button(
                                    "⬇️ Download Image (PNG)",
                                    data=f.read(),
                                    file_name=os.path.basename(img_p),
                                    mime="image/png",
                                    key=f"dl_img_{img_idx}_{os.path.basename(img_p)}",
                                    use_container_width=True
                                )
                        with c_d2:
                            if st.button("🎬 Convert to 5s Ken Burns Video", key=f"btn_kb_{img_idx}_{os.path.basename(img_p)}", use_container_width=True):
                                with st.spinner("🎬 Generating animated Ken Burns motion clip..."):
                                    asp_enum = VideoAspect.portrait if aspect == "portrait" else (VideoAspect.landscape if aspect == "landscape" else VideoAspect.square)
                                    out_dir = os.path.join(utils.root_dir(), "storage", "general_videos")
                                    os.makedirs(out_dir, exist_ok=True)
                                    clip_p = ninerouter_image.image_to_kenburns_clip(
                                        image_path=img_p,
                                        duration=5,
                                        video_aspect=asp_enum,
                                        task_dir=out_dir,
                                    )
                                    if clip_p and os.path.exists(clip_p):
                                        if "studio_clips_dict" not in st.session_state:
                                            st.session_state["studio_clips_dict"] = {}
                                        st.session_state["studio_clips_dict"][img_p] = clip_p
                                        st.success("🎉 Motion video clip generated!")

                        # Video Clip Preview if generated for this image
                        clips_dict = st.session_state.get("studio_clips_dict", {})
                        clip_for_img = clips_dict.get(img_p, "")
                        if clip_for_img and os.path.exists(clip_for_img):
                            st.markdown("---")
                            st.markdown(f"##### 🎬 5s Motion Video Clip Preview")
                            st.video(clip_for_img)
                            with open(clip_for_img, "rb") as vf:
                                st.download_button(
                                    "⬇️ Download Motion Video (MP4)",
                                    data=vf.read(),
                                    file_name=os.path.basename(clip_for_img),
                                    mime="video/mp4",
                                    key=f"dl_vid_{img_idx}_{os.path.basename(clip_for_img)}",
                                    use_container_width=True
                                )
            else:
                st.info("Enter a prompt on the left and click **'Generate AI Image(s)'** to view result here.")

    # ── SUB-TAB 2: IMAGE TO IMAGE ─────────────────────────────────────────────
    with tab_img2img:
        ci2_in, ci2_out = st.columns([1, 1], gap="large")

        with ci2_in:
            with st.container(border=True):
                st.markdown("#### 🖼️ Reference Image & Settings")
                uploaded_file = st.file_uploader(
                    "Upload Reference Image / ریفرنس تصویر اپ لوڈ کریں",
                    type=["png", "jpg", "jpeg", "webp"],
                    key="i2i_file"
                )

                if uploaded_file:
                    st.image(uploaded_file, caption="Reference Photo", width=250)

                i2i_prompt = st.text_area(
                    "Transformation Prompt / کس طرح تبدیل کرنا ہے؟",
                    value="Transform into 4k golden hour cinematic painting, detailed peaceful mosque background",
                    height=80,
                    key="i2i_prompt"
                )

                strength = st.slider(
                    "Transformation Strength (تخلیقی آزادی)",
                    min_value=0.1,
                    max_value=0.9,
                    value=0.6,
                    step=0.05,
                    help="Low % stays close to reference photo; High % gives AI more creative freedom."
                )

            if st.button("🚀 Transform Image (Image-to-Image)", type="primary", use_container_width=True):
                if not uploaded_file:
                    st.error("⚠️ Please upload a reference image first!")
                elif not i2i_prompt.strip():
                    st.error("⚠️ Please enter a transformation prompt!")
                else:
                    with st.spinner("🤖 Transforming reference image via 9Router..."):
                        img_bytes = uploaded_file.getvalue()
                        clean_p = f"{i2i_prompt.strip()}, clean unwatermarked, 4k resolution"
                        res_p = ninerouter_image.generate_9router_img2img(
                            image_bytes=img_bytes,
                            prompt=clean_p,
                            strength=strength,
                            save_dir=AI_IMAGES_DIR,
                        )
                        if res_p and os.path.exists(res_p):
                            st.session_state["last_i2i_image"] = res_p
                            st.success("🎉 Transformed image ready!")
                        else:
                            st.error("❌ Image-to-Image transformation failed.")

        with ci2_out:
            st.markdown("#### ✨ Transformed Output")
            if "last_i2i_image" in st.session_state and os.path.exists(st.session_state["last_i2i_image"]):
                img_i2i = st.session_state["last_i2i_image"]
                st.image(img_i2i, use_container_width=True)

                with open(img_i2i, "rb") as f:
                    st.download_button(
                        "⬇️ Download Transformed Image (PNG)",
                        data=f.read(),
                        file_name=os.path.basename(img_i2i),
                        mime="image/png",
                        use_container_width=True
                    )
            else:
                st.info("Upload an image on the left and click **'Transform Image'** to view result here.")

    # ── SUB-TAB 3: GALLERY & HISTORY ──────────────────────────────────────────
    with tab_gallery:
        st.markdown("#### 📂 AI Image Gallery & History")
        if os.path.exists(AI_IMAGES_DIR):
            files = [f for f in os.listdir(AI_IMAGES_DIR) if f.lower().endswith(('.png', '.jpg', '.jpeg'))]
            files.sort(key=lambda x: os.path.getmtime(os.path.join(AI_IMAGES_DIR, x)), reverse=True)

            if files:
                st.caption(f"Showing **{len(files)}** saved AI images in `storage/ai_images`:")
                cols = st.columns(3)
                for idx, fname in enumerate(files):
                    fp = os.path.join(AI_IMAGES_DIR, fname)
                    with cols[idx % 3]:
                        st.image(fp, use_container_width=True, caption=fname)
                        with open(fp, "rb") as vf:
                            st.download_button(
                                f"⬇️ Save",
                                data=vf.read(),
                                file_name=fname,
                                mime="image/png",
                                key=f"dl_gal_{fname}",
                                use_container_width=True
                            )
            else:
                st.info("No saved AI images found in gallery yet. Generate images in Text-to-Image or Image-to-Image tabs.")
        else:
            st.info("Gallery directory is empty.")
