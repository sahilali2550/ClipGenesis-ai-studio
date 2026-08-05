import os
import random
import subprocess
import threading
from typing import List
from urllib.parse import urlencode

import requests
from loguru import logger
from moviepy.video.io.VideoFileClip import VideoFileClip

from app.config import config
from app.models.schema import MaterialInfo, VideoAspect, VideoConcatMode
from app.utils import utils
from app.services import semantic_video

_requested_count = 0
_requested_count_lock = threading.Lock()


def get_api_key(cfg_key: str) -> str:
    api_keys = config.app.get(cfg_key)
    if not api_keys:
        logger.warning(f"API key for '{cfg_key}' is not configured.")
        return ""

    if isinstance(api_keys, str):
        key = api_keys
    elif isinstance(api_keys, list) and api_keys:
        global _requested_count
        with _requested_count_lock:
            _requested_count += 1
            key = str(api_keys[_requested_count % len(api_keys)])
    else:
        return ""

    key = key.replace("[", "").replace("]", "").replace("'", "").replace('"', "").strip()
    return key


def clear_video_cache(max_keep: int = 0):
    """
    Clean up old downloaded video files, temporary clips, and free memory.
    """
    import glob
    import gc
    import shutil
    import time

    cache_dir = utils.storage_dir("cache_videos")
    temp_dir = utils.storage_dir("temp")
    tasks_dir = utils.storage_dir("tasks")

    for d in [cache_dir, temp_dir]:
        if os.path.exists(d):
            for f in glob.glob(os.path.join(d, "*")):
                try:
                    if os.path.isfile(f) or os.path.islink(f):
                        os.remove(f)
                    elif os.path.isdir(f):
                        shutil.rmtree(f, ignore_errors=True)
                except Exception as e:
                    logger.warning(f"Error removing cache file {f}: {e}")

    if os.path.exists(tasks_dir):
        now = time.time()
        for item in os.listdir(tasks_dir):
            item_path = os.path.join(tasks_dir, item)
            if os.path.isdir(item_path):
                try:
                    if now - os.path.getmtime(item_path) > 3600:
                        shutil.rmtree(item_path, ignore_errors=True)
                except Exception:
                    pass

    gc.collect()
    logger.info("🧹 Memory & Video cache purged. Ready for fresh video generation.")


def search_videos_pexels(
    search_term: str,
    minimum_duration: int,
    video_aspect: VideoAspect = VideoAspect.portrait,
    page: int = 0,
) -> List[MaterialInfo]:
    aspect = VideoAspect(video_aspect)
    video_orientation = aspect.name
    video_width, video_height = aspect.to_resolution()
    api_key = get_api_key("pexels_api_keys")
    headers = {
        "Authorization": api_key,
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36",
    }
    
    # Pick a random page if not specified to get fresh videos every time
    if page <= 0:
        page = random.randint(1, 10)

    # Build URL with page parameter
    params = {"query": search_term, "per_page": 20, "orientation": video_orientation, "page": page}
    query_url = f"https://api.pexels.com/videos/search?{urlencode(params)}"
    logger.info(f"searching videos (page {page}): {query_url}, with proxies: {config.proxy}")

    try:
        r = requests.get(
            query_url,
            headers=headers,
            proxies=config.proxy,
            timeout=(30, 60),
        )
        response = r.json()
        video_items = []
        videos = response.get("videos", [])
        
        # Fallback to page 1 if random page had no videos
        if not videos and page > 1:
            params["page"] = 1
            query_url = f"https://api.pexels.com/videos/search?{urlencode(params)}"
            logger.info(f"fallback searching page 1 videos: {query_url}")
            r = requests.get(query_url, headers=headers, proxies=config.proxy, timeout=(30, 60))
            videos = r.json().get("videos", [])

        if not videos:
            logger.error(f"search videos failed or empty: {response}")
            return video_items

        # loop through each video in the result
        for v in videos:
            duration = v["duration"]
            # check if video has desired minimum duration
            if duration < minimum_duration:
                continue
            video_files = v["video_files"]
            # loop through each url to determine the best quality
            for video in video_files:
                w = int(video["width"])
                h = int(video["height"])
                if w == video_width and h == video_height:
                    item = MaterialInfo()
                    item.provider = "pexels"
                    item.url = video["link"]
                    item.duration = duration
                    
                    # Capture image data for similarity comparison
                    if "image" in v:
                        item.thumbnail_url = v["image"]
                    
                    if "video_pictures" in v:
                        item.preview_images = [pic["picture"] for pic in v["video_pictures"]]
                    
                    video_items.append(item)
                    break
                    
        # Shuffle returned items for maximum randomness
        random.shuffle(video_items)
        return video_items
    except Exception as e:
        logger.error(f"search videos failed: {str(e)}")

    return []


def search_videos_pixabay(
    search_term: str,
    minimum_duration: int,
    video_aspect: VideoAspect = VideoAspect.portrait,
    page: int = 0,
) -> List[MaterialInfo]:
    aspect = VideoAspect(video_aspect)
    video_width, video_height = aspect.to_resolution()
    api_key = get_api_key("pixabay_api_keys")

    if page <= 0:
        page = random.randint(1, 6)

    # Build URL
    params = {
        "q": search_term,
        "video_type": "all",  # Accepted values: "all", "film", "animation"
        "per_page": 40,
        "key": api_key,
        "page": page,
    }
    query_url = f"https://pixabay.com/api/videos/?{urlencode(params)}"
    logger.info(f"searching videos (page {page}): {query_url}, with proxies: {config.proxy}")

    try:
        r = requests.get(
            query_url, proxies=config.proxy, timeout=(30, 60)
        )
        response = r.json()
        video_items = []
        videos = response.get("hits", [])

        if not videos and page > 1:
            params["page"] = 1
            query_url = f"https://pixabay.com/api/videos/?{urlencode(params)}"
            r = requests.get(query_url, proxies=config.proxy, timeout=(30, 60))
            videos = r.json().get("hits", [])

        if not videos:
            logger.error(f"search videos failed: {response}")
            return video_items

        # loop through each video in the result
        for v in videos:
            duration = v["duration"]
            # check if video has desired minimum duration
            if duration < minimum_duration:
                continue
            video_files = v["videos"]
            # loop through each url to determine the best quality
            for video_type in video_files:
                video = video_files[video_type]
                w = int(video["width"])
                # h = int(video["height"])
                if w >= video_width:
                    item = MaterialInfo()
                    item.provider = "pixabay"
                    item.url = video["url"]
                    item.duration = duration
                    video_items.append(item)
                    break

        random.shuffle(video_items)
        return video_items
    except Exception as e:
        logger.error(f"search videos failed: {str(e)}")

    return []


def save_video(video_url: str, save_dir: str = "", search_term: str = "", thumbnail_url: str = "", preview_images: list = None) -> str:
    if not save_dir:
        save_dir = utils.storage_dir("cache_videos")

    if not os.path.exists(save_dir):
        os.makedirs(save_dir)

    url_without_query = video_url.split("?")[0]
    url_hash = utils.md5(url_without_query)
    video_id = f"vid-{url_hash}"
    video_path = f"{save_dir}/{video_id}.mp4"

    # if video already exists, return the path
    if os.path.exists(video_path) and os.path.getsize(video_path) > 0:
        logger.info(f"video already exists: {video_path}")
        # Save metadata if search_term is provided and metadata doesn't exist
        if search_term and not semantic_video.load_video_metadata(video_path):
            additional_info = {}
            if thumbnail_url:
                additional_info["thumbnail_url"] = thumbnail_url
            if preview_images:
                additional_info["preview_images"] = preview_images
            semantic_video.save_video_metadata(video_path, search_term, additional_info)
        return video_path

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36"
    }

    # if video does not exist, download it with streaming chunks
    try:
        response = requests.get(
            video_url,
            headers=headers,
            proxies=config.proxy,
            timeout=(15, 30),
            stream=True,
        )
        response.raise_for_status()
        with open(video_path, "wb") as f:
            for chunk in response.iter_content(chunk_size=1024 * 1024):
                if chunk:
                    f.write(chunk)
    except Exception as download_err:
        logger.warning(f"Failed to download video from {video_url}: {download_err}")
        if os.path.exists(video_path):
            try:
                os.remove(video_path)
            except Exception:
                pass
        return ""

    if os.path.exists(video_path) and os.path.getsize(video_path) > 10000:
        try:
            # Fast ffprobe duration check
            duration, fps = 0.0, 0.0
            try:
                probe_cmd = [
                    "ffprobe", "-v", "error",
                    "-select_streams", "v:0",
                    "-show_entries", "stream=r_frame_rate:format=duration",
                    "-of", "default=noprint_wrappers=1:nokey=1",
                    video_path
                ]
                probe_res = subprocess.run(probe_cmd, capture_output=True, text=True, timeout=5)
                lines = probe_res.stdout.strip().split("\n")
                if len(lines) >= 2:
                    num, den = lines[0].split("/") if "/" in lines[0] else (lines[0], 1)
                    fps = float(num) / float(den) if float(den) > 0 else 30.0
                    duration = float(lines[1])
            except Exception:
                # Fallback to MoviePy clip
                clip = VideoFileClip(video_path)
                duration = clip.duration
                fps = clip.fps
                clip.close()

            if duration > 0:
                if search_term:
                    additional_info = {}
                    if thumbnail_url:
                        additional_info["thumbnail_url"] = thumbnail_url
                    if preview_images:
                        additional_info["preview_images"] = preview_images
                    semantic_video.save_video_metadata(video_path, search_term, additional_info)
                return video_path
        except Exception as e:
            try:
                os.remove(video_path)
            except Exception:
                pass
            logger.warning(f"invalid video file: {video_path} => {str(e)}")
    return ""


def download_videos(
    task_id: str,
    search_terms: List[str],
    source: str = "hybrid",
    video_aspect: VideoAspect = VideoAspect.portrait,
    video_contact_mode: VideoConcatMode = VideoConcatMode.random,
    audio_duration: float = 0.0,
    max_clip_duration: int = 5,
) -> List[str]:
    # Purge old video cache and free RAM to ensure fresh downloads every time
    try:
        clear_video_cache()
    except Exception as cache_err:
        logger.warning(f"Cache clear warning: {cache_err}")

    # Group videos by search term for balanced sampling
    videos_by_term = {}
    found_duration = 0.0

    # Global URL tracking to prevent duplicates across all search terms
    global_video_urls = set()
    src_clean = (source or "hybrid").lower().strip()
    
    for search_term in search_terms:
        video_items = []
        
        if src_clean in ["hybrid", "both", "all", "pexels_pixabay", "combined"]:
            # 🔥 Hybrid Fetching: Fetch from Pexels AND Pixabay simultaneously for maximum collection!
            items_pexels = search_videos_pexels(
                search_term=search_term,
                minimum_duration=max_clip_duration,
                video_aspect=video_aspect,
            )
            items_pixabay = search_videos_pixabay(
                search_term=search_term,
                minimum_duration=max_clip_duration,
                video_aspect=video_aspect,
            )
            video_items = items_pexels + items_pixabay
            random.shuffle(video_items)
            logger.info(f"🔥 Hybrid fetch for '{search_term}': {len(items_pexels)} Pexels + {len(items_pixabay)} Pixabay = {len(video_items)} combined videos")
        elif src_clean == "pixabay":
            items_pixabay = search_videos_pixabay(
                search_term=search_term,
                minimum_duration=max_clip_duration,
                video_aspect=video_aspect,
            )
            if len(items_pixabay) < 3:
                items_pexels = search_videos_pexels(
                    search_term=search_term,
                    minimum_duration=max_clip_duration,
                    video_aspect=video_aspect,
                )
                video_items = items_pixabay + items_pexels
                logger.info(f"Pixabay fetch ({len(items_pixabay)}) supplemented with Pexels ({len(items_pexels)}) for '{search_term}'")
            else:
                video_items = items_pixabay
                logger.info(f"Pixabay found {len(video_items)} videos for '{search_term}'")
        else: # Pexels mode
            items_pexels = search_videos_pexels(
                search_term=search_term,
                minimum_duration=max_clip_duration,
                video_aspect=video_aspect,
            )
            if len(items_pexels) < 3:
                items_pixabay = search_videos_pixabay(
                    search_term=search_term,
                    minimum_duration=max_clip_duration,
                    video_aspect=video_aspect,
                )
                video_items = items_pexels + items_pixabay
                logger.info(f"Pexels fetch ({len(items_pexels)}) supplemented with Pixabay ({len(items_pixabay)}) for '{search_term}'")
            else:
                video_items = items_pexels
                logger.info(f"Pexels found {len(video_items)} videos for '{search_term}'")

        # Filter out duplicates and associate with search term
        unique_videos = []
        duplicates_removed = 0
        
        for item in video_items:
            # Check for URL duplicates across all search terms
            if item.url not in global_video_urls:
                item.search_term = search_term
                unique_videos.append(item)
                global_video_urls.add(item.url)
                found_duration += item.duration
            else:
                duplicates_removed += 1
        
        if duplicates_removed > 0:
            logger.info(f"removed {duplicates_removed} duplicate URLs for '{search_term}'")
        
        if unique_videos:
            videos_by_term[search_term] = unique_videos

    logger.info(
        f"found videos from {len(videos_by_term)} search terms, total duration: {found_duration} seconds, required: {audio_duration} seconds"
    )
    logger.info(f"total unique video URLs: {len(global_video_urls)}")

    # Create balanced selection from all search terms
    valid_video_items = []
    valid_video_urls = set()
    
    # Round-robin selection from each search term to ensure diversity
    max_videos_per_term = max(1, int(audio_duration / max_clip_duration / len(videos_by_term)) + 1) if videos_by_term else 1
    logger.info(f"targeting max {max_videos_per_term} videos per search term for balanced selection")
    
    # Track selection statistics
    selection_stats = {}
    
    for search_term, videos in videos_by_term.items():
        # Shuffle videos within each search term
        if video_contact_mode.value == VideoConcatMode.random.value:
            random.shuffle(videos)
        
        # Take up to max_videos_per_term from this search term
        count = 0
        for item in videos:
            if item.url not in valid_video_urls and count < max_videos_per_term:
                valid_video_items.append(item)
                valid_video_urls.add(item.url)
                count += 1
        
        selection_stats[search_term] = count
        logger.info(f"selected {count} videos from '{search_term}' ({count}/{len(videos)} available)")
    
    # Final shuffle of the balanced selection
    if video_contact_mode.value == VideoConcatMode.random.value:
        random.shuffle(valid_video_items)
    
    logger.info(f"selected {len(valid_video_items)} videos for download with balanced representation")
    
    # Log diversity metrics
    logger.info("🎯 Diversity metrics:")
    logger.info(f"   📊 Search terms represented: {len(selection_stats)}/{len(search_terms)}")
    for term, count in selection_stats.items():
        percentage = (count / len(valid_video_items)) * 100 if valid_video_items else 0
        logger.info(f"   📹 '{term}': {count} videos ({percentage:.1f}%)")

    video_paths = []
    material_directory = config.app.get("material_directory", "").strip()
    if material_directory == "task":
        material_directory = utils.task_dir(task_id)
    elif material_directory and not os.path.isdir(material_directory):
        material_directory = ""

    total_duration = 0.0
    downloaded_urls = set()  # Track downloaded URLs to prevent runtime duplicates
    
    for item in valid_video_items:
        try:
            # Double-check for URL duplicates at download time
            if item.url in downloaded_urls:
                logger.warning(f"skipping duplicate URL: {item.url}")
                continue
                
            logger.info(f"downloading video: {item.url}")
            # Use the search term associated with this specific video item
            item_search_term = getattr(item, 'search_term', 'unknown')
            saved_video_path = save_video(
                video_url=item.url, save_dir=material_directory, search_term=item_search_term, thumbnail_url=item.thumbnail_url, preview_images=item.preview_images
            )
            if saved_video_path:
                logger.info(f"video saved: {saved_video_path} (search_term: '{item_search_term}')")
                video_paths.append(saved_video_path)
                downloaded_urls.add(item.url)
                seconds = min(max_clip_duration, item.duration)
                total_duration += seconds
                if total_duration > audio_duration:
                    logger.info(
                        f"total duration of downloaded videos: {total_duration} seconds, skip downloading more"
                    )
                    break
        except Exception as e:
            logger.error(f"failed to download video: {utils.to_json(item)} => {str(e)}")
    
    if not video_paths or total_duration < audio_duration:
        needed_duration = audio_duration - total_duration
        import math
        needed_clips = math.ceil(needed_duration / max_clip_duration)
        logger.warning(f"Video assets short by {needed_duration:.2f}s. Generating {needed_clips} fallback AI images...")
        
        import urllib.parse
        import uuid
        from moviepy.video.VideoClip import ImageClip
        from app.services.video import video_codec, video_bitrate, audio_bitrate, quality_params
        
        for i in range(needed_clips):
            term = search_terms[i % len(search_terms)] if search_terms else "abstract money concept"
            encoded_term = urllib.parse.quote(term + " highly detailed cinematic key visual")
            w, h = (1080, 1920) if video_aspect.value == VideoAspect.portrait.value else (1920, 1080)
            url = f"https://image.pollinations.ai/prompt/{encoded_term}?width={w}&height={h}&nologo=true"
            
            logger.info(f"Generating fallback AI image: {url}")
            try:
                response = requests.get(url, timeout=30)
                if response.status_code == 200:
                    cache_dir = utils.cache_dir()
                    os.makedirs(cache_dir, exist_ok=True)
                    img_path = os.path.join(cache_dir, f"ai_fallback_{uuid.uuid4().hex[:8]}.jpg")
                    with open(img_path, "wb") as f:
                        f.write(response.content)
                    
                    logger.success(f"Saved fallback AI image to {img_path}")
                    
                    # Convert to MP4 with dynamic zoom (ensuring even dimensions for H.264)
                    image_clip = ImageClip(img_path).with_duration(max_clip_duration)
                    w, h = image_clip.size
                    w = int(w // 2) * 2
                    h = int(h // 2) * 2
                    image_clip = image_clip.resized((w, h))
                    
                    zoom_clip = image_clip.resized(lambda t: (
                        int((w * (1.0 + 0.08 * (t / max_clip_duration))) // 2) * 2,
                        int((h * (1.0 + 0.08 * (t / max_clip_duration))) // 2) * 2
                    ))
                    
                    output_video_path = img_path + ".mp4"
                    zoom_clip.write_videofile(
                        output_video_path,
                        fps=30,
                        logger=None,
                        codec=video_codec,
                        bitrate=video_bitrate,
                        audio_bitrate=audio_bitrate,
                        ffmpeg_params=quality_params
                    )
                    image_clip.close()
                    zoom_clip.close()
                    
                    video_paths.append(output_video_path)
                    total_duration += max_clip_duration
                    logger.success(f"Converted fallback image to zoom clip: {output_video_path}")
            except Exception as ex:
                logger.error(f"Failed to generate fallback AI image for '{term}': {str(ex)}")

    # Final diversity report
    logger.success(f"downloaded {len(video_paths)} videos")
    logger.info(f"🎯 Final diversity: {len(downloaded_urls)} unique URLs downloaded")
    
    return video_paths


if __name__ == "__main__":
    download_videos(
        "test123", ["Money Exchange Medium"], audio_duration=100, source="pixabay"
    )
