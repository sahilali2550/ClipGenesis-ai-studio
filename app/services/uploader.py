"""
Direct Upload APIs - YouTube and TikTok integration for generated videos.
"""

import os
import time
from typing import Dict, Optional
from dataclasses import dataclass, field
from loguru import logger


@dataclass
class UploadJob:
    job_id: str = field(default_factory=lambda: str(__import__('uuid').uuid4()))
    video_path: str = ""
    platform: str = ""  # "youtube" or "tiktok"
    title: str = ""
    description: str = ""
    tags: list = field(default_factory=list)
    status: str = "pending"  # pending, uploading, processing, published, failed
    progress: int = 0
    error_message: str = ""
    url: str = ""
    created_at: float = field(default_factory=time.time)
    completed_at: float = 0.0


class YouTubeUploader:
    """YouTube direct upload integration"""

    def __init__(self):
        self._client = None

    def setup(self, client_secrets_file: str, credentials_file: str = "") -> bool:
        try:
            from google.oauth2.credentials import Credentials
            from google_auth_oauthlib.flow import InstalledAppFlow
            from google.auth.transport.requests import Request
            from googleapiclient.discovery import build
            from googleapiclient.http import MediaFileUpload

            self._SCOPES = ['https://www.googleapis.com/auth/youtube.upload']
            self._client_secrets = client_secrets_file
            self._credentials_file = credentials_file
            self._build_func = build
            self._MediaFileUpload = MediaFileUpload
            return True
        except ImportError:
            logger.warning("YouTube upload requires: pip install google-api-python-client google-auth-oauthlib")
            return False

    def upload(self, video_path: str, title: str, description: str = "",
               tags: list = None, privacy: str = "private",
               category_id: str = "28") -> Optional[str]:
        try:
            from googleapiclient.discovery import build
            from googleapiclient.http import MediaFileUpload
            from google.oauth2.credentials import Credentials
            from google.auth.transport.requests import Request
            import os

            creds = None
            if os.path.exists(self._credentials_file):
                creds = Credentials.from_authorized_user_file(self._credentials_file, self._SCOPES)
            if not creds or not creds.valid:
                if creds and creds.expired and creds.refresh_token:
                    creds.refresh(Request())
                else:
                    return None

            youtube = build('youtube', 'v3', credentials=creds)

            body = {
                'snippet': {
                    'title': title,
                    'description': description,
                    'tags': tags or [],
                    'categoryId': category_id
                },
                'status': {
                    'privacyStatus': privacy,
                    'selfDeclaredMadeForKids': False
                }
            }

            media = MediaFileUpload(
                video_path,
                chunksize=-1,
                resumable=True,
                mimetype='video/*'
            )

            request = youtube.videos().insert(
                part=','.join(body.keys()),
                body=body,
                media_body=media
            )

            response = None
            while response is None:
                status, response = request.next_chunk()
                if status:
                    logger.info(f"YouTube upload progress: {int(status.progress() * 100)}%")

            video_id = response['id']
            url = f"https://www.youtube.com/watch?v={video_id}"
            logger.success(f"YouTube upload complete: {url}")
            return url

        except Exception as e:
            logger.error(f"YouTube upload failed: {e}")
            return None


class TikTokUploader:
    """TikTok direct upload integration (requires TikTok Creator account)"""

    def __init__(self):
        self._access_token = None

    def setup(self, access_token: str) -> bool:
        self._access_token = access_token
        return True

    def upload(self, video_path: str, title: str, description: str = "",
               tags: list = None) -> Optional[str]:
        try:
            import requests

            tags = tags or []
            # TikTok Creator API endpoint
            url = "https://open-api.tiktok.com/research/video/upload/"

            with open(video_path, 'rb') as f:
                files = {'video': f}
                headers = {"Authorization": f"Bearer {self._access_token}"}
                data = {
                    'title': title,
                    'description': description,
                    'tags': ','.join(tags)
                }
                response = requests.post(url, files=files, headers=headers, data=data)

            if response.status_code == 200:
                result = response.json()
                if result.get('data', {}).get('share_url'):
                    share_url = result['data']['share_url']
                    logger.success(f"TikTok upload complete: {share_url}")
                    return share_url
            return None
        except Exception as e:
            logger.error(f"TikTok upload failed: {e}")
            return None


class UploadManager:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._youtube = YouTubeUploader()
            cls._instance._tiktok = TikTokUploader()
            cls._instance._jobs: Dict[str, UploadJob] = {}
        return cls._instance

    def upload_to_youtube(self, video_path: str, title: str, **kwargs) -> UploadJob:
        job = UploadJob(video_path=video_path, platform="youtube",
                        title=title, description=kwargs.get("description", ""),
                        tags=kwargs.get("tags", []))
        self._jobs[job.job_id] = job

        def do_upload():
            job.status = "uploading"
            url = self._youtube.upload(
                video_path=video_path,
                title=title,
                description=job.description,
                tags=job.tags,
                privacy=kwargs.get("privacy", "private")
            )
            if url:
                job.status = "published"
                job.url = url
            else:
                job.status = "failed"
                job.error_message = "Upload returned no URL"
            job.completed_at = time.time()

        threading.Thread(target=do_upload, daemon=True).start()
        return job

    def upload_to_tiktok(self, video_path: str, title: str, **kwargs) -> UploadJob:
        job = UploadJob(video_path=video_path, platform="tiktok",
                        title=title, description=kwargs.get("description", ""),
                        tags=kwargs.get("tags", []))
        self._jobs[job.job_id] = job

        def do_upload():
            job.status = "uploading"
            url = self._tiktok.upload(
                video_path=video_path,
                title=title,
                description=job.description,
                tags=job.tags
            )
            if url:
                job.status = "published"
                job.url = url
            else:
                job.status = "failed"
                job.error_message = "Upload returned no URL"
            job.completed_at = time.time()

        threading.Thread(target=do_upload, daemon=True).start()
        return job

    def get_job(self, job_id: str) -> Optional[Dict]:
        job = self._jobs.get(job_id)
        if job:
            return {
                "job_id": job.job_id,
                "platform": job.platform,
                "title": job.title,
                "status": job.status,
                "progress": job.progress,
                "url": job.url,
                "error_message": job.error_message,
            }
        return None

    def get_all_jobs(self) -> List[Dict]:
        return [self._job_to_dict(j) for j in self._jobs.values()]

    def _job_to_dict(self, job: UploadJob) -> Dict:
        return {
            "job_id": job.job_id,
            "platform": job.platform,
            "title": job.title,
            "video_path": job.video_path,
            "status": job.status,
            "progress": job.progress,
            "url": job.url,
            "error_message": job.error_message,
        }


import threading
upload_manager = UploadManager()
