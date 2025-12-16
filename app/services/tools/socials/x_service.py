
import instaloader, requests, os, math, yt_dlp, re, asyncio
from urllib.parse import urlparse, parse_qs
from fastapi import Request, HTTPException
from app import config as app_config
from app.utils import helper


def is_valid_twitter_url(url: str) -> bool:
    pattern = r'^(https?:\/\/)?(www\.)?(twitter|x)\.com\/[A-Za-z0-9_]+\/status\/[0-9]+(\?.*)?$'
    return bool(re.match(pattern, url))


async def download_video(video_url, request: Request, save_dir="downloads"):

    try:
        if not is_valid_twitter_url(video_url):
            raise ValueError('Invalid X (twitter) video URL!')
            
        print({'video_url':video_url})

        v_info = await video_info(video_url)
        return v_info

    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error {str(e)}")



async def video_info(url, region: str = 'us'):
    """Extract X (Twitter) video information with improved reliability"""
    try:
        ydl_opts = {
            "quiet": True,
            'nocheckcertificate': True,  # Bypass SSL certificate verification
            'legacy_server_connect': True,  # Use legacy server connection for better compatibility
            "format": 'best',
            "socket_timeout": 30,
            "http_chunk_size": 1048576,
            "retries": 10,  # Increased retries for better reliability
            'fragment_retries': 10,  # Retry for fragmented downloads
            "timeout": 90,  # Increased timeout
            'skip_download': True,  # Only get info, don't download
            'no_warnings': True,  # Suppress warnings
        }

        # Use regional proxy if available (better than hardcoded proxy)
        if app_config.settings.prepare_proxy(region):
            ydl_opts['proxy'] = app_config.settings.prepare_proxy(region)
            print(f'[X Service] Using proxy for region: {region}')
        elif app_config.IP2WORLD_PROXY:
            # Fallback to default proxy
            ydl_opts['proxy'] = app_config.IP2WORLD_PROXY

        def extract_info_async(url, ydl_opts):
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                print('[video_info] Starting X (Twitter) scraping ⌛⌛')
                return ydl.extract_info(url, download=False)

        # Execute with timeout
        info = await asyncio.wait_for(
            asyncio.to_thread(extract_info_async, url, ydl_opts),
            timeout=90
        )
        print('[video_info] Scraping Completed ✅')

        # Get the selected format or best available format
        selected_format = next(
            (f for f in info.get("formats", []) if f.get("format_id") == info.get("format_id")),
            None
        )

        # If no selected format, try to get best video format
        if not selected_format and info.get("formats"):
            selected_format = max(
                [f for f in info.get("formats", []) if f.get("vcodec") != "none"],
                key=lambda x: x.get("filesize", 0) or 0,
                default=None
            )

        # Calculate file size
        file_size = selected_format.get("filesize") or selected_format.get("filesize_approx", 0) if selected_format else 0
        file_size_mb = round(file_size / (1024 * 1024), 2) if file_size else 0

        # Get the video URL - try multiple sources
        video_url = info.get('url') or (selected_format.get('url') if selected_format else None)

        if not video_url:
            raise ValueError("Could not extract video URL from X (Twitter)")

        # Return video details (same payload structure)
        video_details = {
            "title": info.get("title"),
            "duration": info.get("duration"),
            "size": file_size,
            "size_in_mb": file_size_mb,
            "thumbnail": info.get("thumbnail"),
            'url': video_url,
            'download_url': video_url,
        }
        return video_details

    except asyncio.TimeoutError:
        raise ValueError("[video_info]: Request timed out after 90 seconds")
    except Exception as e:
        raise ValueError(f"[video_info]: {str(e)}")


