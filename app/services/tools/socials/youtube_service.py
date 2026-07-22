import re
import json
import asyncio
from fastapi import HTTPException
from app import config as app_config
from app.utils.cache import cache
from app.utils.concurrency import download_slot
from app.utils import monitor
import yt_dlp


def _friendly_error(raw: str) -> str:
    msg = raw.lower()
    if "sign in to confirm your age" in msg or "age" in msg and "sign in" in msg:
        return "This video is age-restricted and cannot be downloaded without authentication."
    if "sign in to confirm you're not a bot" in msg or "not a bot" in msg:
        return "YouTube is blocking this request as a bot. Try a different region or try again later."
    if "account associated with this video has been terminated" in msg:
        return "This video is unavailable — the YouTube account has been terminated."
    if "this video is no longer available" in msg:
        return "This video is no longer available."
    if "video unavailable" in msg or "this video is not available" in msg:
        return "This video is unavailable or region-restricted."
    if "private video" in msg:
        return "This video is private and cannot be downloaded."
    if "no audio-only stream available" in msg or "sabr" in msg:
        return "Audio-only stream is not available for this video right now. Try a different region."
    if "invalid youtube url" in msg:
        return raw
    return "Failed to retrieve video information. The video may be unavailable or restricted."


async def download_video(video_url: str, region: str):
    try:
        video_id = extract_youtube_video_id(video_url)
        if video_id:
            video_url = f"https://www.youtube.com/watch?v={video_id}"

        v_info = await video_info(video_url, region)
        return v_info

    except HTTPException:
        raise
    except Exception as e:
        msg = re.sub(r'\x1b\[[0-9;]*m', '', str(e)).split('\nTraceback')[0].strip()
        raise HTTPException(status_code=400, detail={"detail": msg, "message": _friendly_error(msg)})


async def video_info(url, region: str):
    """Get video information using yt-dlp command line tool"""
    try:
        cache_key = cache.make_key("youtube_video", url, region)
        
        cached_data = cache.get(cache_key)
        if cached_data:
            return cached_data
        
        options = {
            "listformats": True,
            "noplaylist": True,
            "quiet": True,
            'skip_download': True,
            'legacy_server_connect': True,
            'socket_timeout': 30,
            # 'extractor_args': {'youtube': {'player_client': ['web', 'android']}},
            'js_runtimes': {'deno': {}},
            'remote_components': ['ejs:npm'],
        }

        try:
            options['proxy'] = app_config.settings.prepare_proxy(region)
            print(f"[youtube] Using proxy region={region}")
        except ValueError:
            pass

        def _extract(url, opts):
            with yt_dlp.YoutubeDL(opts) as ydl:
                return ydl.extract_info(url, download=False)

        async with download_slot():
            info = await asyncio.to_thread(_extract, url, options)

        try:
            monitor.add_request_proxy_bytes(len(json.dumps(info, default=str).encode()))
        except Exception:
            pass

        formats = info.get('formats', [])
        available_formats = []

        for fmt in formats:
            
            if not fmt.get('protocol') in ['https', 'http'] or fmt.get('audio_channels') is None or fmt.get('resolution') == 'audio only':
                continue

            resolution = fmt.get('format_note')
            ext = fmt.get('ext')
            filesize = fmt.get('filesize') or fmt.get('filesize_approx')
            video_url = fmt.get('url')
            duration = info.get("duration")
            format_id = fmt.get('format_id')

            available_formats.append({
                'format_id': format_id,
                'ext': ext,
                'resolution': resolution,
                'filesize': filesize,
                'url': video_url,
                'duration': duration,
            })
        sorted_formats = sorted(available_formats, key=lambda x: (x['filesize'] is None, x['filesize']))
        selected_format = sorted_formats[-1] if sorted_formats else None

        result = {
            'message': 'Video info retrieved successfully',
            'region': region,
            'video_info': {
                "title": info.get("title"),
                "duration": info.get("duration"),
                "video_id": info.get("id"),
                "size": selected_format.get('filesize') if selected_format else None,
                "size_in_mb": round(selected_format.get('filesize') / (1024 * 1024), 2) if selected_format and selected_format.get('filesize') else None,
                "thumbnail": info.get("thumbnail"),
                'video_url': info.get('webpage_url'), 
                'download_url': selected_format.get('url') if selected_format else None, 
                'url': selected_format.get('url') if selected_format else None, 
                'available_formats': sorted_formats
            }
        }
        
        cache.set(cache_key, result)

        return result
    except Exception as e:
        raise ValueError(str(e).split('\nTraceback')[0].strip())


def extract_youtube_video_id(url: str) -> str | None:
    pattern = r'(?:https?:\/\/)?(?:www\.)?(?:youtube\.com\/(?:watch\?v=|embed\/|shorts\/)|youtu\.be\/)([a-zA-Z0-9_-]{6,12})'
    match = re.search(pattern, url)
    return match.group(1) if match else None





async def get_audio_url(video_url: str, region: str):
    """Get audio URL using yt-dlp Python package"""
    try:
        cache_key = cache.make_key("youtube_audio", video_url, region)
        cached_data = cache.get(cache_key)
        if cached_data:
            return cached_data
        
        options = {
            "format": "bestaudio/best",
            "noplaylist": True,
            "quiet": True,
            'skip_download': True,
            'legacy_server_connect': True,
            'socket_timeout': 30,
            'geo_bypass': True,
            'geo_bypass_country': region if region else 'US',
            'js_runtimes': {'deno': {}},
            'remote_components': ['ejs:npm'],
        }

        try:
            options['proxy'] = app_config.settings.prepare_proxy(region)
        except ValueError:
            pass

        def _extract(url, opts):
            with yt_dlp.YoutubeDL(opts) as ydl:
                return ydl.extract_info(url, download=False)

        async with download_slot():
            info = await asyncio.to_thread(_extract, video_url, options)

        try:
            monitor.add_request_proxy_bytes(len(json.dumps(info, default=str).encode()))
        except Exception:
            pass

        audio_url = info.get('url')
        if not audio_url:
            raise ValueError("Audio URL not found in the extracted information.")

        http_headers = info.get('http_headers', {})

        audio_details = {
            "title": info.get("title"),
            "duration": info.get("duration"),
            "video_id": info.get("id"),
            "size": None,
            "size_in_mb": None,
            "thumbnail": info.get("thumbnail"),
            'audio_url': audio_url,
            'download_url': audio_url,
            'http_headers': http_headers,
            'warning': 'Audio URL expires in 5-6 hours. Use http_headers when accessing.',
            'webpage_url': info.get('webpage_url')
        }
        cache.set(cache_key, audio_details)
        return audio_details

    except Exception as e:
        msg = re.sub(r'\x1b\[[0-9;]*m', '', str(e)).split('\nTraceback')[0].strip()
        raise HTTPException(status_code=400, detail={"detail": msg, "message": _friendly_error(msg)})


