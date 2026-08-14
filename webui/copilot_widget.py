"""
webui/copilot_widget.py — ClipGenesis AI Copilot Brain UI Popover & Drawer
Renders 9Router Multi-Model Switcher, Real-Time Task Monitor & Interactive AI Chat directly on top of the main screen & sidebar across all 13 Studio Tabs.
"""

import os
import streamlit as st
from app.services import copilot_brain


def _render_copilot_content(current_page_name: str, key_suffix: str = "main"):
    """
    Renders inner content of Copilot Brain (Model Switcher, Monitor, Chat, Action Chips).
    """
    st.markdown(
        """
        <div style="background:linear-gradient(135deg, rgba(0,229,160,0.15) 0%, rgba(0,128,255,0.15) 100%);
                    border:1px solid rgba(0,229,160,0.4);border-radius:12px;padding:12px;margin-bottom:14px;">
            <b style="color:#00E5A0;font-size:1.05rem;">🧠 ClipGenesis AI Copilot Brain</b>
            <p style="margin:4px 0 0 0;font-size:0.83rem;color:#C8C0BA;">
                9Router AI Model Team • Real-Time Task Monitor • Auto-Healer & Script Genius
            </p>
        </div>
        """,
        unsafe_allow_html=True
    )

    # ── 1. 9Router Multi-Model Team Switcher ────────────────────────────
    models_map = copilot_brain.MODEL_TEAM_MAP
    model_keys = list(models_map.keys())
    
    selected_model_idx = st.selectbox(
        "🤖 Select 9Router AI Model Team",
        options=range(len(model_keys)),
        format_func=lambda x: models_map[model_keys[x]][0],
        index=0,
        key=f"copilot_model_select_{key_suffix}"
    )
    selected_model_key = model_keys[selected_model_idx]

    # ── 2. Real-Time Task Monitor & Health Status ───────────────────────
    status = copilot_brain.get_copilot_system_status()
    ninerouter_badge = "🟢 ONLINE (20128)" if status["ninerouter_online"] else "🟡 LOCAL PROXY"
    
    st.markdown(
        f"""
        <div style="background:rgba(14,17,23,0.85);border:1px solid rgba(0,229,160,0.25);
                    border-radius:10px;padding:10px 14px;margin-bottom:12px;font-size:0.83rem;color:#E2E8F0;">
            <b>👁️ Real-Time System & Task Monitor:</b><br/>
            • 9Router Proxy: <span style="color:#00E5A0;font-weight:bold;">{ninerouter_badge}</span><br/>
            • Active Tasks: <span style="color:#38BDF8;font-weight:bold;">{status['active_tasks_count']} Active Render Jobs</span><br/>
            • Active Studio Tab: <span style="color:#F59E0B;font-weight:bold;">{current_page_name}</span>
        </div>
        """,
        unsafe_allow_html=True
    )

    # ── 3. Quick Action Chips ───────────────────────────────────────────
    st.markdown("<b>🪄 Quick AI Assistant Actions:</b>", unsafe_allow_html=True)
    col_c1, col_c2, col_c3 = st.columns(3)
    
    prompt_to_send = ""
    with col_c1:
        if st.button("✍️ Enhance Script", use_container_width=True, key=f"cp_act_script_{key_suffix}"):
            prompt_to_send = "Give me 3 tips to make my video script more engaging and viral."
    with col_c2:
        if st.button("🏷️ Viral Hashtags", use_container_width=True, key=f"cp_act_tags_{key_suffix}"):
            prompt_to_send = "Generate 10 high-CTR hashtags for my current video topic."
    with col_c3:
        if st.button("🎨 Image Style", use_container_width=True, key=f"cp_act_style_{key_suffix}"):
            prompt_to_send = "Recommend the best 9Router image style (3D Pixar, Photorealistic 8K, Cyberpunk) for my topic."

    # ── 4. Chat History & Interactive Input ─────────────────────────────
    if "copilot_chat_history" not in st.session_state:
        st.session_state["copilot_chat_history"] = [
            {"role": "assistant", "content": "👋 سلام! میں ClipGenesis AI Copilot Brain ہوں۔ میں 9Router کے تمام AI ماڈلز کے ساتھ لائیو منسلک ہوں۔ سکرپٹ، آواز، یا ویژول سیٹنگز کے بارے میں کچھ بھی پوچھیں!"}
        ]

    # Display history
    chat_container = st.container(height=240)
    with chat_container:
        for msg in st.session_state["copilot_chat_history"]:
            if msg["role"] == "user":
                st.chat_message("user").write(msg["content"])
            else:
                st.chat_message("assistant").write(msg["content"])

    # Chat Input
    user_input = st.chat_input("Ask AI Copilot anything…", key=f"copilot_chat_input_{key_suffix}")
    
    final_prompt = user_input or prompt_to_send

    if final_prompt:
        st.session_state["copilot_chat_history"].append({"role": "user", "content": final_prompt})
        
        with st.spinner("🧠 Consulting 9Router AI Team…"):
            ans = copilot_brain.query_copilot_brain(
                user_prompt=final_prompt,
                selected_model_key=selected_model_key,
                current_context=current_page_name
            )
            st.session_state["copilot_chat_history"].append({"role": "assistant", "content": ans})
            st.rerun()


def render_copilot_widget(current_page_name: str = "Dashboard"):
    """
    Renders prominent AI Copilot Brain Bar at top of main screen and inside sidebar.
    """
    # ── Main Canvas Top Banner & Popover (100% Prominent on Screen) ─────────
    col_left, col_right = st.columns([3, 1])
    with col_left:
        st.markdown(
            f"""
            <div style="background:linear-gradient(90deg, rgba(0,229,160,0.12) 0%, rgba(0,128,255,0.12) 100%);
                        border:1px solid rgba(0,229,160,0.35);border-radius:10px;padding:8px 16px;margin:8px 0 16px 0;
                        display:flex;align-items:center;justify-between:space-between;">
                <span style="color:#00E5A0;font-weight:700;font-size:0.95rem;">
                    🧠 ClipGenesis AI Copilot Brain Active • 9Router Team Connected • Monitoring Tasks
                </span>
            </div>
            """,
            unsafe_allow_html=True
        )
    with col_right:
        # Streamlit Popover directly on top of main UI!
        with st.popover("💬 Open AI Copilot Brain", use_container_width=True):
            _render_copilot_content(current_page_name, key_suffix="main_popover")

    # Also render inside sidebar for backup
    with st.sidebar.expander("💬 ClipGenesis AI Copilot Brain", expanded=True):
        _render_copilot_content(current_page_name, key_suffix="sidebar")
