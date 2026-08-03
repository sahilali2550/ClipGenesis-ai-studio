"""
Security & Enterprise - JWT auth, watermarking, API rate limiting, audit logs.
"""

import os
import time
import json
import hashlib
import functools
import threading
from typing import Dict, Optional, List
from collections import defaultdict
from dataclasses import dataclass, field
from loguru import logger

from app.utils import utils


# ─── JWT Auth ───────────────────────────────────────────────────────────

class JWTAuth:
    """JWT-based authentication system"""

    def __init__(self, secret_key: str = ""):
        self._secret = secret_key or os.environ.get("JWT_SECRET", "clipgenesis-secret-key-change-me")
        self._users: Dict[str, Dict] = {}
        self._users_file = os.path.join(utils.root_dir(), "storage", "users.json")
        self._load_users()

    def _load_users(self):
        if os.path.exists(self._users_file):
            with open(self._users_file, "r") as f:
                self._users = json.load(f)

    def _save_users(self):
        os.makedirs(os.path.dirname(self._users_file), exist_ok=True)
        with open(self._users_file, "w") as f:
            json.dump(self._users, f, indent=2)

    def register(self, username: str, password: str, role: str = "user") -> Optional[Dict]:
        if username in self._users:
            return None
        pw_hash = hashlib.sha256(f"{password}{self._secret}".encode()).hexdigest()
        self._users[username] = {
            "username": username,
            "password_hash": pw_hash,
            "role": role,
            "created_at": time.time(),
        }
        self._save_users()
        return {"username": username, "role": role}

    def authenticate(self, username: str, password: str) -> Optional[str]:
        user = self._users.get(username)
        if not user:
            return None
        pw_hash = hashlib.sha256(f"{password}{self._secret}".encode()).hexdigest()
        if user["password_hash"] != pw_hash:
            return None
        # Generate simple token (production: use PyJWT)
        token_data = f"{username}:{time.time()}:{self._secret}"
        token = hashlib.sha256(token_data.encode()).hexdigest()
        # Store token for validation
        user["active_token"] = token
        user["token_created"] = time.time()
        self._save_users()
        return token

    def validate_token(self, token: str) -> Optional[Dict]:
        for username, user in self._users.items():
            if user.get("active_token") == token:
                token_age = time.time() - user.get("token_created", 0)
                if token_age < 86400:  # 24 hour expiry
                    return {"username": username, "role": user["role"]}
        return None

    def get_user(self, username: str) -> Optional[Dict]:
        user = self._users.get(username)
        if user:
            return {"username": user["username"], "role": user["role"]}
        return None


# ─── Watermarking ───────────────────────────────────────────────────────

class Watermarker:
    """Add custom watermarks to videos"""

    @staticmethod
    def add_text_watermark(video_path: str, text: str, position: str = "bottom_right",
                            font_size: int = 24, opacity: float = 0.5,
                            output_path: str = "") -> Optional[str]:
        import subprocess

        if not output_path:
            output_path = video_path.replace(".mp4", "_watermarked.mp4")

        positions = {
            "top_left": "x=10:y=10",
            "top_right": "x=w-tw-10:y=10",
            "bottom_left": "x=10:y=h-th-10",
            "bottom_right": "x=w-tw-10:y=h-th-10",
            "center": "x=(w-tw)/2:y=(h-th)/2",
        }
        pos = positions.get(position, positions["bottom_right"])

        try:
            cmd = [
                "ffmpeg", "-y", "-i", video_path,
                "-vf", f"drawtext=text='{text}':fontsize={font_size}:fontcolor=white@{opacity}:{pos}",
                "-c:a", "copy", output_path
            ]
            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode == 0:
                logger.success(f"Text watermark added: '{text}' at {position}")
                return output_path
        except Exception as e:
            logger.error(f"Watermark failed: {e}")
        return None

    @staticmethod
    def add_image_watermark(video_path: str, image_path: str, position: str = "bottom_right",
                             scale: float = 0.15, opacity: float = 0.5,
                             output_path: str = "") -> Optional[str]:
        import subprocess

        if not output_path:
            output_path = video_path.replace(".mp4", "_watermarked.mp4")

        positions = {
            "top_left": "overlay=10:10",
            "top_right": "overlay=main_w-overlay_w-10:10",
            "bottom_left": "overlay=10:main_h-overlay_h-10",
            "bottom_right": "overlay=main_w-overlay_w-10:main_h-overlay_h-10",
            "center": "overlay=(main_w-overlay_w)/2:(main_h-overlay_h)/2",
        }
        pos = positions.get(position, positions["bottom_right"])

        try:
            cmd = [
                "ffmpeg", "-y",
                "-i", video_path,
                "-i", image_path,
                "-filter_complex",
                f"[1:v]scale=iw*{scale}:ih*{scale},format=rgba,colorchannelmixer=aa={opacity}[watermark];[0:v][watermark]{pos}",
                "-c:a", "copy", output_path
            ]
            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode == 0:
                logger.success(f"Image watermark added at {position}")
                return output_path
        except Exception as e:
            logger.error(f"Image watermark failed: {e}")
        return None


# ─── Rate Limiter ───────────────────────────────────────────────────────

class RateLimiter:
    """Per-user API rate limiting"""

    def __init__(self, requests_per_minute: int = 60,
                 requests_per_hour: int = 300,
                 requests_per_day: int = 1000):
        self._limits = {
            "minute": requests_per_minute,
            "hour": requests_per_hour,
            "day": requests_per_day,
        }
        self._requests: Dict[str, List[float]] = defaultdict(list)
        self._lock = threading.Lock()

    def is_allowed(self, user_id: str) -> bool:
        """Check if request is allowed for user"""
        now = time.time()
        with self._lock:
            requests = self._requests[user_id]
            # Clean old entries
            requests[:] = [t for t in requests if t > now - 86400]

            # Check limits
            minute_count = sum(1 for t in requests if t > now - 60)
            hour_count = sum(1 for t in requests if t > now - 3600)
            day_count = len(requests)

            if minute_count >= self._limits["minute"]:
                return False
            if hour_count >= self._limits["hour"]:
                return False
            if day_count >= self._limits["day"]:
                return False

            requests.append(now)
            return True

    def get_remaining(self, user_id: str) -> Dict:
        now = time.time()
        requests = self._requests.get(user_id, [])
        minute_count = sum(1 for t in requests if t > now - 60)
        hour_count = sum(1 for t in requests if t > now - 3600)
        day_count = sum(1 for t in requests if t > now - 86400)

        return {
            "minute": {"remaining": self._limits["minute"] - minute_count, "limit": self._limits["minute"]},
            "hour": {"remaining": self._limits["hour"] - hour_count, "limit": self._limits["hour"]},
            "day": {"remaining": self._limits["day"] - day_count, "limit": self._limits["day"]},
        }


# ─── Audit Logger ───────────────────────────────────────────────────────

class AuditLogger:
    """Track all actions for compliance"""

    def __init__(self):
        self._log_dir = os.path.join(utils.root_dir(), "storage", "audit_logs")
        os.makedirs(self._log_dir, exist_ok=True)
        self._lock = threading.Lock()

    def log(self, user: str, action: str, details: Dict = None, ip: str = ""):
        """Log an audit event"""
        entry = {
            "timestamp": time.time(),
            "user": user,
            "action": action,
            "details": details or {},
            "ip": ip,
        }

        # Append to daily log file
        date_str = time.strftime("%Y-%m-%d")
        log_file = os.path.join(self._log_dir, f"audit_{date_str}.jsonl")

        with self._lock:
            with open(log_file, "a", encoding="utf-8") as f:
                f.write(json.dumps(entry, ensure_ascii=False, default=str) + "\n")

    def query(self, user: str = "", action: str = "", days: int = 7,
              limit: int = 100) -> List[Dict]:
        """Query audit logs"""
        results = []
        for i in range(days):
            date_str = time.strftime("%Y-%m-%d", time.localtime(time.time() - i * 86400))
            log_file = os.path.join(self._log_dir, f"audit_{date_str}.jsonl")
            if not os.path.exists(log_file):
                continue
            with open(log_file, "r", encoding="utf-8") as f:
                for line in f:
                    entry = json.loads(line.strip())
                    if user and entry["user"] != user:
                        continue
                    if action and entry["action"] != action:
                        continue
                    results.append(entry)
                    if len(results) >= limit:
                        return results
        return results


# Global instances
auth = JWTAuth()
watermarker = Watermarker()
rate_limiter = RateLimiter()
audit_logger = AuditLogger()
