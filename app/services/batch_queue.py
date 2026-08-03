"""
Bulk Queue Management - Batch video generation with priority scheduling, auto-retry, and status tracking.
"""

import os
import json
import time
import threading
import uuid
from typing import List, Dict, Optional, Callable
from dataclasses import dataclass, field, asdict
from enum import Enum
from loguru import logger
from queue import PriorityQueue, Empty

from app.config import config
from app.services import task as tm
from app.utils import utils


class TaskPriority(Enum):
    LOW = 3
    NORMAL = 2
    HIGH = 1


class BatchStatus(Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class BatchTask:
    task_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    subject: str = ""
    params_dict: Dict = field(default_factory=dict)
    priority: int = TaskPriority.NORMAL.value
    status: str = BatchStatus.PENDING.value
    retry_count: int = 0
    max_retries: int = 3
    error_message: str = ""
    result: Dict = field(default_factory=dict)
    created_at: float = field(default_factory=time.time)
    started_at: float = 0.0
    completed_at: float = 0.0
    progress: int = 0


class BatchQueue:
    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._tasks: Dict[str, BatchTask] = {}
                    cls._instance._queue = PriorityQueue()
                    cls._instance._processing = False
                    cls._instance._worker_thread = None
                    cls._instance._stop_event = threading.Event()
        return cls._instance

    def add_task(self, subject: str, params_dict: Dict = None,
                 priority: int = TaskPriority.NORMAL.value,
                 max_retries: int = 3) -> BatchTask:
        """Add a new task to the batch queue"""
        task = BatchTask(
            subject=subject,
            params_dict=params_dict or {},
            priority=priority,
            max_retries=max_retries,
        )
        self._tasks[task.task_id] = task
        self._queue.put((priority, time.time(), task.task_id))
        logger.info(f"Batch task queued: {task.task_id} - '{subject[:50]}...' (priority={priority})")
        return task

    def add_batch(self, subjects: List[str], params_dict: Dict = None,
                  priority: int = TaskPriority.NORMAL.value) -> List[BatchTask]:
        """Add multiple tasks at once"""
        tasks = []
        for subject in subjects:
            if subject.strip():
                task = self.add_task(subject.strip(), params_dict, priority)
                tasks.append(task)
        logger.info(f"Batch of {len(tasks)} tasks added to queue")
        return tasks

    def start_processing(self, on_complete: Callable = None, on_error: Callable = None):
        """Start processing the queue in background"""
        if self._processing:
            logger.warning("Queue is already processing")
            return
        self._processing = True
        self._stop_event.clear()
        self._worker_thread = threading.Thread(
            target=self._process_queue,
            args=(on_complete, on_error),
            daemon=True
        )
        self._worker_thread.start()
        logger.info("Batch queue processing started")

    def stop_processing(self):
        """Stop processing the queue"""
        self._stop_event.set()
        self._processing = False
        if self._worker_thread:
            self._worker_thread.join(timeout=5)
        logger.info("Batch queue processing stopped")

    def _process_queue(self, on_complete: Callable, on_error: Callable):
        """Process tasks from the queue"""
        max_concurrent = config.app.get("max_concurrent_tasks", 5)
        active_threads = []
        completed_count = 0
        failed_count = 0
        total_count = len(self._tasks)

        while not self._stop_event.is_set():
            # Check if all tasks are done
            pending = [t for t in self._tasks.values()
                       if t.status == BatchStatus.PENDING.value]
            processing = [t for t in self._tasks.values()
                         if t.status == BatchStatus.PROCESSING.value]

            if not pending and not processing:
                break

            # Start new tasks if we have capacity
            while len(active_threads) < max_concurrent and pending:
                task = pending.pop(0)
                self._execute_task(task, on_complete, on_error)
                active_threads.append(task.task_id)

            # Clean up completed threads
            active_threads = [tid for tid in active_threads
                             if self._tasks[tid].status == BatchStatus.PROCESSING.value]

            time.sleep(0.5)

        logger.info(f"Batch processing complete: {completed_count}/{total_count} succeeded, {failed_count} failed")

    def _execute_task(self, task: BatchTask, on_complete: Callable, on_error: Callable):
        """Execute a single task in a background thread"""
        task.status = BatchStatus.PROCESSING.value
        task.started_at = time.time()

        def run():
            try:
                from app.models.schema import VideoParams
                params = VideoParams(**task.params_dict) if task.params_dict else VideoParams(video_subject=task.subject)

                result = tm.start(task_id=task.task_id, params=params)
                if result and "videos" in result:
                    task.status = BatchStatus.COMPLETED.value
                    task.result = result
                    task.completed_at = time.time()
                    task.progress = 100
                    logger.success(f"Batch task completed: {task.task_id} - '{task.subject[:50]}'")
                    if on_complete:
                        on_complete(task)
                else:
                    raise Exception("Video generation returned no videos")
            except Exception as e:
                task.retry_count += 1
                task.error_message = str(e)
                if task.retry_count < task.max_retries:
                    logger.warning(f"Batch task retry {task.retry_count}/{task.max_retries}: {task.task_id}")
                    task.status = BatchStatus.PENDING.value
                    self._queue.put((task.priority, time.time(), task.task_id))
                else:
                    task.status = BatchStatus.FAILED.value
                    task.completed_at = time.time()
                    logger.error(f"Batch task failed: {task.task_id} - {e}")
                    if on_error:
                        on_error(task)

        thread = threading.Thread(target=run, daemon=True)
        thread.start()

    def get_task(self, task_id: str) -> Optional[BatchTask]:
        """Get a specific task"""
        return self._tasks.get(task_id)

    def get_all_tasks(self) -> List[Dict]:
        """Get all tasks as dicts"""
        return [self._task_to_dict(t) for t in self._tasks.values()]

    def get_tasks_by_status(self, status: str) -> List[Dict]:
        """Get tasks filtered by status"""
        return [self._task_to_dict(t) for t in self._tasks.values()
                if t.status == status]

    def get_stats(self) -> Dict:
        """Get queue statistics"""
        tasks = list(self._tasks.values())
        return {
            "total": len(tasks),
            "pending": len([t for t in tasks if t.status == BatchStatus.PENDING.value]),
            "processing": len([t for t in tasks if t.status == BatchStatus.PROCESSING.value]),
            "completed": len([t for t in tasks if t.status == BatchStatus.COMPLETED.value]),
            "failed": len([t for t in tasks if t.status == BatchStatus.FAILED.value]),
            "cancelled": len([t for t in tasks if t.status == BatchStatus.CANCELLED.value]),
        }

    def cancel_task(self, task_id: str) -> bool:
        """Cancel a pending or processing task"""
        task = self._tasks.get(task_id)
        if task and task.status in [BatchStatus.PENDING.value, BatchStatus.PROCESSING.value]:
            task.status = BatchStatus.CANCELLED.value
            task.completed_at = time.time()
            logger.info(f"Batch task cancelled: {task_id}")
            return True
        return False

    def clear_completed(self):
        """Remove completed and failed tasks from memory"""
        to_remove = [tid for tid, t in self._tasks.items()
                     if t.status in [BatchStatus.COMPLETED.value, BatchStatus.FAILED.value, BatchStatus.CANCELLED.value]]
        for tid in to_remove:
            del self._tasks[tid]
        logger.info(f"Cleared {len(to_remove)} completed/failed tasks from batch queue")

    def _task_to_dict(self, task: BatchTask) -> Dict:
        """Convert BatchTask to dictionary for JSON serialization"""
        return {
            "task_id": task.task_id,
            "subject": task.subject,
            "priority": task.priority,
            "status": task.status,
            "retry_count": task.retry_count,
            "max_retries": task.max_retries,
            "error_message": task.error_message,
            "result": task.result,
            "created_at": task.created_at,
            "started_at": task.started_at,
            "completed_at": task.completed_at,
            "progress": task.progress,
            "duration": task.completed_at - task.started_at if task.started_at else 0,
        }


# Global batch queue instance
batch_queue = BatchQueue()
