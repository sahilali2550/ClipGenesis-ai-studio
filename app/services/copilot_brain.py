"""
app/services/copilot_brain.py — ClipGenesis AI Copilot Brain Engine
Interfaces with 9Router AI Model Team (Gemini 1.5 Pro, GPT-4o, DeepSeek, Claude 3.5),
monitors active video tasks, and auto-diagnoses rendering status.
"""

import os
import glob
import time
import requests
from loguru import logger
from typing import Dict, Any, List

NINEROUTER_BASE_URL = "http://localhost:20128/v1"

MODEL_TEAM_MAP = {
    "gemini_flash": ("✨ Gemini 3.1 / 1.5 Flash (Ultra Fast)", "ag/gemini-3.1-flash-image"),
    "gpt4o": ("🚀 GPT-4o Omni (Creative Scripting)", "openai/gpt-4o"),
    "deepseek_r1": ("🧠 DeepSeek R1 / V3 (Deep Logic & Research)", "deepseek/deepseek-reasoner"),
    "claude_sonnet": ("🎭 Claude 3.5 Sonnet (Refined Polish)", "anthropic/claude-3-5-sonnet"),
    "qwen_72b": ("⚡ Qwen 2.5 72B (Multilingual Expert)", "qwen/qwen-2.5-72b"),
}


def get_copilot_system_status() -> Dict[str, Any]:
    """
    Scans ClipGenesis runtime state, active tasks, storage directories, and 9Router status.
    """
    ninerouter_online = False
    try:
        r = requests.get(f"{NINEROUTER_BASE_URL}/models", timeout=2)
        if r.status_code == 200:
            ninerouter_online = True
    except Exception:
        ninerouter_online = False

    # Check active task folders
    tasks = glob.glob("storage/tasks/*")
    active_tasks = []
    for t in tasks:
        if os.path.isdir(t):
            t_id = os.path.basename(t)
            script_exists = os.path.exists(os.path.join(t, "script.json"))
            audio_exists = os.path.exists(os.path.join(t, "audio.mp3"))
            sub_exists = os.path.exists(os.path.join(t, "subtitle.srt"))
            final_exists = os.path.exists(os.path.join(t, "final-1.mp4")) or os.path.exists(os.path.join(t, "video.mp4"))
            
            active_tasks.append({
                "task_id": t_id,
                "script": script_exists,
                "audio": audio_exists,
                "subtitles": sub_exists,
                "video_ready": final_exists,
                "mtime": time.ctime(os.path.getmtime(t))
            })

    # Check general videos
    gen_videos = glob.glob("storage/general_videos/*.mp4")

    return {
        "ninerouter_online": ninerouter_online,
        "active_tasks_count": len(active_tasks),
        "recent_tasks": active_tasks[:3],
        "generated_videos_count": len(gen_videos),
    }


def query_copilot_brain(
    user_prompt: str,
    selected_model_key: str = "gemini_flash",
    current_context: str = ""
) -> str:
    """
    Queries 9Router multi-model team with ClipGenesis Copilot system prompt and live runtime context.
    """
    sys_status = get_copilot_system_status()
    
    model_name = MODEL_TEAM_MAP.get(selected_model_key, MODEL_TEAM_MAP["gemini_flash"])[1]

    system_instruction = f"""
You are ClipGenesis AI Copilot Brain — the intelligent assistant embedded inside ClipGenesis AI Video Studio.
You help video creators write viral scripts, choose 9Router image styles (Photorealistic 8K, 3D Pixar, Cyberpunk), select AI voices, generate SEO hashtags, and troubleshoot video tasks.

Live Studio Context:
- 9Router Status: {"ONLINE ✅" if sys_status['ninerouter_online'] else "OFFLINE / LOCAL PROXY"}
- Active Tasks: {sys_status['active_tasks_count']}
- Current Tab / Page: {current_context}

Be encouraging, professional, concise, and respond in clear, helpful language (supporting Urdu & English).
"""

    messages = [
        {"role": "system", "content": system_instruction},
        {"role": "user", "content": user_prompt}
    ]

    try:
        res = requests.post(
            f"{NINEROUTER_BASE_URL}/chat/completions",
            json={
                "model": model_name,
                "messages": messages,
                "temperature": 0.7,
                "max_tokens": 800,
            },
            timeout=15
        )
        if res.status_code == 200:
            data = res.json()
            return data["choices"][0]["message"]["content"]
        else:
            return f"🤖 Copilot (Local Fallback): System status is nominal. 9Router status: {res.status_code}. Ask me to refine scripts, suggest styles, or generate hashtags!"
    except Exception as ex:
        logger.warning(f"Copilot 9Router query warning: {ex}")
        # Smart local fallback response generator
        low = user_prompt.lower()
        if "script" in low or "story" in low or "سکرپٹ" in low:
            return "💡 **Copilot Script Tip**: Try giving a clear protagonist, exciting hook in the first 3 seconds, and a strong moral resolution at the end. Choose 3.5s scene speed for maximum engagement!"
        elif "hashtag" in low or "seo" in low or "ہیش" in low:
            return "🏷️ **Copilot SEO Recommendation**:\n#Shorts #Reels #Viral #Trending #ClipGenesis #AIContent #Top10 #ExplorePage"
        elif "style" in low or "image" in low or "تصویر" in low:
            return "🎨 **Copilot Style Recommendation**: For Kids Stories use `3D Pixar / Disney`. For Mysteries & Crime use `Cyberpunk Dark` or `Photorealistic 8K`!"
        else:
            return f"🧠 **ClipGenesis Brain Active**: I am monitoring all render jobs ({sys_status['active_tasks_count']} active tasks). How can I assist you with scriptwriting, voice selection, or video styles today?"
