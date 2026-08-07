from typing import Optional, List, Dict, Any
from enum import Enum
from pydantic import BaseModel, Field
from datetime import datetime


class BatchTaskStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class BatchTaskItem(BaseModel):
    task_id: str = ""
    topic: str = ""
    script: Optional[str] = None
    template: Optional[str] = "youtube_short"
    brand: Optional[str] = None
    language: Optional[str] = "en"
    voice_name: Optional[str] = None
    status: BatchTaskStatus = BatchTaskStatus.PENDING
    error_message: Optional[str] = None
    output_video: Optional[str] = None
    created_at: str = Field(default_factory=lambda: datetime.now().isoformat())


class BatchJob(BaseModel):
    batch_id: str
    created_at: str = Field(default_factory=lambda: datetime.now().isoformat())
    status: BatchTaskStatus = BatchTaskStatus.PENDING
    max_concurrent: int = 1
    total_tasks: int = 0
    completed_count: int = 0
    failed_count: int = 0
    items: List[BatchTaskItem] = Field(default_factory=list)
