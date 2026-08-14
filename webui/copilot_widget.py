"""
webui/copilot_widget.py — ClipGenesis AI Copilot Brain UI Drawer & Floating Widget
Renders 9Router Multi-Model Switcher, Real-Time Task Monitor & Interactive AI Chat across all 13 Studio Tabs.
"""

import os
import streamlit as st
from app.services import copilot_brain


def render_copilot_widget(current_page_name: str = "Dashboard"):
    """
    Renders the Floating AI Copilot Brain Widget on Streamlit UI.
    """
    # Inject Custom Floating Glassmorphic CSS for Copilot Widget
    st.markdown(
        """
        <style>
        .copilot-floating-badge {
            background: linear-gradient(135deg, #00E5A0 0%, #0080FF 100%);
            color: #0E1117;
            padding: 8px 16px;
            border-radius: 20px;
            font-weight: 700;
            font-size: 0.88rem;
            display: inline-flex;
            align-items: center;
            gap: 8px;
            box-shadow: 0 4px 15px rgba(0,229,160,0.3);
            margin-bottom: 12px;
        }
        .copilot-status-box {
            background: rgba(14, 17, 23, 0.75);
            border: 1px solid rgba(0, 229, 160, 0.25);
            border-radius: 12px;
            padding: 10px 14px;
            margin-bottom: 12px;
            font-size: 0.82rem;
            color: #E2E8F0;
        }
        </style>
        """,
        unsafe_allow_html=True
    )

    # Copilot Container Widget
    with st.sidebar.expander("💬 ClipGenesis AI Copilot Brain", expanded=False):
        st.markdown(
            '<div class="copilot-floating-badge">🧠 AI Copilot & Task Monitor</div>',
            unsafe_allow_html=True
        )

        # ── 1. 9Router Multi-Model Team Switcher ────────────────────────────
        models_map = copilot_brain.MODEL_TEAM_MAP
        model_keys = list(models_map.keys())
        
        selected_model_idx = st.selectbox(
            "🤖 9Router AI Model Team",
            options=range(len(model_keys)),
            format_func=lambda x: models_map[model_keys[x]][0],
            index=0,
            key="copilot_model_select"
        )
        selected_model_key = model_keys[selected_model_idx]

        # ── 2. Real-Time Task Monitor & Health Status ───────────────────────
        status = copilot_brain.get_copilot_system_status()
        ninerouter_badge = "🟢 ONLINE (20128)" if status["ninerouter_online"] else "🟡 LOCAL PROXY"
        
        st.markdown(
            f"""
            <div class="copilot-status-box">
                <b>👁️ Real-Time System Status:</b><br/>
                • 9Router Proxy: <span style="color:#00E5A0;">{ninerouter_badge}</span><br/>
                • Active Task Jobs: <span style="color:#38BDF8;">{status['active_tasks_count']}</span><br/>
                • Current Tab: <span style="color:#F59E0B;">{current_page_name}</span>
            </div>
            """,
            unsafe_allow_html=True
        )

        # ── 3. Quick Action Chips ───────────────────────────────────────────
        st.markdown("<b>🪄 Quick AI Actions:</b>", unsafe_allow_html=True)
        col_c1, col_c2 = st.columns(2)
        
        prompt_to_send = ""
        with col_c1:
            if st.button("✍️ Enhance Script", use_container_width=True, key="cp_act_script"):
                prompt_to_send = "Give me 3 tips to make my video script more engaging and viral."
        with col_c2:
            if st.button("🏷️ Viral Hashtags", use_container_width=True, key="cp_act_tags"):
                prompt_to_send = "Generate 10 high-CTR hashtags for my current video topic."

        # ── 4. Chat History & Input ─────────────────────────────────────────
        if "copilot_chat_history" not in st.session_state:
            st.session_state["copilot_chat_history"] = [
                {"role": "assistant", "content": "👋 سلام! میں ClipGenesis AI Copilot Brain ہوں۔ میں 9Router کے تمام AI ماڈلز کے ساتھ لائیو منسلک ہوں۔ سکرپٹ، آواز، یا ویژول سیٹنگز کے بارے میں کچھ بھی پوچھیں!"}
            ]

        # Display history
        chat_container = st.container(height=200)
        with chat_container:
            for msg in st.session_state["copilot_chat_history"]:
                if msg["role"] == "user":
                    st.chat_message("user").write(msg["content"])
                else:
                    st.chat_message("assistant").write(msg["content"])

        # Chat Input
        user_input = st.chat_input("Ask AI Copilot anything…", key="copilot_chat_input")
        
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
