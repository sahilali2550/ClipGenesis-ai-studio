import threading
import uuid
from typing import Callable, Optional
from loguru import logger
from batch.schemas import BatchJob, BatchTaskItem, BatchTaskStatus
from batch.queue import get_queue_controller
from app.models.schema import VideoParams, VideoAspect
from brand import merge_template_and_brand


def process_single_item(
    item: BatchTaskItem,
    render_func: Optional[Callable[[VideoParams], str]] = None
) -> BatchTaskItem:
    """Processes a single batch video item safely."""
    item.status = BatchTaskStatus.RUNNING
    logger.info(f"Processing batch task: {item.task_id} (Topic: {item.topic})")

    try:
        # Build base VideoParams
        params = VideoParams(
            video_subject=item.topic,
            video_script=item.script or "",
            video_aspect=VideoAspect.portrait,
            video_clip_duration=5,
        )
        if item.voice_name:
            params.voice_name = item.voice_name

        # Merge Template and Brand Kit
        params = merge_template_and_brand(
            item.template or "",
            item.brand or "",
            params
        )

        if render_func:
            output_path = render_func(params)
            item.output_video = output_path
        else:
            # Simulated / Mock renderer for tests or pipeline wrapper
            item.output_video = f"/outputs/batch_{item.task_id}.mp4"

        item.status = BatchTaskStatus.COMPLETED
        logger.info(f"Batch task completed: {item.task_id}")

    except Exception as e:
        item.status = BatchTaskStatus.FAILED
        item.error_message = str(e)
        logger.error(f"Batch task failed: {item.task_id} — {e}")

    return item


def process_batch_job(
    job: BatchJob,
    render_func: Optional[Callable[[VideoParams], str]] = None,
    run_async: bool = False
) -> BatchJob:
    """Processes all items in a batch job sequentially or via queue controller."""
    job.status = BatchTaskStatus.RUNNING
    controller = get_queue_controller(job.max_concurrent)

    def _execute():
        for item in job.items:
            controller.acquire()
            try:
                process_single_item(item, render_func=render_func)
                if item.status == BatchTaskStatus.COMPLETED:
                    job.completed_count += 1
                else:
                    job.failed_count += 1
            finally:
                controller.release()

        if job.failed_count == len(job.items) and len(job.items) > 0:
            job.status = BatchTaskStatus.FAILED
        else:
            job.status = BatchTaskStatus.COMPLETED
        logger.info(f"Batch job complete: {job.batch_id} (Completed: {job.completed_count}, Failed: {job.failed_count})")

    if run_async:
        thread = threading.Thread(target=_execute, daemon=True)
        thread.start()
    else:
        _execute()

    return job
