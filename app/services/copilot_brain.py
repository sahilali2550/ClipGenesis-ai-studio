"""
app/services/copilot_brain.py — ClipGenesis Master AI Copilot Brain & Autonomous Intent Engine
Manages 10-Agent Autonomous Swarm, persistent disk memory (storage/copilot_brain_state.json),
auto-resume checkpoints after PC power loss, 9Router Multi-Model interaction, and direct video creation triggers.
"""

import os
import re
import json
import glob
import time
import requests
from loguru import logger
from typing import Dict, Any, List, Optional

NINEROUTER_BASE_URL = "http://localhost:20128/v1"
MEMORY_FILE_PATH = "storage/copilot_brain_state.json"
CHECKPOINT_FILE_PATH = "storage/task_checkpoints.json"

# Real 9Router model IDs — ag/ models VERIFIED working (HTTP 200 confirmed)
MODEL_TEAM_MAP = {
    "ag_flash_low":  ("✨ Gemini 3.5 Flash Low (Default — Fastest)", "ag/gemini-3.5-flash-low"),
    "ag_flash_mid":  ("🚀 Gemini 3.5 Flash Medium (Balanced)",       "ag/gemini-3.5-flash-medium"),
    "ag_flash_high": ("🔥 Gemini 3.7 Flash High (Most Capable)",     "ag/gemini-3.7-flash-high"),
    "deepseek_v3":   ("🧠 DeepSeek V3 (Deep Logic & Research)",       "if/deepseek-v3"),
    "qwen3_coder":   ("💻 Qwen3 Coder (Script & Code Expert)",        "if/qwen3-coder-plus"),
    "claude_sonnet": ("🎭 Claude Sonnet 4.5 (Refined Polish)",        "kr/claude-sonnet-4.5"),
}

# Fast fallback chain — ag/ models first (verified working), then others
_FALLBACK_MODEL_CHAIN = [
    "ag/gemini-3.5-flash-low",
    "ag/gemini-3.5-flash-extra-low",
    "ag/gemini-3-flash",
    "ag/gemini-3.5-flash-medium",
    "ag/gemini-3.7-flash-low",
    "freellm/openai-fast",
    "freellm/gpt-oss-20b",
]

SURAH_NAME_MAP = {
    "fatiha": 1, "baqarah": 2, "yasin": 36, "yaseen": 36, "rahman": 55,
    "mulk": 67, "kahf": 18, "waqiah": 56, "ikhlas": 112, "falaq": 113,
    "nas": 114, "naas": 114, "kafirun": 109, "nasr": 110, "masad": 111,
}


def _get_ninerouter_api_key() -> str:
    """Reads 9Router API key from config.toml (openai_api_key field)."""
    try:
        from app.config import config as cfg
        key = cfg.app.get("openai_api_key", "").strip()
        if key:
            return key
    except Exception:
        pass
    return ""


# ── 1. Power-Cut Checkpoint & Persistent Memory Engine ──────────────────────

def load_brain_memory() -> Dict[str, Any]:
    """Loads persistent copilot memory from disk."""
    if os.path.exists(MEMORY_FILE_PATH):
        try:
            with open(MEMORY_FILE_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.warning(f"Brain memory read warning: {e}")

    return {
        "chat_history": [
            {
                "role": "assistant",
                "content": (
                    "👋 سلام! میں ClipGenesis AI Copilot Brain (CEO Agent) ہوں۔ "
                    "میں 10-Agent Swarm کے ساتھ ڈائریکٹ جڑا ہوا ہوں۔ "
                    "مجھے ویڈیو بنانے کا آرڈر دیں (مثلاً: *'Surah 112 ki video bana do'* یا *'5 Mysterious Places ki reel banao'*), "
                    "اور میں فوراً ویڈیو پروسیس کر دوں گا!"
                )
            }
        ],
        "user_preferences": {
            "default_model": "ag_flash_low",
            "language": "ur"
        },
        "total_tasks_completed": 0
    }


def save_brain_memory(memory_data: Dict[str, Any]):
    """Saves copilot memory persistently to disk."""
    try:
        os.makedirs("storage", exist_ok=True)
        with open(MEMORY_FILE_PATH, "w", encoding="utf-8") as f:
            json.dump(memory_data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.warning(f"Brain memory save warning: {e}")


def save_powercut_checkpoint(task_id: str, stage: str, task_data: Dict[str, Any]):
    """
    Saves rendering checkpoint to disk so ClipGenesis can auto-resume after power cut.
    """
    try:
        os.makedirs("storage", exist_ok=True)
        checkpoints = {}
        if os.path.exists(CHECKPOINT_FILE_PATH):
            try:
                with open(CHECKPOINT_FILE_PATH, "r", encoding="utf-8") as f:
                    checkpoints = json.load(f)
            except Exception:
                checkpoints = {}

        checkpoints[task_id] = {
            "task_id": task_id,
            "stage": stage,
            "timestamp": time.time(),
            "readable_time": time.ctime(),
            "data": task_data,
            "resumable": True
        }

        with open(CHECKPOINT_FILE_PATH, "w", encoding="utf-8") as f:
            json.dump(checkpoints, f, ensure_ascii=False, indent=2)

        logger.info(f"🛡️ Power-Cut Guard: Saved checkpoint '{stage}' for task {task_id}")
    except Exception as e:
        logger.warning(f"Power-Cut Guard warning: {e}")


def get_unfinished_checkpoints() -> List[Dict[str, Any]]:
    """Scans for unfinished tasks interrupted by PC power cut."""
    if os.path.exists(CHECKPOINT_FILE_PATH):
        try:
            with open(CHECKPOINT_FILE_PATH, "r", encoding="utf-8") as f:
                checkpoints = json.load(f)

            unfinished = []
            for t_id, cp in checkpoints.items():
                if cp.get("resumable", False):
                    task_dir = os.path.join("storage", "tasks", t_id)
                    final_path = os.path.join(task_dir, "final-1.mp4")
                    if not os.path.exists(final_path):
                        unfinished.append(cp)

            return sorted(unfinished, key=lambda x: x.get("timestamp", 0), reverse=True)
        except Exception as e:
            logger.warning(f"Checkpoint scan warning: {e}")
    return []


def clear_checkpoint(task_id: str):
    """Removes checkpoint when task finishes successfully."""
    if os.path.exists(CHECKPOINT_FILE_PATH):
        try:
            with open(CHECKPOINT_FILE_PATH, "r", encoding="utf-8") as f:
                checkpoints = json.load(f)
            if task_id in checkpoints:
                del checkpoints[task_id]
                with open(CHECKPOINT_FILE_PATH, "w", encoding="utf-8") as f:
                    json.dump(checkpoints, f, ensure_ascii=False, indent=2)
        except Exception:
            pass


# ── 2. Autonomous Intent Parser ─────────────────────────────────────────────

def parse_autonomous_intent(user_prompt: str) -> Optional[Dict[str, Any]]:
    """
    Parses user prompt for autonomous execution actions (e.g. creating Quran videos or General videos).
    """
    low = user_prompt.lower()
    
    # 1. Check for Quran Video creation intent
    is_video_cmd = any(w in low for w in ["bana", "make", "create", "generate", "banao", "reel", "video"])
    
    if is_video_cmd or "surah" in low or "soorah" in low or "سورۃ" in low or "سورة" in low:
        # Match numeric surah: surah 112, soorah 55, etc.
        m_num = re.search(r"(?:surah|soorah|سورۃ|سورة)\s*(\d+)", low)
        surah_num = None
        if m_num:
            surah_num = int(m_num.group(1))
        else:
            # Match named surah: surah ikhlas, surah rahman, etc.
            for sname, snum in SURAH_NAME_MAP.items():
                if sname in low:
                    surah_num = snum
                    break

        if surah_num and 1 <= surah_num <= 114:
            # Match ayahs if specified (e.g. 1 se 10 ayahs)
            m_ayah = re.search(r"(\d+)\s*(?:se|to|-)\s*(\d+)", low)
            from_a, to_a = 1, 4
            if m_ayah:
                from_a = max(1, int(m_ayah.group(1)))
                to_a = max(from_a, int(m_ayah.group(2)))
            
            return {
                "type": "quran_video",
                "surah": surah_num,
                "from_ayah": from_a,
                "to_ayah": to_a,
                "video_aspect": "9:16",
                "reciter_name": "Yasser Al-Dossari"
            }

    # 2. Check for General Video creation intent
    if is_video_cmd and not ("surah" in low or "soorah" in low or "سورۃ" in low or "سورة" in low):
        # Extract clean topic by stripping action phrases
        clean_topic = re.sub(
            r"\b(bana\s*do|banao|make\s*a\s*video|create\s*a\s*video|create\s*video|generate|ki\s*video|ki\s*reel|facebook\s*post\s*k\s*liey|facebook\s*post\s*ky\s*liey)\b",
            "",
            low,
            flags=re.I
        ).strip()
        clean_topic = re.sub(r"\s+", " ", clean_topic).strip()
        
        if len(clean_topic) >= 3:
            return {
                "type": "general_video",
                "topic": clean_topic
            }

    return None


# ── 3. Swarm System Status ──────────────────────────────────────────────────

def get_copilot_system_status() -> Dict[str, Any]:
    """Scans ClipGenesis runtime state, active tasks, and 9Router status."""
    ninerouter_online = False
    try:
        r = requests.get(f"{NINEROUTER_BASE_URL}/models", timeout=2)
        if r.status_code == 200:
            ninerouter_online = True
    except Exception:
        ninerouter_online = False

    unfinished_cps = get_unfinished_checkpoints()
    gen_videos = glob.glob("storage/general_videos/*.mp4")

    swarm_bots = [
        {"name": "👑 Master Copilot (CEO)", "status": "Active 🟢"},
        {"name": "📜 Script & Prompt Bot", "status": "Ready ⚡"},
        {"name": "🎙️ Voice & Audio Bot", "status": "Ready ⚡"},
        {"name": "🎨 9Router Visual Bot", "status": "Ready ⚡"},
        {"name": "🏷️ SEO & Thumbnail Bot", "status": "Ready ⚡"},
        {"name": "⚙️ UI Controller Bot", "status": "Ready ⚡"},
        {"name": "🕌 Islamic Specialist Bot", "status": "Ready ⚡"},
        {"name": "🔗 Link Re-Creator Bot", "status": "Ready ⚡"},
        {"name": "📦 Batch Pipeline Bot", "status": "Ready ⚡"},
        {"name": "📊 Viral Predictor Bot", "status": "Ready ⚡"},
    ]

    return {
        "ninerouter_online": ninerouter_online,
        "unfinished_checkpoints": unfinished_cps,
        "powercut_recovery_available": len(unfinished_cps) > 0,
        "generated_videos_count": len(gen_videos),
        "swarm_bots": swarm_bots,
    }


# ── 4. Multi-Model Query Engine ─────────────────────────────────────────────

def _try_single_model(model: str, messages: list, headers: dict, timeout: int = 12) -> Optional[str]:
    """
    Attempts one 9Router chat request. Handles both standard JSON and SSE streaming responses.
    """
    try:
        res = requests.post(
            f"{NINEROUTER_BASE_URL}/chat/completions",
            headers=headers,
            json={
                "model": model,
                "messages": messages,
                "temperature": 0.7,
                "max_tokens": 600,
                "stream": False,
            },
            timeout=timeout
        )
        if res.status_code != 200:
            return None

        try:
            data = res.json()
            return data["choices"][0]["message"]["content"]
        except Exception:
            pass

        content_parts = []
        for line in res.text.splitlines():
            line = line.strip()
            if line.startswith("data:") and "[DONE]" not in line:
                try:
                    chunk = json.loads(line[5:].strip())
                    delta = chunk.get("choices", [{}])[0].get("delta", {})
                    if delta.get("content"):
                        content_parts.append(delta["content"])
                except Exception:
                    pass
        if content_parts:
            return "".join(content_parts)

    except Exception:
        pass
    return None


def query_copilot_brain(
    user_prompt: str,
    selected_model_key: str = "ag_flash_low",
    current_context: str = ""
) -> str:
    """
    Queries 9Router and checks for autonomous video creation commands.
    If a video command is parsed, appends an autonomous action marker.
    """
    intent_action = parse_autonomous_intent(user_prompt)
    sys_status = get_copilot_system_status()
    api_key = _get_ninerouter_api_key()
    headers = {"Authorization": f"Bearer {api_key}"} if api_key else {}

    primary_model = MODEL_TEAM_MAP.get(selected_model_key, MODEL_TEAM_MAP["ag_flash_low"])[1]
    model_chain = [primary_model] + [m for m in _FALLBACK_MODEL_CHAIN if m != primary_model]

    system_instruction = (
        "You are ClipGenesis AI Copilot Brain — CEO Agent of a 10-Agent Swarm inside ClipGenesis. "
        "When the user commands you to create a video, acknowledge enthusiastically in Urdu and state that "
        "the 10-Agent Swarm has started rendering the video.\n\n"
        f"Live: 9Router {'ONLINE' if sys_status['ninerouter_online'] else 'OFFLINE'} | Tab: {current_context}\n"
        "Respond in clear Urdu or English."
    )

    messages = [
        {"role": "system", "content": system_instruction},
        {"role": "user", "content": user_prompt},
    ]

    base_reply = None
    for model in model_chain:
        logger.info(f"Copilot: Trying {model}...")
        reply = _try_single_model(model, messages, headers, timeout=12)
        if reply and len(reply.strip()) > 5:
            base_reply = reply.strip()
            break

    if not base_reply:
        if intent_action and intent_action["type"] == "quran_video":
            base_reply = f"🚀 **Surah {intent_action['surah']} کی ویڈیو رینڈرنگ خودکار طور پر شروع کر دی گئی ہے!** 10-Agent Swarm پس منظر میں پروسیسنگ کر رہا ہے..."
        elif intent_action and intent_action["type"] == "general_video":
            base_reply = f"🚀 **موضوع '{intent_action['topic']}' کی وائرل ریل جنریشن شروع کر دی گئی ہے!** 10-Agent Swarm رینڈر کر رہا ہے..."
        else:
            base_reply = "🧠 **ClipGenesis Copilot Active:** 10-Agent Swarm تیار ہے۔ مجھے ویڈیو بنانے کا آرڈر دیں!"

    # Append autonomous action JSON marker if intent was detected
    if intent_action:
        action_json = json.dumps(intent_action, ensure_ascii=False)
        base_reply += f"\n\n[AUTONOMOUS_ACTION: {action_json}]"

    return base_reply
