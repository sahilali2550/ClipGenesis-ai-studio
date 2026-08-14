"""
webui/copilot_widget.py — ClipGenesis Master Copilot Brain & 10-Agent Swarm UI Drawer
Fixed: Removed nested expanders, fixed duplicate chat_input keys, sidebar uses plain markdown.
"""

import streamlit as st
from app.services import copilot_brain


def _render_bot_status_plain(sys_status: dict):
    """Renders 10-bot team status as plain markdown (no expander nesting)."""
    bots = sys_status.get("swarm_bots", [])
    lines = []
    for bot in bots:
        lines.append(f"• {bot['name']}: **{bot['status']}**")
    st.markdown("\n".join(lines))


def _render_copilot_content(current_page_name: str, key_suffix: str = "main"):
    """
    Renders inner content of Copilot Brain.
    NOTE: No st.expander used here — caller controls container to avoid nesting.
    """
    # ── Header ──────────────────────────────────────────────────────────
    sys_status = copilot_brain.get_copilot_system_status()
    nr_status = "🟢 Connected" if sys_status.get("ninerouter_online") else "🔴 Offline"

    st.markdown(
        f"""
        <div style="background:linear-gradient(135deg,rgba(0,229,160,0.15),rgba(0,128,255,0.15));
                    border:1px solid rgba(0,229,160,0.4);border-radius:10px;padding:10px;margin-bottom:10px;">
            <b style="color:#00E5A0;">🧠 ClipGenesis AI Copilot Brain (CEO Agent)</b><br/>
            <span style="font-size:0.78rem;color:#C8C0BA;">
                9Router: {nr_status} &nbsp;|&nbsp; 10-Agent Swarm Active &nbsp;|&nbsp; Power-Cut Checkpoint Protection
            </span>
        </div>
        """,
        unsafe_allow_html=True
    )

    # ── 1. Power-Cut Recovery ────────────────────────────────────────────
    unfinished = sys_status.get("unfinished_checkpoints", [])
    if unfinished:
        top_cp = unfinished[0]
        st.warning(
            f"🛡️ **Power-Cut Recovery:** Task `{top_cp['task_id'][:8]}` was interrupted at "
            f"**{top_cp['stage']}** ({top_cp.get('readable_time', '')})"
        )
        if st.button(
            f"⚡ 1-Click Resume Task ({top_cp['task_id'][:8]})",
            type="primary",
            use_container_width=True,
            key=f"res_cp_{key_suffix}"
        ):
            st.info("⏳ Auto-resume feature available after full rendering engine hook is connected.")
            copilot_brain.clear_checkpoint(top_cp["task_id"])

    # ── 2. 9Router Model Switcher ────────────────────────────────────────
    models_map = copilot_brain.MODEL_TEAM_MAP
    model_keys = list(models_map.keys())
    selected_model_idx = st.selectbox(
        "🤖 9Router AI Model Team",
        options=range(len(model_keys)),
        format_func=lambda x: models_map[model_keys[x]][0],
        index=0,
        key=f"copilot_model_{key_suffix}"
    )
    selected_model_key = model_keys[selected_model_idx]

    # ── 3. 10-Bot Swarm Status (plain — NO nested expander) ──────────────
    st.markdown("**🤖 10-Agent Swarm Status:**")
    _render_bot_status_plain(sys_status)
    st.divider()

    # ── 4. Quick Action Chips ────────────────────────────────────────────
    st.markdown("**🪄 Quick Actions:**")
    col1, col2, col3 = st.columns(3)
    prompt_to_send = ""
    with col1:
        if st.button("✍️ Script Tips", use_container_width=True, key=f"act_script_{key_suffix}"):
            prompt_to_send = "Give me 3 tips to make my video script more engaging and viral."
    with col2:
        if st.button("🏷️ Hashtags", use_container_width=True, key=f"act_tags_{key_suffix}"):
            prompt_to_send = "Generate 10 high-CTR viral hashtags for my current video topic."
    with col3:
        if st.button("🎨 Image Style", use_container_width=True, key=f"act_style_{key_suffix}"):
            prompt_to_send = "Recommend the best 9Router AI image style for my topic: 3D Pixar, Photorealistic 8K, or Cyberpunk?"

    # ── 5. Chat History ──────────────────────────────────────────────────
    if "copilot_chat_history" not in st.session_state:
        saved_mem = copilot_brain.load_brain_memory()
        st.session_state["copilot_chat_history"] = saved_mem.get("chat_history", [])

    chat_container = st.container(height=220)
    with chat_container:
        for msg in st.session_state["copilot_chat_history"]:
            if msg["role"] == "user":
                st.chat_message("user").write(msg["content"])
            else:
                st.chat_message("assistant").write(msg["content"])

    # ── 6. Chat Input (only ONE per page — use key_suffix to differentiate) ──
    user_input = st.chat_input(
        f"Ask AI Copilot anything… ({current_page_name})",
        key=f"copilot_input_{key_suffix}"
    )
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
        mem = copilot_brain.load_brain_memory()
        mem["chat_history"] = st.session_state["copilot_chat_history"]
        copilot_brain.save_brain_memory(mem)
        st.rerun()


def render_copilot_widget(current_page_name: str = "Dashboard"):
    """
    Renders AI Copilot Brain:
    - Top banner strip on main canvas (always visible)
    - Popover drawer on main canvas (no sidebar nesting issue)
    - Sidebar: plain status text only (NO expander nesting)
    """
    sys_status = copilot_brain.get_copilot_system_status()
    nr_online = sys_status.get("ninerouter_online", False)
    recovery = sys_status.get("powercut_recovery_available", False)

    badge = "🛡️ Power-Cut Recovery Active" if recovery else ("🟢 9Router Live" if nr_online else "🔴 9Router Offline")

    # ── Main Canvas Banner + Popover ────────────────────────────────────
    col_left, col_right = st.columns([4, 1])
    with col_left:
        st.markdown(
            f"""
            <div style="background:linear-gradient(90deg,rgba(0,229,160,0.10),rgba(0,128,255,0.10));
                        border:1px solid rgba(0,229,160,0.30);border-radius:8px;
                        padding:7px 14px;margin:2px 0 10px 0;">
                <span style="color:#00E5A0;font-weight:700;font-size:0.9rem;">
                    🧠 ClipGenesis AI Copilot Brain (CEO Agent) &nbsp;•&nbsp; {badge}
                </span>
            </div>
            """,
            unsafe_allow_html=True
        )
    with col_right:
        with st.popover("💬 AI Copilot", use_container_width=True):
            _render_copilot_content(current_page_name, key_suffix="popover")

    # ── Sidebar: Simple status ONLY — NO expander, NO nesting ───────────
    st.sidebar.markdown("---")
    st.sidebar.markdown(
        f"**🧠 AI Copilot Brain**\n\n"
        f"9Router: {'🟢 Online' if nr_online else '🔴 Offline'}\n\n"
        f"Swarm: 10 Agents Active\n\n"
        f"{'🛡️ Power-Cut Recovery Pending' if recovery else '✅ All Systems Normal'}"
    )
