import asyncio
import os
import glob
import time
from app import config as app_config
from app.utils.cache import cache
import yt_dlp
from yt_dlp.networking.impersonate import ImpersonateTarget

# Limits
TIKTOK_MAX_DURATION = 120  # seconds (2 minutes)
TIKTOK_CACHE_TTL = 86400  # 24 hours in seconds
TIKTOK_FORMAT = 'best[height<=480][ext=mp4]/best[height<=480]/worst[ext=mp4]/worst'

# Fallback regions to try if requested region fails
TIKTOK_FALLBACK_REGIONS = ['US', 'SG']


def _base_options():
    return {
        "quiet": True,
        'noplaylist': True,
        'nocheckcertificate': True,
        'legacy_server_connect': True,
        'impersonate': ImpersonateTarget.from_str('chrome'),
    }


def _cleanup_old_tiktok_files():
    """Delete TikTok files older than 24 hours from downloads folder."""
    pattern = os.path.join(app_config.DOWNLOAD_DIR, "tiktok_*.mp4")
    now = time.time()
    for filepath in glob.glob(pattern):
        if now - os.path.getmtime(filepath) > TIKTOK_CACHE_TTL:
            try:
                os.remove(filepath)
            except OSError:
                pass


def _extract_sync(url, opts):
    with yt_dlp.YoutubeDL(opts) as ydl:
        return ydl.extract_info(url, download=False)


def _download_sync(url, opts):
    with yt_dlp.YoutubeDL(opts) as ydl:
        ydl.extract_info(url, download=True)


async def _extract_with_fallback(url, region):
    """Try extracting info: requested region proxy → no proxy → fallback regions."""
    attempts = []

    # 1) Requested region proxy
    opts = _base_options()
    opts['skip_download'] = True
    try:
        proxy = app_config.settings.prepare_proxy(region)
        opts['proxy'] = proxy
        attempts.append(f"proxy-{region}")
    except ValueError:
        pass

    try:
        return await asyncio.to_thread(_extract_sync, url, opts), region
    except Exception as e:
        print(f"[tiktok] Extract failed with {attempts[-1] if attempts else 'no-proxy'}: {e}")

    # 2) No proxy (direct from server)
    opts = _base_options()
    opts['skip_download'] = True
    try:
        return await asyncio.to_thread(_extract_sync, url, opts), None
    except Exception as e:
        print(f"[tiktok] Extract failed with no proxy: {e}")

    # 3) Fallback regions
    for fallback_region in TIKTOK_FALLBACK_REGIONS:
        if fallback_region.lower() == region.lower():
            continue
        opts = _base_options()
        opts['skip_download'] = True
        try:
            opts['proxy'] = app_config.settings.prepare_proxy(fallback_region)
        except ValueError:
            continue
        try:
            return await asyncio.to_thread(_extract_sync, url, opts), fallback_region
        except Exception as e:
            print(f"[tiktok] Extract failed with proxy-{fallback_region}: {e}")

    raise ValueError("All extraction attempts failed. TikTok may be blocking this video or all proxy regions.")


async def _download_with_fallback(url, region, working_region):
    """Download using the region that worked for extraction, with fallbacks."""
    regions_to_try = []

    # Start with the region that worked for extraction
    if working_region:
        regions_to_try.append(working_region)
    else:
        regions_to_try.append(None)  # None = no proxy

    # Add other fallbacks
    if working_region != region:
        regions_to_try.append(region)
    regions_to_try.append(None)  # no proxy
    for fr in TIKTOK_FALLBACK_REGIONS:
        if fr not in regions_to_try and fr.lower() != (working_region or '').lower():
            regions_to_try.append(fr)

    for r in regions_to_try:
        opts = _base_options()
        opts['format'] = TIKTOK_FORMAT
        opts['outtmpl'] = f"{app_config.DOWNLOAD_DIR}/tiktok_%(id)s.%(ext)s"
        opts['retries'] = 3
        opts['fragment_retries'] = 3

        label = 'no-proxy'
        if r:
            try:
                opts['proxy'] = app_config.settings.prepare_proxy(r)
                label = f"proxy-{r}"
            except ValueError:
                continue

        try:
            await asyncio.to_thread(_download_sync, url, opts)
            print(f"[tiktok] Download succeeded with {label}")
            return
        except Exception as e:
            print(f"[tiktok] Download failed with {label}: {e}")

    raise ValueError("All download attempts failed.")


async def video_info(url, region: str, base_url: str = None):
    try:
        cache_key = cache.make_key("tiktok_video", url, region)
        cached_data = cache.get(cache_key)
        if cached_data:
            return cached_data

        # Step 1: Extract info with fallback
        info, working_region = await _extract_with_fallback(url, region)

        video_id = info.get('id')
        duration = info.get('duration') or 0

        # Check duration limit
        if duration > TIKTOK_MAX_DURATION:
            raise ValueError(
                f"Video is too long ({duration}s). "
                f"Maximum allowed duration is {TIKTOK_MAX_DURATION}s ({TIKTOK_MAX_DURATION // 60} minutes)."
            )

        # Step 2: Check if file already exists (cached on disk)
        download_path = f"{app_config.DOWNLOAD_DIR}/tiktok_{video_id}.mp4"
        if not os.path.exists(download_path):
            _cleanup_old_tiktok_files()

            # Step 3: Download with fallback
            await _download_with_fallback(url, region, working_region)

        # Build format info from extracted metadata
        formats = info.get('formats', [])
        available_formats = []
        for fmt in formats:
            protocol = fmt.get('protocol', '')
            vcodec = fmt.get('vcodec', 'none')
            if protocol not in ['https', 'http']:
                continue
            if not vcodec or vcodec == 'none':
                continue
            resolution = fmt.get('resolution')
            filesize = fmt.get('filesize') or fmt.get('filesize_approx')
            width = fmt.get('width')
            height = fmt.get('height')
            available_formats.append({
                'format_id': fmt.get('format_id'),
                'ext': fmt.get('ext'),
                'resolution': resolution or (f"{width}x{height}" if width and height else 'unknown'),
                'format_note': fmt.get('format_note') or resolution or 'unknown',
                'width': width,
                'height': height,
                'filesize': filesize,
                'filesize_mb': round(filesize / (1024 * 1024), 2) if filesize else None,
            })

        sorted_formats = sorted(available_formats, key=lambda x: (x['filesize'] is None, x['filesize']))

        # Get actual file size from disk
        actual_size = os.path.getsize(download_path) if os.path.exists(download_path) else None

        server_video_url = None
        if base_url:
            server_video_url = f"{base_url}/downloads/tiktok_{video_id}.mp4"

        result = {
            'message': 'Video downloaded successfully',
            'region': working_region or region,
            'video_info': {
                "title": info.get("title"),
                "duration": duration,
                "video_id": video_id,
                "size": actual_size,
                "size_in_mb": round(actual_size / (1024 * 1024), 2) if actual_size else None,
                "thumbnail": info.get("thumbnail"),
                'webpage_url': info.get('webpage_url'),
                'video_url': server_video_url,
                'download_url': server_video_url,
                'available_formats': sorted_formats,
                'total_formats': len(sorted_formats)
            }
        }
        cache.set(cache_key, result, ttl=TIKTOK_CACHE_TTL)
        return result
    except Exception as e:
        raise ValueError(f"[video_info]: {str(e)}")
