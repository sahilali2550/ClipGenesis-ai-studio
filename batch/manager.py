import os
import json
import csv
import uuid
from typing import List, Dict, Optional, Union, Any
from loguru import logger
from batch.schemas import BatchJob, BatchTaskItem, BatchTaskStatus
from batch.processor import process_batch_job


_active_batches: Dict[str, BatchJob] = {}


def parse_batch_input(raw_data: Union[str, List[Dict[str, Any]]]) -> List[BatchTaskItem]:
    """Parses JSON or CSV input data into a list of BatchTaskItems."""
    items: List[BatchTaskItem] = []

    if isinstance(raw_data, list):
        parsed = raw_data
    elif isinstance(raw_data, str) and raw_data.endswith(".json") and os.path.exists(raw_data):
        with open(raw_data, "r", encoding="utf-8") as f:
            parsed = json.load(f)
    elif isinstance(raw_data, str) and raw_data.endswith(".csv") and os.path.exists(raw_data):
        parsed = []
        with open(raw_data, "r", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            for row in reader:
                parsed.append(dict(row))
    elif isinstance(raw_data, str):
        # Try JSON string parse
        try:
            parsed = json.loads(raw_data)
        except Exception:
            parsed = []
    else:
        parsed = []

    for idx, entry in enumerate(parsed):
        topic = entry.get("topic") or entry.get("subject") or f"Topic {idx+1}"
        task_item = BatchTaskItem(
            task_id=f"task_{idx+1:03d}",
            topic=topic,
            script=entry.get("script"),
            template=entry.get("template", "youtube_short"),
            brand=entry.get("brand"),
            language=entry.get("language", "en"),
            voice_name=entry.get("voice_name"),
        )
        items.append(task_item)

    return items


def create_batch_job(
    input_data: Union[str, List[Dict[str, Any]]],
    max_concurrent: int = 1
) -> BatchJob:
    """Creates a new BatchJob from CSV/JSON file path, string, or list of dicts."""
    batch_id = f"batch_{uuid.uuid4().hex[:6]}"
    items = parse_batch_input(input_data)
    
    job = BatchJob(
        batch_id=batch_id,
        max_concurrent=max_concurrent,
        total_tasks=len(items),
        items=items
    )
    _active_batches[batch_id] = job
    logger.info(f"Created batch job {batch_id} with {len(items)} items.")
    return job


def get_batch(batch_id: str) -> Optional[BatchJob]:
    return _active_batches.get(batch_id)


def list_batches() -> List[BatchJob]:
    return list(_active_batches.values())


def get_batch_stats() -> Dict[str, int]:
    total_batches = len(_active_batches)
    total_videos = 0
    completed_videos = 0
    failed_videos = 0

    for job in _active_batches.values():
        total_videos += len(job.items)
        completed_videos += job.completed_count
        failed_videos += job.failed_count

    return {
        "active_batches": total_batches,
        "total_videos": total_videos,
        "completed_videos": completed_videos,
        "failed_videos": failed_videos,
    }
