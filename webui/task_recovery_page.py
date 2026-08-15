"""
webui/task_recovery_page.py — Dedicated Task Recovery & Unfinished Tasks Manager
Allows viewing real interrupted tasks, resuming them, or deleting stale tasks cleanly.
"""

import os
import streamlit as st
from app.services import task as tm


def render_task_recovery_page():
    st.markdown(
        """
        <div style="padding:10px 0 18px 0;">
            <span style="font-size:1.8rem;font-weight:800;background:linear-gradient(135deg,#00E5A0,#00B4D8);
                         -webkit-background-clip:text;-webkit-text-fill-color:transparent;background-clip:text;">
                🛡️ Task Recovery & Unfinished Tasks
            </span>
            <span style="font-size:0.85rem;color:#8A7F78;margin-left:14px;">
                Power-Cut Guard • Resume Interrupted Videos • Clean Stale Tasks
            </span>
        </div>
        """,
        unsafe_allow_html=True
    )

    unfinished = tm.get_unfinished_tasks()

    # Top Control Bar
    col_stat, col_clean = st.columns([3, 1])
    with col_stat:
        st.markdown(
            f"""
            <div style="background:#161616;border:1px solid rgba(0,229,160,0.3);border-radius:10px;padding:12px 18px;">
                <b style="color:#00E5A0;font-size:1.1rem;">📊 Interrupted Tasks: {len(unfinished)}</b>
                <p style="margin:2px 0 0 0;font-size:0.8rem;color:#8A7F78;">
                    Only genuinely interrupted tasks with saved assets are listed below.
                </p>
            </div>
            """,
            unsafe_allow_html=True
        )
    with col_clean:
        if unfinished:
            if st.button("🧹 Clean All Stale Tasks", type="secondary", use_container_width=True, key="clean_all_tasks_btn"):
                count = tm.clean_all_unfinished_tasks()
                st.success(f"🧹 Cleaned {count} stale tasks successfully!")
                st.rerun()

    st.markdown("<br/>", unsafe_allow_html=True)

    if not unfinished:
        st.markdown(
            """
            <div style="background:#161616;border:1px solid rgba(0,229,160,0.2);border-radius:12px;
                        padding:36px;text-align:center;margin-top:10px;">
                <div style="font-size:2.5rem;margin-bottom:8px;">✅</div>
                <h3 style="color:#00E5A0;margin-bottom:6px;">No Interrupted Tasks Found!</h3>
                <p style="color:#8A7F78;font-size:0.9rem;max-width:480px;margin:0 auto;">
                    All previous tasks completed successfully or workspace is clean. Any new task interrupted by a power cut will appear here automatically.
                </p>
            </div>
            """,
            unsafe_allow_html=True
        )
        return

    # List of real unfinished tasks
    for idx, t in enumerate(unfinished):
        t_id = t["task_id"]
        subj = t["subject"]
        created = t.get("created_at", "Unknown")
        has_audio = bool(t.get("audio_file"))
        has_srt = bool(t.get("srt_file"))
        f_count = t.get("file_count", 0)

        with st.container(border=True):
            c_info, c_acts = st.columns([3, 1])
            with c_info:
                st.markdown(f"#### ⚡ `{t_id}` — **{subj}**")
                badges = []
                if has_audio:
                    badges.append("<span style='color:#00E5A0;'>🎙️ Voiceover Audio Saved</span>")
                if has_srt:
                    badges.append("<span style='color:#00B4D8;'>✍️ Subtitles SRT Saved</span>")
                badges.append(f"<span style='color:#8A7F78;'>📁 {f_count} Files in folder</span>")
                
                st.markdown(f"🕒 **Interrupted At:** `{created}` &nbsp;|&nbsp; " + " &nbsp;•&nbsp; ".join(badges), unsafe_allow_html=True)

            with c_acts:
                if st.button("🔄 Resume Task", type="primary", key=f"rec_res_{t_id}_{idx}", use_container_width=True):
                    with st.spinner(f"⚡ Resuming video rendering for '{subj}'..."):
                        try:
                            res = tm.resume_task(t_id)
                            st.success(f"🎉 Task '{subj}' completed successfully!")
                            st.rerun()
                        except Exception as ex:
                            st.error(f"❌ Resume Error: {ex}")

                if st.button("🗑️ Delete", key=f"rec_del_{t_id}_{idx}", use_container_width=True):
                    tm.delete_unfinished_task(t_id)
                    st.success(f"🗑️ Deleted task {t_id}")
                    st.rerun()
