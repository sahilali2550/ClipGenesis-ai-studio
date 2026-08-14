import json
import math
import os.path
import re
import shutil
from datetime import datetime
from os import path

from loguru import logger

from app.config import config
from app.models import const
from app.models.schema import VideoConcatMode, VideoParams, VideoAspect
from app.services import llm, material, subtitle, video, voice
from app.services import state as sm
from app.utils import utils


def generate_script(task_id, params):
    logger.info("\n\n## generating video script")
    video_script = params.video_script.strip()
    if not video_script:
        video_script = llm.generate_script(
            video_subject=params.video_subject,
            language=params.video_language,
            paragraph_number=params.paragraph_number,
        )
    else:
        logger.debug(f"video script: \n{video_script}")

    if not video_script:
        sm.state.update_task(task_id, state=const.TASK_STATE_FAILED)
        logger.error("failed to generate video script.")
        return None

    return video_script


def generate_terms(task_id, params, video_script):
    logger.info("\n\n## generating video terms")
    video_terms = params.video_terms
    if not video_terms:
        video_terms = llm.generate_terms(
            video_subject=params.video_subject, video_script=video_script, amount=5
        )
    else:
        if isinstance(video_terms, str):
            video_terms = [term.strip() for term in re.split(r"[,，]", video_terms)]
        elif isinstance(video_terms, list):
            video_terms = [term.strip() for term in video_terms]
        else:
            raise ValueError("video_terms must be a string or a list of strings.")

        logger.debug(f"video terms: {utils.to_json(video_terms)}")

    if not video_terms:
        sm.state.update_task(task_id, state=const.TASK_STATE_FAILED)
        logger.error("failed to generate video terms.")
        return None

    return video_terms


def save_script_data(task_id, video_script, video_terms, params):
    script_file = path.join(utils.task_dir(task_id), "script.json")
    script_data = {
        "script": video_script,
        "search_terms": video_terms,
        "params": params,
    }

    with open(script_file, "w", encoding="utf-8") as f:
        f.write(utils.to_json(script_data))


def generate_audio(task_id, params, video_script):
    logger.info("\n\n## generating audio")
    audio_file = path.join(utils.task_dir(task_id), "audio.mp3")
    sub_maker = voice.tts(
        text=video_script,
        voice_name=voice.parse_voice_name(params.voice_name),
        voice_rate=params.voice_rate,
        voice_file=audio_file,
    )
    if sub_maker is None:
        sm.state.update_task(task_id, state=const.TASK_STATE_FAILED)
        logger.error(
            """failed to generate audio:
1. check if the language of the voice matches the language of the video script.
2. check if the network is available. If you are in China, it is recommended to use a VPN and enable the global traffic mode.
        """.strip()
        )
        return None, None, None

    # Get the actual audio file path (might be .wav if MP3 conversion failed)
    actual_audio_file = getattr(sub_maker, '_actual_audio_file', audio_file)
    if actual_audio_file != audio_file:
        logger.info(f"Audio file saved as: {actual_audio_file} (instead of {audio_file})")
        audio_file = actual_audio_file

    audio_duration = math.ceil(voice.get_audio_duration(sub_maker))
    return audio_file, audio_duration, sub_maker


def generate_subtitle(task_id, params, video_script, sub_maker, audio_file):
    if not params.subtitle_enabled:
        return ""

    subtitle_path = path.join(utils.task_dir(task_id), "subtitle.srt")
    subtitle_provider = config.app.get("subtitle_provider", "edge").strip().lower()
    logger.info(f"\n\n## generating subtitle, provider: {subtitle_provider}")

    # Check if Chatterbox TTS was used by examining the voice name
    is_chatterbox = voice.is_chatterbox_voice(params.voice_name)
    
    subtitle_fallback = False
    if subtitle_provider == "edge":
        if is_chatterbox and sub_maker and sub_maker.subs:
            # Use specialized Chatterbox subtitle function for word-level timestamps
            logger.info("Using Chatterbox-optimized subtitle generation")
            voice.create_chatterbox_subtitle(
                sub_maker=sub_maker, text=video_script, subtitle_file=subtitle_path
            )
        elif sub_maker and sub_maker.subs:
            # Detect if edge-tts returned SentenceBoundary (7.2+) vs WordBoundary (<=7.0)
            # SentenceBoundary: full sentences (~avg >15 chars per sub)
            # WordBoundary:     individual words (~avg <8 chars per sub)
            avg_sub_len = sum(len(s) for s in sub_maker.subs) / len(sub_maker.subs)
            is_sentence_level = avg_sub_len >= 15

            if is_sentence_level:
                # edge-tts 7.2+: sentence-level chunks — use Chatterbox subtitle fn
                # which already handles sentence-level timestamps perfectly
                logger.info(
                    f"Detected SentenceBoundary chunks (avg len={avg_sub_len:.1f}), "
                    "using sentence-level subtitle generation"
                )
                voice.create_chatterbox_subtitle(
                    sub_maker=sub_maker, text=video_script, subtitle_file=subtitle_path
                )
            else:
                # edge-tts <=7.0: word-level chunks — use original word-matching logic
                logger.info(
                    f"Detected WordBoundary chunks (avg len={avg_sub_len:.1f}), "
                    "using word-matching subtitle generation"
                )
                voice.create_subtitle(
                    text=video_script, sub_maker=sub_maker, subtitle_file=subtitle_path
                )
        else:
            # Fallback: no sub data at all
            voice.create_subtitle(
                text=video_script, sub_maker=sub_maker, subtitle_file=subtitle_path
            )
        
        if not os.path.exists(subtitle_path):
            subtitle_fallback = True
            logger.warning("subtitle file not found, fallback to whisper")

    if subtitle_provider == "whisper" or subtitle_fallback:
        subtitle.create(audio_file=audio_file, subtitle_file=subtitle_path)
        logger.info("\n\n## correcting subtitle")
        subtitle.correct(subtitle_file=subtitle_path, video_script=video_script)

    # Generate enhanced subtitles if word highlighting is enabled
    if getattr(params, 'enable_word_highlighting', False):
        logger.info("\n\n## generating enhanced subtitles for word highlighting")
        enhanced_subtitle_path = path.join(utils.task_dir(task_id), "subtitle_enhanced.json")
        enhanced_subtitles = subtitle.create_enhanced_subtitles(
            audio_file=audio_file, 
            subtitle_file=enhanced_subtitle_path,
            params=params
        )
        if enhanced_subtitles:
            # Store both paths for later use
            params._enhanced_subtitle_path = enhanced_subtitle_path
            logger.info(f"enhanced subtitles created: {enhanced_subtitle_path}")

    subtitle_lines = subtitle.file_to_subtitles(subtitle_path)
    if not subtitle_lines:
        logger.warning(f"subtitle file is invalid: {subtitle_path}")
        return ""

    return subtitle_path


def get_video_materials(task_id, params, video_terms, audio_duration):
    if params.video_source == "local":
        logger.info("\n\n## preprocess local materials")
        materials = video.preprocess_video(
            materials=params.video_materials, clip_duration=params.video_clip_duration
        )
        if not materials:
            sm.state.update_task(task_id, state=const.TASK_STATE_FAILED)
            logger.error(
                "no valid materials found, please check the materials and try again."
            )
            return None
        return [material_info.url for material_info in materials]
    else:
        logger.info(f"\n\n## downloading videos from {params.video_source}")
        if isinstance(video_terms, str):
            clean_terms = [t.strip() for t in video_terms.split(",") if t.strip()]
        else:
            clean_terms = video_terms

        downloaded_videos = material.download_videos(
            task_id=task_id,
            search_terms=clean_terms,
            source=params.video_source,
            video_aspect=params.video_aspect,
            video_contact_mode=params.video_concat_mode,
            audio_duration=audio_duration * params.video_count,
            max_clip_duration=params.video_clip_duration,
        )
        if not downloaded_videos:
            sm.state.update_task(task_id, state=const.TASK_STATE_FAILED)
            logger.error(
                "failed to download videos, maybe the network is not available. if you are in China, please use a VPN."
            )
            return None
        return downloaded_videos


def generate_final_videos(
    task_id, params, downloaded_videos, audio_file, subtitle_path, video_script=""
):
    final_video_paths = []
    combined_video_paths = []
    
    # Force random mode for multiple videos to ensure variety
    # Semantic mode would produce identical videos, which doesn't make sense for multiple generation
    video_concat_mode = params.video_concat_mode
    if params.video_count > 1 and video_concat_mode.value == "semantic":
        logger.info(f"🔄 Multiple videos requested ({params.video_count}), forcing random concatenation mode for variety")
        logger.info("   ℹ️  Semantic mode would produce identical videos, which is not useful for multiple generation")
        video_concat_mode = VideoConcatMode.random
    
    video_transition_mode = params.video_transition_mode

    _progress = 50
    for i in range(params.video_count):
        index = i + 1
        combined_video_path = path.join(
            utils.task_dir(task_id), f"combined-{index}.mp4"
        )
        logger.info(f"\n\n## combining video: {index} => {combined_video_path}")
        video.combine_videos(
            combined_video_path=combined_video_path,
            video_paths=downloaded_videos,
            audio_file=audio_file,
            video_aspect=params.video_aspect,
            video_concat_mode=video_concat_mode,
            video_transition_mode=video_transition_mode,
            max_clip_duration=params.video_clip_duration,
            threads=params.n_threads,
            script=video_script,
            params=params,
        )

        _progress += 50 / params.video_count / 2
        sm.state.update_task(task_id, progress=_progress)

        final_video_path = path.join(utils.task_dir(task_id), f"final-{index}.mp4")

        logger.info(f"\n\n## generating video: {index} => {final_video_path}")
        video.generate_video(
            video_path=combined_video_path,
            audio_path=audio_file,
            subtitle_path=subtitle_path,
            output_file=final_video_path,
            params=params,
            video_script=video_script,
        )

        _progress += 50 / params.video_count / 2
        sm.state.update_task(task_id, progress=_progress)

        final_video_paths.append(final_video_path)
        combined_video_paths.append(combined_video_path)

    return final_video_paths, combined_video_paths


def start(task_id, params: VideoParams, stop_at: str = "video"):
    logger.info(f"start task: {task_id}, stop_at: {stop_at}")
    sm.state.update_task(task_id, state=const.TASK_STATE_PROCESSING, progress=5)

    if type(params.video_concat_mode) is str:
        params.video_concat_mode = VideoConcatMode(params.video_concat_mode)

    # 1. Generate script
    video_script = generate_script(task_id, params)
    if not video_script or "Error: " in video_script:
        sm.state.update_task(task_id, state=const.TASK_STATE_FAILED)
        return

    sm.state.update_task(task_id, state=const.TASK_STATE_PROCESSING, progress=10)

    if stop_at == "script":
        sm.state.update_task(
            task_id, state=const.TASK_STATE_COMPLETE, progress=100, script=video_script
        )
        return {"script": video_script}

    # 2. Generate terms
    video_terms = ""
    if params.video_source != "local":
        video_terms = generate_terms(task_id, params, video_script)
        if not video_terms:
            sm.state.update_task(task_id, state=const.TASK_STATE_FAILED)
            return

    save_script_data(task_id, video_script, video_terms, params)

    if stop_at == "terms":
        sm.state.update_task(
            task_id, state=const.TASK_STATE_COMPLETE, progress=100, terms=video_terms
        )
        return {"script": video_script, "terms": video_terms}

    sm.state.update_task(task_id, state=const.TASK_STATE_PROCESSING, progress=20)

    # 3. Generate audio
    audio_file, audio_duration, sub_maker = generate_audio(
        task_id, params, video_script
    )
    if not audio_file:
        sm.state.update_task(task_id, state=const.TASK_STATE_FAILED)
        return

    sm.state.update_task(task_id, state=const.TASK_STATE_PROCESSING, progress=30)

    if stop_at == "audio":
        sm.state.update_task(
            task_id,
            state=const.TASK_STATE_COMPLETE,
            progress=100,
            audio_file=audio_file,
        )
        return {"audio_file": audio_file, "audio_duration": audio_duration}

    # 4. Generate subtitle
    subtitle_path = generate_subtitle(
        task_id, params, video_script, sub_maker, audio_file
    )

    if stop_at == "subtitle":
        sm.state.update_task(
            task_id,
            state=const.TASK_STATE_COMPLETE,
            progress=100,
            subtitle_path=subtitle_path,
        )
        return {"subtitle_path": subtitle_path}

    sm.state.update_task(task_id, state=const.TASK_STATE_PROCESSING, progress=40)

    # 5. Get video materials
    downloaded_videos = get_video_materials(
        task_id, params, video_terms, audio_duration
    )
    if not downloaded_videos:
        sm.state.update_task(task_id, state=const.TASK_STATE_FAILED)
        return

    if stop_at == "materials":
        sm.state.update_task(
            task_id,
            state=const.TASK_STATE_COMPLETE,
            progress=100,
            materials=downloaded_videos,
        )
        return {"materials": downloaded_videos}

    sm.state.update_task(task_id, state=const.TASK_STATE_PROCESSING, progress=50)

    # 6. Generate final videos
    final_video_paths, combined_video_paths = generate_final_videos(
        task_id, params, downloaded_videos, audio_file, subtitle_path, video_script
    )

    if not final_video_paths:
        sm.state.update_task(task_id, state=const.TASK_STATE_FAILED)
        return

    # Save to dedicated section folder storage/general_videos/
    general_out_dir = path.join(utils.root_dir(), "storage", "general_videos")
    os.makedirs(general_out_dir, exist_ok=True)
    saved_general_videos = []
    import shutil
    for idx_v, f_path in enumerate(final_video_paths):
        if path.exists(f_path):
            sec_path = path.join(general_out_dir, f"video_{task_id[:8]}_{idx_v+1}.mp4")
            shutil.copy(f_path, sec_path)
            saved_general_videos.append(sec_path)
            logger.info(f"📁 Video saved to dedicated section folder: {sec_path}")

    # ── Project Output Management (STEP 5) ───────────────────────────
    project_dir = path.join(utils.root_dir(), "storage", "projects", task_id)
    os.makedirs(project_dir, exist_ok=True)

    dest_video = path.join(project_dir, "video.mp4")
    if final_video_paths and path.exists(final_video_paths[0]):
        shutil.copy(final_video_paths[0], dest_video)

    # Save Storyboard & Timeline JSON
    try:
        from storyboard.planner import create_storyboard_project
        sb_project = create_storyboard_project(
            topic=params.video_subject or "Untitled Video",
            script=video_script or "",
            template_id=getattr(params, "template_id", "youtube_short"),
            brand_id=getattr(params, "brand_id", None)
        )
        with open(path.join(project_dir, "storyboard.json"), "w", encoding="utf-8") as f:
            f.write(sb_project.model_dump_json(indent=2))
        with open(path.join(project_dir, "timeline.json"), "w", encoding="utf-8") as f:
            f.write(sb_project.timeline.model_dump_json(indent=2))
    except Exception as e:
        logger.warning(f"Could not save storyboard for project {task_id}: {e}")

    # Generate Thumbnail Collection & copy primary thumbnail.jpg
    dest_thumb = path.join(project_dir, "thumbnail.jpg")
    try:
        from thumbnail.manager import create_video_thumbnails
        tb_collection = create_video_thumbnails(
            source_video=dest_video if path.exists(dest_video) else final_video_paths[0],
            title_text=params.video_subject or "ClipGenesis Output",
            subtitle_text=video_script[:40] if video_script else "",
            brand_id=getattr(params, "brand_id", None),
            template_id=getattr(params, "template_id", "youtube_short"),
            num_variants=3,
            output_dir=project_dir
        )
        if tb_collection.variants and path.exists(tb_collection.variants[0].output_path):
            shutil.copy(tb_collection.variants[0].output_path, dest_thumb)
    except Exception as e:
        logger.warning(f"Could not save thumbnail for project {task_id}: {e}")

    # Save metadata.json
    metadata = {
        "task_id": task_id,
        "video_subject": params.video_subject,
        "video_script": video_script,
        "video_terms": video_terms,
        "voice_name": params.voice_name,
        "video_aspect": str(params.video_aspect),
        "video_concat_mode": str(params.video_concat_mode),
        "video_source": params.video_source,
        "template_id": getattr(params, "template_id", "youtube_short"),
        "brand_id": getattr(params, "brand_id", None),
        "created_at": datetime.now().isoformat(),
        "project_dir": project_dir,
        "video_path": dest_video if path.exists(dest_video) else final_video_paths[0],
        "thumbnail_path": dest_thumb if path.exists(dest_thumb) else None
    }
    with open(path.join(project_dir, "metadata.json"), "w", encoding="utf-8") as f:
        f.write(utils.to_json(metadata))

    logger.success(f"📦 Saved complete project output folder -> {project_dir}")

    logger.success(
        f"task {task_id} finished, generated {len(final_video_paths)} videos."
    )
    import gc
    gc.collect()

    kwargs = {
        "videos": final_video_paths,
        "combined_videos": combined_video_paths,
        "script": video_script,
        "terms": video_terms,
        "audio_file": audio_file,
        "audio_duration": audio_duration,
        "subtitle_path": subtitle_path,
        "materials": downloaded_videos,
    }
    sm.state.update_task(
        task_id, state=const.TASK_STATE_COMPLETE, progress=100, **kwargs
    )
    return kwargs


def get_unfinished_tasks() -> list:
    """
    Scan storage/tasks/* for interrupted video generation tasks
    where any files exist in the task folder but no completed MP4 video exists.
    Returns a list of dicts.
    """
    unfinished = []
    tasks_dir = path.join(utils.root_dir(), "storage", "tasks")
    if not path.exists(tasks_dir):
        return []

    for item in os.listdir(tasks_dir):
        folder_path = path.join(tasks_dir, item)
        if path.isdir(folder_path):
            all_files = os.listdir(folder_path)
            mp4_files = [f for f in all_files if f.endswith(".mp4") and not f.startswith("raw_") and path.getsize(path.join(folder_path, f)) > 1000]
            
            # If folder has files and no finished MP4, it IS an unfinished task!
            if all_files and not mp4_files:
                audio_p = path.join(folder_path, "audio.mp3")
                srt_p = path.join(folder_path, "subtitle.srt")
                script_p = path.join(folder_path, "script.json")

                subject = "5 Most Disturbing & Mysterious Places on Earth"
                terms = ""
                if path.exists(script_p):
                    try:
                        with open(script_p, "r", encoding="utf-8") as sf:
                            s_data = json.load(sf)
                            subject = s_data.get("video_subject") or s_data.get("subject") or subject
                            terms = s_data.get("video_terms") or ""
                    except Exception:
                        pass

                created_ts = path.getmtime(folder_path)
                dt_str = datetime.fromtimestamp(created_ts).strftime("%Y-%m-%d %H:%M")
                unfinished.append({
                    "task_id": item,
                    "subject": subject,
                    "folder_path": folder_path,
                    "audio_file": audio_p if path.exists(audio_p) and path.getsize(audio_p) > 5000 else "",
                    "srt_file": srt_p if path.exists(srt_p) else "",
                    "terms": terms,
                    "created_at": dt_str,
                })

    unfinished.sort(key=lambda x: x.get("created_at", ""), reverse=True)
    return unfinished


def resume_task(task_id: str) -> dict:
    """
    Resume an interrupted video generation task:
    Reuses existing audio.mp3, subtitle.srt, and script.json if valid, or auto-generates missing parts.
    """
    logger.info(f"🔄 Resuming unfinished task: {task_id}")
    task_dir = path.join(utils.root_dir(), "storage", "tasks", task_id)
    if not path.exists(task_dir):
        raise RuntimeError(f"Task folder not found: {task_id}")

    audio_file = path.join(task_dir, "audio.mp3")
    subtitle_path = path.join(task_dir, "subtitle.srt")
    script_p = path.join(task_dir, "script.json")

    subject = "5 Most Disturbing & Mysterious Places on Earth"
    terms = "mysterious, dark, aesthetic, scary places"
    video_script = ""
    aspect_ratio = "portrait"
    voice_name = "en-US-ChristopherNeural"

    if path.exists(script_p):
        try:
            with open(script_p, "r", encoding="utf-8") as sf:
                s_data = json.load(sf)
                subject = s_data.get("video_subject") or subject
                terms = s_data.get("video_terms") or terms
                video_script = s_data.get("video_script") or ""
                aspect_ratio = s_data.get("video_aspect") or "portrait"
                voice_name = s_data.get("voice_name") or voice_name
        except Exception as e:
            logger.warning(f"Resume script parse warning: {e}")

    params = VideoParams(
        video_subject=subject,
        video_script=video_script,
        video_terms=terms,
        video_aspect=VideoAspect(aspect_ratio),
        video_concat_mode=VideoConcatMode.random,
        video_source="hybrid",
        voice_name=voice_name,
    )

    # 1. Ensure valid script exists
    if not video_script or len(video_script.strip()) < 10:
        logger.info(f"📝 Script missing in task {task_id}. Generating script for '{subject}'...")
        video_script = llm.generate_script(video_subject=subject, language="")
        params.video_script = video_script
        terms = llm.generate_terms(subject, video_script)
        params.video_terms = ", ".join(terms) if terms else terms
        save_script_data(task_id, video_script, params.video_terms, params)

    # 2. Ensure valid audio.mp3 (>5KB) exists
    valid_audio = path.exists(audio_file) and path.getsize(audio_file) > 5000
    if not valid_audio:
        logger.info(f"🔊 Audio file missing/corrupted in task {task_id}. Generating audio...")
        audio_file, audio_duration, sub_maker = generate_audio(task_id, params, video_script)
        subtitle_path = generate_subtitle(task_id, params, video_script, sub_maker, audio_file)

    audio_duration = 30.0
    if path.exists(audio_file) and path.getsize(audio_file) > 5000:
        try:
            from moviepy.audio.io.AudioFileClip import AudioFileClip
            ac = AudioFileClip(audio_file)
            audio_duration = ac.duration
            ac.close()
        except Exception as ac_err:
            logger.warning(f"Audio duration check error: {ac_err}")

    # 3. Fetch 4K background materials & render final video
    downloaded_videos = get_video_materials(
        task_id, params, params.video_terms, audio_duration
    )
    if not downloaded_videos:
        raise RuntimeError(f"Could not fetch background videos for resumed task {task_id}")

    final_video_paths, combined_video_paths = generate_final_videos(
        task_id, params, downloaded_videos, audio_file, subtitle_path
    )

    return {
        "videos": final_video_paths,
        "combined_videos": combined_video_paths,
        "script": video_script,
        "audio_file": audio_file,
    }


if __name__ == "__main__":
    task_id = "task_id"
    params = VideoParams(
        video_subject="金钱的作用",
        voice_name="zh-CN-XiaoyiNeural-Female",
        voice_rate=1.0,
    )
    start(task_id, params, stop_at="video")
