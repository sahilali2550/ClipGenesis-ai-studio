"""
webui/copilot_widget.py — ClipGenesis Master Copilot Brain & 10-Agent Swarm UI Drawer
Renders Power-Cut Checkpoint Auto-Resume Banner, 10-Bot Team Live Progress, 9Router Multi-Model Switcher, and Interactive Chat.
"""

import os
import streamlit as st
from app.services import copilot_brain, agent_swarm, task as tm


def _render_copilot_content(current_page_name: str, key_suffix: str = "main"):
    """
    Renders inner content of Copilot Brain (Model Switcher, 10-Bot Swarm Monitor, Chat, Action Chips).
    """
    st.markdown(
        """
        <div style="background:linear-gradient(135deg, rgba(0,229,160,0.15) 0%, rgba(0,128,255,0.15) 100%);
                    border:1px solid rgba(0,229,160,0.4);border-radius:12px;padding:12px;margin-bottom:14px;">
            <b style="color:#00E5A0;font-size:1.08rem;">🧠 ClipGenesis AI Copilot Brain (CEO Agent)</b>
            <p style="margin:4px 0 0 0;font-size:0.83rem;color:#C8C0BA;">
                10-Agent Swarm • Power-Cut Checkpoint Protection • 9Router Multi-Model Team
            </p>
        </div>
        """,
        unsafe_allow_html=True
    )

    # ── 1. Power-Cut Recovery Checkpoint Detection ──────────────────────
    sys_status = copilot_brain.get_copilot_system_status()
    unfinished = sys_status.get("unfinished_checkpoints", [])
    
    if unfinished:
        top_cp = unfinished[0]
        st.markdown(
            f"""
            <div style="background:rgba(239,68,68,0.12);border:1px solid rgba(239,68,68,0.35);
                        border-radius:10px;padding:12px;margin-bottom:12px;">
                <b style="color:#EF4444;">🛡️ Power-Cut Recovery: Unfinished Task Detected!</b><br/>
                <span style="font-size:0.82rem;color:#E2E8F0;">
                    Task <code>{top_cp['task_id'][:8]}</code> was interrupted during <b>{top_cp['stage']}</b> at {top_cp.get('readable_time', '')}.
                </span>
            </div>
            """,
            unsafe_allow_html=True
        )
        if st.button(f"⚡ 1-Click Resume Task ({top_cp['task_id'][:8]})", type="primary", use_container_width=True, key=f"res_cp_{key_suffix}"):
            with st.spinner("⏳ Resuming rendering from saved checkpoint…"):
                try:
                    res_path = tm.resume_task(top_cp['task_id'])
                    st.success(f"🎉 Task auto-resumed successfully: {res_path}")
                    copilot_brain.clear_checkpoint(top_cp['task_id'])
                    st.rerun()
                except Exception as ex:
                    st.error(f"❌ Auto-resume error: {ex}")

    # ── 2. 9Router Multi-Model Team Switcher ────────────────────────────
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

    # ── 3. 10-Agent Swarm Live Status Dashboard ─────────────────────────
    with st.expander("🤖 10-Agent Swarm Team Status (Live)", expanded=False):
        bots = sys_status.get("swarm_bots", [])
        b_cols = st.columns(2)
        for idx, bot in enumerate(bots):
            with b_cols[idx % 2]:
                st.markdown(f"<span style='font-size:0.8rem;color:#C8C0BA;'>• {bot['name']}: <b style='color:#00E5A0;'>{bot['status']}</b></span>", unsafe_allow_html=True)

    # ── 4. Quick Action Chips ───────────────────────────────────────────
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

    # ── 5. Chat History & Interactive Input ─────────────────────────────
    if "copilot_chat_history" not in st.session_state:
        saved_mem = copilot_brain.load_brain_memory()
        st.session_state["copilot_chat_history"] = saved_mem.get("chat_history", [])

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
            
            # Persist to disk memory
            mem = copilot_brain.load_brain_memory()
            mem["chat_history"] = st.session_state["copilot_chat_history"]
            copilot_brain.save_brain_memory(mem)
            st.rerun()


def render_copilot_widget(current_page_name: str = "Dashboard"):
    """
    Renders prominent AI Copilot Brain Bar at top of main screen and inside sidebar.
    """
    # ── Main Canvas Top Banner & Popover (100% Prominent on Screen) ─────────
    col_left, col_right = st.columns([3, 1])
    with col_left:
        sys_status = copilot_brain.get_copilot_system_status()
        badge_text = "🛡️ Power-Cut Recovery Active" if sys_status.get("powercut_recovery_available") else "🟢 10-Agent Swarm Ready"
        st.markdown(
            f"""
            <div style="background:linear-gradient(90deg, rgba(0,229,160,0.12) 0%, rgba(0,128,255,0.12) 100%);
                        border:1px solid rgba(0,229,160,0.35);border-radius:10px;padding:8px 16px;margin:4px 0 14px 0;
                        display:flex;align-items:center;justify-between:space-between;">
                <span style="color:#00E5A0;font-weight:700;font-size:0.95rem;">
                    🧠 ClipGenesis AI Copilot Brain (CEO Agent) • {badge_text} • 9Router Team Connected
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
    with st.sidebar.expander("💬 ClipGenesis AI Copilot Brain", expanded=False):
        _render_copilot_content(current_page_name, key_suffix="sidebar")
