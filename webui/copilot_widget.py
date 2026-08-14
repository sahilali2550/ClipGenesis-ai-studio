"""
webui/copilot_widget.py — ClipGenesis Master Copilot Brain & Autonomous 10-Agent Swarm UI Drawer
Renders Power-Cut Checkpoint Auto-Resume Banner, 10-Bot Team Live Progress, 9Router Multi-Model Switcher,
Interactive Chat, AND Autonomous Task Execution when commands like "Surah 112 ki video bana do" are issued.
"""

import os
import re
import json
import time
import streamlit as st
from app.services import copilot_brain, agent_swarm, task as tm, quran_api


def _render_bot_status_plain(sys_status: dict):
    """Renders 10-bot team status as plain markdown."""
    bots = sys_status.get("swarm_bots", [])
    lines = []
    for bot in bots:
        lines.append(f"• {bot['name']}: **{bot['status']}**")
    st.markdown("\n".join(lines))


def _execute_autonomous_action(action: dict):
    """
    Executes real video generation task directly when Copilot Brain receives a command!
    """
    action_type = action.get("type")
    
    if action_type == "quran_video":
        surah_num = action.get("surah", 112)
        from_ayah = action.get("from_ayah", 1)
        to_ayah = action.get("to_ayah", 4)
        surah_info = quran_api.get_surah_info(surah_num)
        surah_name = surah_info.get("name", f"Surah {surah_num}")

        st.info(f"🚀 **10-Agent Swarm Action:** Generating Quran Video for Surah {surah_name} (Ayahs {from_ayah}–{to_ayah})…")
        
        prog_bar = st.progress(0.1, text="⏳ 10-Agent Swarm rendering Quran Video...")
        
        task_id = f"copilot_quran_{int(time.time())}"
        from app.services import quran_task
        
        def prog_cb(val, msg=""):
            prog_bar.progress(min(val, 1.0), text=msg or "Processing...")

        try:
            video_path = quran_task.generate_quran_video(
                task_id=task_id,
                surah=surah_num,
                from_ayah=from_ayah,
                to_ayah=to_ayah,
                reciter_name="Yasser Al-Dossari",
                translation_edition="ur.jalandhry",
                video_source="hybrid",
                video_aspect="9:16",
                progress_cb=prog_cb
            )

            if video_path and os.path.exists(video_path):
                prog_bar.progress(1.0, text="✅ Video Generation Complete!")
                st.success(f"🎉 **Video Ready!** Surah {surah_name} ({from_ayah}–{to_ayah})")
                st.video(video_path)
                st.session_state["copilot_last_rendered_video"] = video_path
            else:
                prog_bar.progress(0.0, text="❌ Error")
                st.error("❌ Video rendering error. Check logs for details.")
        except Exception as ex:
            prog_bar.progress(0.0, text="❌ Error")
            st.error(f"❌ Swarm Execution Error: {ex}")

    elif action_type == "general_video":
        topic = action.get("topic", "General Video")
        st.info(f"🚀 **10-Agent Swarm Action:** Generating Reel for topic '{topic}'…")
        
        prog_bar = st.progress(0.1, text=f"⏳ 10-Agent Swarm generating script & scenes for '{topic}'...")
        task_id = f"copilot_gen_{int(time.time())}"

        try:
            # Run Swarm Orchestrator
            swarm_res = agent_swarm.swarm_orchestrator.execute_autopilot_swarm(
                task_id=task_id,
                topic=topic
            )
            prog_bar.progress(0.6, text="🎨 Rendering scenes & audio...")
            
            # Start Video Task
            from app.models.schema import VideoParams
            params = VideoParams(
                video_subject=topic,
                video_script=swarm_res["script_res"].get("script", ""),
                video_terms=swarm_res["script_res"].get("terms", [topic]),
                video_aspect="9:16",
                video_source="hybrid",
                voice_name="ur-PK-UzmaNeural"
            )
            
            res = tm.start(task_id=task_id, params=params)
            prog_bar.progress(1.0, text="✅ Swarm Execution Complete!")
            st.success(f"🎉 **Reel Ready!** Topic: {topic}")
        except Exception as ex:
            prog_bar.progress(0.0, text="❌ Error")
            st.error(f"❌ Swarm Execution Error: {ex}")


def _render_copilot_content(current_page_name: str, key_suffix: str = "main"):
    """
    Renders inner content of Copilot Brain with direct autonomous action execution.
    """
    sys_status = copilot_brain.get_copilot_system_status()
    nr_status = "🟢 Connected" if sys_status.get("ninerouter_online") else "🔴 Offline"

    st.markdown(
        f"""
        <div style="background:linear-gradient(135deg,rgba(0,229,160,0.15),rgba(0,128,255,0.15));
                    border:1px solid rgba(0,229,160,0.4);border-radius:10px;padding:10px;margin-bottom:10px;">
            <b style="color:#00E5A0;">🧠 ClipGenesis AI Copilot Brain (CEO Agent)</b><br/>
            <span style="font-size:0.78rem;color:#C8C0BA;">
                9Router: {nr_status} &nbsp;|&nbsp; 10-Agent Swarm Autopilot &nbsp;|&nbsp; Power-Cut Checkpoint Protection
            </span>
        </div>
        """,
        unsafe_allow_html=True
    )

    # ── 1. Power-Cut Recovery Checkpoint Detection ──────────────────────
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
            with st.spinner("⏳ Auto-resuming rendering from checkpoint…"):
                try:
                    res_path = tm.resume_task(top_cp["task_id"])
                    st.success(f"🎉 Task auto-resumed: {res_path}")
                    copilot_brain.clear_checkpoint(top_cp["task_id"])
                    st.rerun()
                except Exception as ex:
                    st.error(f"❌ Auto-resume error: {ex}")

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

    # ── 3. 10-Bot Swarm Status ───────────────────────────────────────────
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

    # ── 5. Chat History & Execution ──────────────────────────────────────
    if "copilot_chat_history" not in st.session_state:
        saved_mem = copilot_brain.load_brain_memory()
        st.session_state["copilot_chat_history"] = saved_mem.get("chat_history", [])

    # Display history (cleaning action markers from display)
    chat_container = st.container(height=240)
    pending_action = None

    with chat_container:
        for msg in st.session_state["copilot_chat_history"]:
            content = msg["content"]
            # Extract action marker if present
            m_act = re.search(r"\[AUTONOMOUS_ACTION:\s*(\{.*?\})\]", content)
            display_text = re.sub(r"\[AUTONOMOUS_ACTION:\s*\{.*?\}\]", "", content).strip()
            
            if msg["role"] == "user":
                st.chat_message("user").write(display_text)
            else:
                st.chat_message("assistant").write(display_text)
                if m_act:
                    try:
                        pending_action = json.loads(m_act.group(1))
                    except Exception:
                        pass

    # Render pending autonomous action if just issued
    if pending_action:
        _execute_autonomous_action(pending_action)

    # ── 6. Chat Input ────────────────────────────────────────────────────
    user_input = st.chat_input(
        f"Ask AI Copilot anything or type 'Surah 112 ki video bana do'…",
        key=f"copilot_input_{key_suffix}"
    )
    final_prompt = user_input or prompt_to_send

    if final_prompt:
        st.session_state["copilot_chat_history"].append({"role": "user", "content": final_prompt})
        with st.spinner("🧠 10-Agent Swarm Processing Command…"):
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
    Renders AI Copilot Brain bar on top of main canvas and popover drawer.
    """
    sys_status = copilot_brain.get_copilot_system_status()
    nr_online = sys_status.get("ninerouter_online", False)
    recovery = sys_status.get("powercut_recovery_available", False)

    badge = "🛡️ Power-Cut Recovery Active" if recovery else ("🟢 10-Agent Swarm Ready" if nr_online else "🔴 9Router Offline")

    # Top Banner & Popover
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
        with st.popover("💬 AI Copilot Autopilot", use_container_width=True):
            _render_copilot_content(current_page_name, key_suffix="popover")

    # Sidebar Simple Status
    st.sidebar.markdown("---")
    st.sidebar.markdown(
        f"**🧠 AI Copilot Autopilot**\n\n"
        f"9Router: {'🟢 Online' if nr_online else '🔴 Offline'}\n\n"
        f"Swarm: 10 Autonomous Agents\n\n"
        f"{'🛡️ Power-Cut Recovery Pending' if recovery else '✅ Autopilot Ready'}"
    )
