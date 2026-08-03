"""
Platform Integration - Auto hashtag generator, usage dashboard, smart caching, version history.
"""

import os
import time
import json
import shutil
import hashlib
from typing import Dict, List, Optional
from dataclasses import dataclass, field
from loguru import logger
from app.utils import utils
from app.config import config


# ─── Auto Hashtag Generator ────────────────────────────────────────────

class HashtagGenerator:
    """Generate trending hashtags from video content"""

    # Base hashtag pools by category
    CATEGORY_HASHTAGS = {
        "health": ["#health", "#wellness", "#fitness", "#nutrition", "#mentalhealth", "#selfcare", "#healthy", "#healthylifestyle"],
        "finance": ["#finance", "#money", "#investing", "#wealth", "#financialfreedom", "#business", "#entrepreneur", "#personalfinance"],
        "tech": ["#tech", "#technology", "#AI", "#coding", "#programming", "#innovation", "#digital", "#software"],
        "education": ["#education", "#learning", "#knowledge", "#study", "#facts", "#didyouknow", "#educational", "#science"],
        "motivation": ["#motivation", "#inspiration", "#success", "#mindset", "#goals", "#nevergiveup", "#motivational", "#grind"],
        "entertainment": ["#entertainment", "#fun", "#comedy", "#humor", "#trending", "#viral", "#fyp", "#foryou"],
        "lifestyle": ["#lifestyle", "#life", "#dailylife", "#vlog", "#day", "#routine", "#livingmybestlife"],
        "food": ["#food", "#foodie", "#cooking", "#recipe", "#healthy", "#yummy", "#delicious", "#homemade"],
    }

    # Universal high-engagement hashtags
    UNIVERSAL_TAGS = ["#trending", "#viral", "#fyp", "#foryou", "#explore", "#reels", "#shorts"]

    def generate(self, title: str, script: str = "", platform: str = "youtube",
                 count: int = 15) -> List[str]:
        """Generate hashtags based on content"""
        content = f"{title} {script}".lower()
        tags = set()

        # Match category hashtags
        for category, hashtags in self.CATEGORY_HASHTAGS.items():
            if any(kw in content for kw in category.split()):
                tags.update(hashtags[:4])

        # Extract key nouns from title
        stop_words = {"the", "a", "an", "is", "are", "was", "were", "be", "been",
                      "to", "of", "in", "for", "on", "with", "at", "by", "from",
                      "and", "or", "but", "not", "this", "that", "it", "how", "what",
                      "why", "when", "where", "who", "your", "you", "can", "will"}
        words = re.findall(r'\b[a-zA-Z]{3,}\b', title.lower())
        keywords = [w for w in words if w not in stop_words]
        for kw in keywords[:5]:
            tags.add(f"#{kw}")

        # Add platform-specific tags
        if platform == "tiktok":
            tags.update(["#fyp", "#foryou", "#tiktok", "#viral"])
        elif platform == "youtube":
            tags.update(["#youtube", "#subscribe", "#shorts"])
        elif platform == "instagram":
            tags.update(["#reels", "#instagram", "#explore"])

        # Fill with universal tags
        while len(tags) < count:
            for tag in self.UNIVERSAL_TAGS:
                if len(tags) >= count:
                    break
                tags.add(tag)

        return sorted(list(tags))[:count]


# ─── Smart Cache ───────────────────────────────────────────────────────

class SmartCache:
    """Intelligent caching system to reuse downloaded videos/clips across projects"""

    def __init__(self):
        self._cache_dir = utils.storage_dir("cache_videos")
        self._index_file = os.path.join(self._cache_dir, "cache_index.json")
        self._index = self._load_index()

    def _load_index(self) -> Dict:
        if os.path.exists(self._index_file):
            try:
                with open(self._index_file, "r") as f:
                    return json.load(f)
            except Exception:
                pass
        return {"entries": {}, "stats": {"hits": 0, "misses": 0}}

    def _save_index(self):
        os.makedirs(self._cache_dir, exist_ok=True)
        with open(self._index_file, "w") as f:
            json.dump(self._index, f, indent=2, default=str)

    def get(self, key: str) -> Optional[str]:
        """Get cached file path by key"""
        entry = self._index["entries"].get(key)
        if entry and os.path.exists(entry["path"]):
            entry["last_accessed"] = time.time()
            entry["access_count"] = entry.get("access_count", 0) + 1
            self._index["stats"]["hits"] += 1
            self._save_index()
            return entry["path"]
        self._index["stats"]["misses"] += 1
        return None

    def put(self, key: str, file_path: str, metadata: Dict = None):
        """Add file to cache"""
        self._index["entries"][key] = {
            "path": file_path,
            "size": os.path.getsize(file_path) if os.path.exists(file_path) else 0,
            "created_at": time.time(),
            "last_accessed": time.time(),
            "access_count": 1,
            "metadata": metadata or {},
        }
        self._save_index()

    def get_stats(self) -> Dict:
        """Get cache statistics"""
        total_size = sum(e.get("size", 0) for e in self._index["entries"].values())
        return {
            "total_entries": len(self._index["entries"]),
            "total_size_mb": round(total_size / 1_000_000, 2),
            "hits": self._index["stats"]["hits"],
            "misses": self._index["stats"]["misses"],
            "hit_rate": round(
                self._index["stats"]["hits"] /
                max(1, self._index["stats"]["hits"] + self._index["stats"]["misses"]) * 100, 1
            ),
        }

    def cleanup(self, max_age_days: int = 30, max_size_mb: int = 5000):
        """Remove old or excess cache entries"""
        now = time.time()
        max_age = max_age_days * 86400
        removed = 0

        # Remove expired entries
        expired = [k for k, v in self._index["entries"].items()
                   if now - v.get("last_accessed", 0) > max_age]
        for key in expired:
            entry = self._index["entries"].pop(key)
            if os.path.exists(entry["path"]):
                try:
                    os.remove(entry["path"])
                except Exception:
                    pass
            removed += 1

        # Remove excess if over size limit
        total_size = sum(e.get("size", 0) for e in self._index["entries"].values())
        if total_size > max_size_mb * 1_000_000:
            # Sort by last accessed (oldest first)
            sorted_entries = sorted(self._index["entries"].items(),
                                     key=lambda x: x[1].get("last_accessed", 0))
            for key, entry in sorted_entries:
                if total_size <= max_size_mb * 1_000_000:
                    break
                total_size -= entry.get("size", 0)
                if os.path.exists(entry["path"]):
                    try:
                        os.remove(entry["path"])
                    except Exception:
                        pass
                del self._index["entries"][key]
                removed += 1

        self._save_index()
        logger.info(f"Cache cleanup: removed {removed} entries")
        return removed


# ─── Version History ───────────────────────────────────────────────────

class VersionHistory:
    """Track and revert to previous video versions"""

    def __init__(self):
        self._history_dir = utils.storage_dir("version_history", create=True)

    def save_version(self, task_id: str, params: Dict, result: Dict,
                      label: str = "") -> str:
        """Save a version snapshot"""
        version_id = f"v_{int(time.time())}_{task_id[:8]}"
        version_dir = os.path.join(self._history_dir, task_id)
        os.makedirs(version_dir, exist_ok=True)

        version_data = {
            "version_id": version_id,
            "task_id": task_id,
            "label": label or f"Version {version_id}",
            "params": params,
            "result_summary": {
                "videos": result.get("videos", []),
                "script": result.get("script", "")[:200],
                "terms": result.get("terms", []),
            },
            "created_at": time.time(),
        }

        version_file = os.path.join(version_dir, f"{version_id}.json")
        with open(version_file, "w", encoding="utf-8") as f:
            json.dump(version_data, f, ensure_ascii=False, indent=2, default=str)

        logger.info(f"Version saved: {version_id} for task {task_id}")
        return version_id

    def get_versions(self, task_id: str) -> List[Dict]:
        """Get all versions for a task"""
        version_dir = os.path.join(self._history_dir, task_id)
        if not os.path.isdir(version_dir):
            return []

        versions = []
        for fname in sorted(os.listdir(version_dir), reverse=True):
            if fname.endswith(".json"):
                with open(os.path.join(version_dir, fname), "r") as f:
                    versions.append(json.load(f))
        return versions

    def get_version(self, task_id: str, version_id: str) -> Optional[Dict]:
        """Get a specific version"""
        version_file = os.path.join(self._history_dir, task_id, f"{version_id}.json")
        if os.path.exists(version_file):
            with open(version_file, "r") as f:
                return json.load(f)
        return None


# ─── Usage Dashboard ───────────────────────────────────────────────────

class UsageDashboard:
    """Track API costs and usage across providers"""

    def __init__(self):
        self._usage_file = os.path.join(utils.storage_dir("", create=True), "usage_stats.json")
        self._usage = self._load()

    def _load(self) -> Dict:
        if os.path.exists(self._usage_file):
            try:
                with open(self._usage_file, "r") as f:
                    return json.load(f)
            except Exception:
                pass
        return {
            "api_calls": {},
            "video_generations": {"total": 0, "by_date": {}},
            "tts_usage": {"total_chars": 0, "by_provider": {}},
            "llm_usage": {"total_tokens_approx": 0, "by_provider": {}},
        }

    def _save(self):
        with open(self._usage_file, "w") as f:
            json.dump(self._usage, f, indent=2, default=str)

    def track_api_call(self, provider: str, endpoint: str = ""):
        """Track an API call"""
        key = f"{provider}:{endpoint}" if endpoint else provider
        if key not in self._usage["api_calls"]:
            self._usage["api_calls"][key] = {"count": 0, "last_called": 0}
        self._usage["api_calls"][key]["count"] += 1
        self._usage["api_calls"][key]["last_called"] = time.time()
        self._save()

    def track_video_generation(self):
        """Track a video generation"""
        self._usage["video_generations"]["total"] += 1
        date_key = time.strftime("%Y-%m-%d")
        self._usage["video_generations"]["by_date"][date_key] = \
            self._usage["video_generations"]["by_date"].get(date_key, 0) + 1
        self._save()

    def track_tts_usage(self, provider: str, char_count: int):
        """Track TTS character usage"""
        self._usage["tts_usage"]["total_chars"] += char_count
        if provider not in self._usage["tts_usage"]["by_provider"]:
            self._usage["tts_usage"]["by_provider"][provider] = 0
        self._usage["tts_usage"]["by_provider"][provider] += char_count
        self._save()

    def track_llm_usage(self, provider: str, approx_tokens: int):
        """Track LLM token usage"""
        self._usage["llm_usage"]["total_tokens_approx"] += approx_tokens
        if provider not in self._usage["llm_usage"]["by_provider"]:
            self._usage["llm_usage"]["by_provider"][provider] = 0
        self._usage["llm_usage"]["by_provider"][provider] += approx_tokens
        self._save()

    def get_summary(self) -> Dict:
        """Get usage summary"""
        return {
            "api_calls_total": sum(v["count"] for v in self._usage["api_calls"].values()),
            "videos_generated": self._usage["video_generations"]["total"],
            "tts_chars_total": self._usage["tts_usage"]["total_chars"],
            "llm_tokens_approx": self._usage["llm_usage"]["total_tokens_approx"],
            "videos_today": self._usage["video_generations"]["by_date"].get(
                time.strftime("%Y-%m-%d"), 0),
            "top_api_providers": sorted(
                self._usage["api_calls"].items(),
                key=lambda x: x[1]["count"],
                reverse=True
            )[:5],
        }


import re

# Global instances
hashtag_generator = HashtagGenerator()
smart_cache = SmartCache()
version_history = VersionHistory()
usage_dashboard = UsageDashboard()
