import re
import json
import os
import glob
import time
import httpx
from app import config as app_config
from app.utils.cache import cache
from app.utils.concurrency import download_slot
from app.utils import monitor

TIKTOK_MAX_DURATION = 120
TIKTOK_FILE_TTL = 86400   # 24 hours on disk
TIKTOK_CACHE_TTL = 82800  # 23 hours in Redis

BROWSER_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/125.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "Accept-Encoding": "identity",
    "Referer": "https://www.tiktok.com/",
    "Sec-Fetch-Dest": "document",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Site": "same-origin",
}


def _extract_video_id(url: str):
    match = re.search(r'/video/(\d+)', url)
    return match.group(1) if match else None


async def _get_video_id(url: str, proxy: str = None) -> str:
    vid = _extract_video_id(url)
    if not vid:
        kwargs = {"follow_redirects": True, "timeout": 15, "headers": BROWSER_HEADERS}
        if proxy:
            kwargs["proxy"] = proxy
        async with httpx.AsyncClient(**kwargs) as client:
            r = await client.head(url)
        vid = _extract_video_id(str(r.url))
    if not vid:
        raise ValueError(f"Could not extract TikTok video ID from: {url}")
    return vid


def _parse_item(html: str) -> dict:
    match = re.search(
        r'<script\s+id="__UNIVERSAL_DATA_FOR_REHYDRATION__"[^>]*>(.*?)</script>',
        html, re.DOTALL
    )
    if not match:
        raise ValueError("TikTok page JSON not found — likely a bot-check page")
    page_data = json.loads(match.group(1))
    try:
        item = (
            page_data["__DEFAULT_SCOPE__"]
            .get("webapp.video-detail", {})
            .get("itemInfo", {})
            .get("itemStruct")
        )
        if not item:
            raise ValueError("itemStruct missing in page data")
        return item
    except (KeyError, TypeError):
        raise ValueError("Unexpected TikTok page structure")


def _extract_cdn_url(item: dict) -> str | None:
    video = item.get("video", {})
    for key in ("playAddr", "playUrl", "downloadAddr"):
        val = video.get(key)
        if not val:
            continue
        if isinstance(val, str):
            return val
        if isinstance(val, dict):
            for u in (val.get("urlList") or []):
                if u:
                    return u
    return None


def _cleanup_old_files():
    now = time.time()
    for fp in glob.glob(os.path.join(app_config.DOWNLOAD_DIR, "tiktok_*.mp4")):
        if now - os.path.getmtime(fp) > TIKTOK_FILE_TTL:
            try:
                os.remove(fp)
            except OSError:
                pass


def _proxies_to_try(region: str):
    seen = set()
    for r in [region, 'US', 'SG']:
        key = r.upper()
        if key in seen:
            continue
        seen.add(key)
        try:
            yield f"proxy-{key}", app_config.settings.prepare_proxy(r)
        except ValueError:
            pass
    yield "no-proxy", None


async def video_info(url: str, region: str, base_url: str = None):
    try:
        cache_key = cache.make_key("tiktok_video", url, region)
        cached = cache.get(cache_key)
        if cached:
            return cached

        proxy_for_id = None
        try:
            proxy_for_id = app_config.settings.prepare_proxy(region)
        except ValueError:
            pass

        video_id = await _get_video_id(url, proxy=proxy_for_id)
        canonical_url = f"https://www.tiktok.com/@i/video/{video_id}"
        download_path = os.path.join(app_config.DOWNLOAD_DIR, f"tiktok_{video_id}.mp4")

        # File already on disk — build result without re-scraping
        if os.path.exists(download_path):
            actual_size = os.path.getsize(download_path)
            server_url = f"{base_url}/downloads/tiktok_{video_id}.mp4" if base_url else None
            result = {
                "message": "Video downloaded successfully",
                "region": region,
                "video_info": {
                    "video_id": video_id,
                    "size": actual_size,
                    "size_in_mb": round(actual_size / (1024 * 1024), 2),
                    "webpage_url": url,
                    "video_url": server_url,
                    "download_url": server_url,
                }
            }
            cache.set(cache_key, result, ttl=TIKTOK_CACHE_TTL)
            return result

        _cleanup_old_files()

        last_error = None
        for label, proxy in _proxies_to_try(region):
            try:
                kwargs = {
                    "timeout": httpx.Timeout(20, read=60),
                    "headers": BROWSER_HEADERS,
                    "follow_redirects": True,
                }
                if proxy:
                    kwargs["proxy"] = proxy

                async with download_slot():
                    async with httpx.AsyncClient(**kwargs) as client:
                        # Step 1: load page — sets tt_chain_token cookie
                        r = await client.get(canonical_url)
                        r.raise_for_status()
                        item = _parse_item(r.text)

                        cdn_url = _extract_cdn_url(item)
                        if not cdn_url:
                            raise ValueError("No video URL found in page data")

                        duration = item.get("video", {}).get("duration") or item.get("duration") or 0
                        if duration > TIKTOK_MAX_DURATION:
                            raise ValueError(f"Video too long ({duration}s). Max is {TIKTOK_MAX_DURATION}s.")

                        # Step 2: download with SAME client (cookies active)
                        async with client.stream("GET", cdn_url) as dr:
                            dr.raise_for_status()
                            with open(download_path, "wb") as f:
                                async for chunk in dr.aiter_bytes(chunk_size=1024 * 64):
                                    f.write(chunk)

                print(f"[tiktok] Success with {label}")
                actual_size = os.path.getsize(download_path) if os.path.exists(download_path) else 0
                if actual_size:
                    monitor.add_request_proxy_bytes(actual_size)

                author = item.get("author") or {}
                video = item.get("video", {})
                cover = video.get("cover") or video.get("originCover") or ""
                stats = item.get("stats") or {}
                server_url = f"{base_url}/downloads/tiktok_{video_id}.mp4" if base_url else None

                result = {
                    "message": "Video downloaded successfully",
                    "region": region,
                    "video_info": {
                        "title": item.get("desc") or "TikTok Video",
                        "duration": duration,
                        "video_id": video_id,
                        "thumbnail": cover,
                        "size": actual_size,
                        "size_in_mb": round(actual_size / (1024 * 1024), 2) if actual_size else None,
                        "webpage_url": url,
                        "video_url": server_url,
                        "download_url": server_url,
                        "author": author.get("nickname") or author.get("uniqueId"),
                        "play_count": stats.get("playCount"),
                        "like_count": stats.get("diggCount"),
                    }
                }
                cache.set(cache_key, result, ttl=TIKTOK_CACHE_TTL)
                return result

            except ValueError:
                raise
            except Exception as e:
                print(f"[tiktok] {label} failed: {e}")
                last_error = e
                if os.path.exists(download_path):
                    os.remove(download_path)
                continue

        raise ValueError(f"All TikTok attempts failed: {last_error}")

    except ValueError:
        raise
    except Exception as e:
        raise ValueError(f"[tiktok] {str(e)}")