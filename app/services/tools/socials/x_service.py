
import yt_dlp, re, asyncio
from urllib.parse import urlparse, parse_qs
from fastapi import Request, HTTPException
from app import config as app_config
from app.utils.concurrency import download_slot
import asyncio
from app.utils.cache import cache

def is_valid_twitter_url(url: str) -> bool:
    pattern = r'^(https?:\/\/)?(www\.)?(twitter|x)\.com\/[A-Za-z0-9_]+\/status\/[0-9]+(\?.*)?$'
    return bool(re.match(pattern, url))


async def download_video(video_url, request: Request, save_dir="downloads"):

    try:    
        cache_key = cache.make_key("x_video", video_url)
        cached_data = cache.get(cache_key)
        if cached_data:
            return cached_data

        if not is_valid_twitter_url(video_url):
            raise ValueError('Invalid X (twitter) video URL!')

        v_info = await video_info(video_url)

        cache.set(cache_key, v_info)
        return v_info

    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error {str(e)}")



def _normalize_url(url: str) -> str:
    """Normalize to twitter.com — yt-dlp's Twitter extractor is more stable with it."""
    return re.sub(r'https?://(www\.)?x\.com/', 'https://twitter.com/', url)


def _alternate_url(url: str) -> str | None:
    """Return the other domain variant if applicable."""
    if 'x.com' in url:
        return re.sub(r'https?://(www\.)?x\.com/', 'https://twitter.com/', url)
    if 'twitter.com' in url:
        return re.sub(r'https?://(www\.)?twitter\.com/', 'https://x.com/', url)
    return None


def _build_ydl_opts(region: str) -> dict:
    opts = {
        "quiet": True,
        'nocheckcertificate': True,
        'legacy_server_connect': True,
        "format": 'best',
        "socket_timeout": 30,
        "http_chunk_size": 1048576,
        "retries": 3,
        'fragment_retries': 5,
        'skip_download': True,
        'no_warnings': True,
    }
    try:
        opts['proxy'] = app_config.settings.prepare_proxy(region)
    except ValueError:
        pass
    return opts


def _pick_format(info: dict) -> tuple:
    formats = info.get("formats", [])
    combined = [
        f for f in formats
        if f.get('protocol') in ('https', 'http')
        and 'only' not in (f.get('format_note') or '')
    ]
    selected = max(
        combined or formats,
        key=lambda x: x.get('filesize') or x.get('filesize_approx') or 0,
        default=None
    )
    video_url = info.get('url') or (selected.get('url') if selected else None)
    file_size = (selected.get("filesize") or selected.get("filesize_approx") or 0) if selected else 0
    return video_url, file_size


async def video_info(url, region: str = 'us'):
    """Extract X (Twitter) video information with domain-fallback retry."""
    url = _normalize_url(url)
    ydl_opts = _build_ydl_opts(region)

    def _extract(u, opts):
        with yt_dlp.YoutubeDL(opts) as ydl:
            return ydl.extract_info(u, download=False)

    last_error = None
    for attempt_url in [url, _alternate_url(url)]:
        if not attempt_url:
            continue
        try:
            async with download_slot():
                info = await asyncio.to_thread(_extract, attempt_url, ydl_opts)

            video_url, file_size = _pick_format(info)
            if not video_url:
                last_error = "No video found in this tweet."
                continue

            return {
                "title": info.get("title"),
                "duration": info.get("duration"),
                "size": file_size,
                "size_in_mb": round(file_size / (1024 * 1024), 2) if file_size else 0,
                "thumbnail": info.get("thumbnail"),
                'url': video_url,
                'download_url': video_url,
            }
        except asyncio.TimeoutError:
            last_error = "Request timed out."
            continue
        except Exception as e:
            last_error = str(e)
            continue

    raise ValueError(last_error or "Could not extract video from this tweet.")


