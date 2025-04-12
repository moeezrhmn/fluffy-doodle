import requests, os, yt_dlp, re, asyncio
from fastapi import Request, HTTPException
from app import config as app_config



def is_valid_vk_url(url: str) -> bool:
    """Validate VK video URL"""
    pattern = r'^(https?:\/\/)?(www\.)?(vk\.com\/video|vkvideo\.ru\/playlist)\/[-\d_]+\/video[-\d_]+(\?.*)?$'
    return bool(re.match(pattern, url))

async def download_video(video_url, request: Request, save_dir="downloads"):
    try:
        if not is_valid_vk_url(video_url):
            raise ValueError('Invalid VK video URL!')

        print({'video_url': video_url})

        v_info = await video_info(video_url)
        return v_info

    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error: {str(e)}")

async def video_info(url):
    try:
        ydl_opts = {
            "quiet": True,
            "nocheckcertificate": True,
            # "proxy": app_config.IP2WORLD_PROXY,
            "format": "best",
            "list-formats": True,
            "socket_timeout": 30,
            "http_chunk_size": 1048576,
            "retries": 3,
            "timeout": 60,
        }

        def extract_info_async(url, ydl_opts):
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                print("[video_info] Starting scraping ⌛⌛")
                return ydl.extract_info(url, download=False)

        info = await asyncio.wait_for(asyncio.to_thread(extract_info_async, url, ydl_opts), timeout=60)
        print("[video_info] Scraping Completed ✅")

        selected_format = next((f for f in info.get("formats", []) if f.get("format_id") == info.get("format_id")), None)
        file_size = selected_format.get("filesize", 0) if selected_format else 0
        file_size_mb = round(file_size / (1024 * 1024), 2) if file_size else 0

        video_details = {
            "title": info.get("title"),
            "duration": info.get("duration"),
            "size": file_size,
            "size_in_mb": file_size_mb,
            "thumbnail": info.get("thumbnail"),
            "download_url": info["url"],
        }
        return video_details

    except Exception as e:
        raise ValueError(f"[video_info]: {str(e)}")
