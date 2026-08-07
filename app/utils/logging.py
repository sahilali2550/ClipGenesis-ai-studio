import json
import os
import sys
from typing import Optional, Dict, Any
from loguru import logger
from app.config import config


def structured_log(
    task_id: str = "",
    stage: str = "init",
    status: str = "success",
    model: str = "",
    duration: float = 0.0,
    message: str = "",
    extra: Optional[Dict[str, Any]] = None,
):
    """
    Structured JSON logger for production metrics and tracking generation stages.
    """
    log_event = {
        "task_id": task_id,
        "stage": stage,
        "status": status,
        "model": model,
        "duration": duration,
        "message": message,
    }
    if extra:
        log_event.update(extra)

    # Format JSON payload
    json_str = json.dumps(log_event, ensure_ascii=False)
    
    if status == "error" or status == "failed":
        logger.error(f"[STRUCTURED_LOG] {json_str}")
    elif status == "warning":
        logger.warning(f"[STRUCTURED_LOG] {json_str}")
    else:
        logger.info(f"[STRUCTURED_LOG] {json_str}")

    return log_event
