import threading
from typing import Dict
from loguru import logger


class ConcurrencyController:
    """Limits concurrent video rendering tasks to respect local system limits."""

    def __init__(self, max_concurrent: int = 1):
        self.max_concurrent = max_concurrent
        self.semaphore = threading.Semaphore(max_concurrent)
        self.active_count = 0
        self._lock = threading.Lock()

    def acquire(self) -> bool:
        acquired = self.semaphore.acquire(blocking=True)
        if acquired:
            with self._lock:
                self.active_count += 1
        return acquired

    def release(self):
        with self._lock:
            if self.active_count > 0:
                self.active_count -= 1
        self.semaphore.release()


_global_queue_controller = ConcurrencyController(max_concurrent=1)


def get_queue_controller(max_concurrent: int = 1) -> ConcurrencyController:
    global _global_queue_controller
    if _global_queue_controller.max_concurrent != max_concurrent:
        _global_queue_controller = ConcurrencyController(max_concurrent=max_concurrent)
    return _global_queue_controller
