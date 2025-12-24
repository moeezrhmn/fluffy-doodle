
import instaloader, requests, os, math, yt_dlp, asyncio
from urllib.parse import urlparse, parse_qs
from fastapi import Request, HTTPException
from app import config as app_config
from app.utils import helper
from app.utils.cache import cache



async def download_video(video_url, region, save_dir="downloads"):

    try:
        cache_key = cache.make_key("facebook_video", video_url, region)
        result = cache.get(cache_key)
        if result:
            return result

        result = await video_info(video_url, region)
        cache.set(cache_key, result)
        return result

    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error {str(e)}")


async def video_info(url, region: str):
    try:
        ydl_opts = {
            "quiet": True,
            'nocheckcertificate': True,
            'legacy_server_connect': True,  # Use legacy SSL connection
            "format": 'best',
            "noplaylist": True,
            "list-formats": True,
            "socket_timeout": 40,
            "http_chunk_size": 1048576,
            "retries": 5,  # More retries for SSL issues
            "timeout": 60,
            "extractor_retries": 3,  # Retry on extractor failures
        }

        if app_config.settings.prepare_proxy(region):
            ydl_opts['proxy'] = app_config.settings.prepare_proxy(region)
            

        def _extract(url, opts):
            with yt_dlp.YoutubeDL(opts) as ydl:
                return ydl.extract_info(url, download=False)
            
        info = await asyncio.to_thread(_extract, url, ydl_opts)
        
        selected_format = next((f for f in info.get("formats", []) if f.get("format_id") == info.get("format_id")), None)
        file_size = selected_format.get("filesize", 0) if selected_format else 0
        file_size_mb = round(file_size / (1024 * 1024), 2) if file_size else 0

        video_details = {
            "title": info.get("title"),
            "duration": info.get("duration"),
            "size": file_size,
            "size_in_mb": file_size_mb,
            "thumbnail": info.get("thumbnail"), 
            'url':info['url'],
            'download_url':info['url'],
        }
        return video_details
    except Exception as e:
        raise ValueError(f"[video_info]: {str(e)}")




