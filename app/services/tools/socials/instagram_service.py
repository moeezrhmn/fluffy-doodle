
import instaloader, requests, os, math, yt_dlp
from urllib.parse import urlparse, parse_qs
from fastapi import Request, HTTPException
from app import config as app_config
from app.utils import helper

try:
    from instagrapi import Client
    from app.services.tools.socials.instagram_account_manager import account_manager
    INSTAGRAPI_AVAILABLE = True
except ImportError:
    INSTAGRAPI_AVAILABLE = False
    account_manager = None
    print("[instagram] Warning: instagrapi not installed. Run: pip install instagrapi")

os.environ['https_proxy'] = app_config.IP2WORLD_STICKY_PROXY


def download_video(post_url, request: Request, save_dir="downloads"):
    """Download Instagram video - Optimized for speed"""

    try:
        return instaloader_download_video(post_url)
    except Exception as instaloader_ex:
        print(f"[instagram] Instaloader failed: {str(instaloader_ex)}. Trying yt-dlp fallback...")

    try:
        return download_video_with_ytdlp(post_url)
    except Exception as ytdlp_ex:
        print(f"[instagram] yt-dlp failed: {str(ytdlp_ex)}. Trying Instagrapi fallback...")

    try:
        return download_video_with_instagrapi(post_url)
    except Exception as instagrapi_ex:
        
        raise ValueError(
            f"[instagram] Failed to download video from Instagram."
            f" Instaloader: {str(instaloader_ex)}, "
            f"Instagrapi: {str(instagrapi_ex)}, "
            f"yt-dlp: {str(ytdlp_ex)}",
        )

   



def instaloader_download_video(post_url):
    """Download Instagram video using Instaloader (slow)"""
    L = instaloader.Instaloader()
    shortcode = extract_reel_id(post_url)

    post = instaloader.Post.from_shortcode(L.context, shortcode)

    if not post.is_video:
        raise ValueError("The provided URL does not point to a video.")

    # Get video details
    video_url = post.video_url
    thumbnail_url = post.url
    caption = post.caption if post.caption else "No Caption"
    likes = post.likes if post.likes else 0
    profile = post.profile if post.profile else "No Profile"
    is_reel = post.is_video and post.typename == "GraphVideo"

    video_details = {
        "title": caption,
        "duration": post.video_duration,
        "thumbnail": thumbnail_url,
        "size": "Unknown",
        "download_url": video_url,
        "is_reel": is_reel,
        "likes": likes,
        "profile": profile,
    }

    return video_details


def download_video_with_instagrapi(post_url):
    """Use instagrapi library with account rotation - FAST"""
    try:
        # Get authenticated client from account manager
        cl = account_manager.get_client() if account_manager else None

        if not cl:
            # Try without authentication as fallback
            print("[instagram] No authenticated accounts available, trying without login")
            cl = Client()
            cl.delay_range = [0.5, 1]  # Reduced delay for speed
            if app_config.IP2WORLD_STICKY_PROXY:
                cl.set_proxy(app_config.IP2WORLD_STICKY_PROXY)

        # Extract media ID from URL
        media_pk = cl.media_pk_from_url(post_url)

        # Get media info (authenticated if available)
        media = cl.media_info(media_pk)

        if media.media_type != 2 and media.media_type != 8:  # 2=video, 8=album with video
            raise ValueError("The provided URL does not point to a video.")

        # Get video URL
        video_url = None
        if media.media_type == 2:  # Single video
            video_url = str(media.video_url)
        elif media.media_type == 8:  # Album - get first video
            for resource in media.resources:
                if resource.media_type == 2:
                    video_url = str(resource.video_url)
                    break

        if not video_url:
            raise ValueError("Could not extract video URL from Instagram")

        # Build response similar to instaloader format
        video_details = {
            "title": media.caption_text if media.caption_text else "Instagram Video",
            "duration": media.video_duration if hasattr(media, 'video_duration') else None,
            "thumbnail": str(media.thumbnail_url) if media.thumbnail_url else None,
            "size": "Unknown",
            "download_url": video_url,
            "is_reel": media.product_type == "clips",
            "likes": media.like_count if media.like_count else 0,
            "profile": media.user.username if media.user else "Unknown",
        }

        auth_status = f"authenticated as {cl.username}" if hasattr(cl, 'username') and cl.username else "without authentication"
        print(f"[instagram] Successfully extracted with instagrapi ({auth_status})")
        return video_details

    except Exception as e:
        raise ValueError(f"Instagrapi extraction failed: {str(e)}")


def download_video_with_ytdlp(post_url):
    """Final fallback using yt-dlp (no authentication)"""
    try:
        ydl_opts = {
            'quiet': True,
            'no_warnings': True,
            'skip_download': True,
        }

        print(f"[instagram] Trying yt-dlp without authentication")
        if app_config.settings.prepare_proxy():
            ydl_opts['proxy'] = app_config.settings.prepare_proxy()

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(post_url, download=False)

        # Extract video URL (best quality)
        video_url = None
        if 'url' in info:
            video_url = info['url']
        elif 'formats' in info:
            # Get the best quality format with video
            formats = [f for f in info['formats'] if f.get('vcodec') != 'none']
            if formats:
                best_format = max(formats, key=lambda x: x.get('height', 0))
                video_url = best_format.get('url')

        if not video_url:
            raise ValueError("Could not extract video URL from Instagram")

        # Build response similar to instaloader format
        video_details = {
            "title": info.get("title") or info.get("description") or "Instagram Video",
            "duration": info.get("duration"),
            "thumbnail": info.get("thumbnail"),
            "size": "Unknown",
            "download_url": video_url,
            "is_reel": True,
            "likes": info.get("like_count", 0),
            "profile": info.get("uploader") or info.get("channel") or "Unknown",
        }

        print(f"[instagram] Successfully extracted with yt-dlp")
        return video_details

    except Exception as e:
        error_msg = str(e)
        if "inappropriate" in error_msg.lower() or "unavailable for certain audiences" in error_msg.lower():
            raise ValueError(
                f"Age-restricted content cannot be downloaded without authentication. "
                f"This video is restricted by Instagram. "
                f"Original error: {error_msg}"
            )
        raise ValueError(f"yt-dlp extraction failed: {error_msg}")


def extract_reel_id(post_url):

    parsed_url = urlparse(post_url)
    path = parsed_url.path
    parts = path.strip("/").split("/")
    if len(parts) >= 2 and parts[0] == "reel":
        return parts[1]

    return None
