import re
from fastapi import HTTPException
from app import config as app_config
from app.utils import helper
import yt_dlp



async def download_video(video_url: str, region: str):
    """Get YouTube video information"""
    try:
        video_id = extract_youtube_video_id(video_url)
        video_url = f"https://www.youtube.com/watch?v={video_id}"
        print({'video_url': video_url, 'video_id': video_id})

        v_info = await video_info(video_url, region)
        # v_info = await video_info_2(video_url)
        return v_info

    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error {str(e)}")


async def video_info(url, region: str):
    """Get video information using yt-dlp command line tool"""
    try:
        options = {
            "listformats": True,
            "noplaylist": True,
            "quiet": True,
            'skip_download': True,
            'legacy_server_connect': True,
            'geo_bypass': True,  # Bypass geo-restrictions
            'geo_bypass_country': region if region else 'US',  # Use region for geo-bypass
        }

        if app_config.settings.prepare_proxy(region):
            options['proxy'] = app_config.settings.prepare_proxy(region)

        with yt_dlp.YoutubeDL(options) as ydl:
            info = ydl.extract_info(url, download=False)

        # Save the full info to file
        # helper.save_json_to_file(info, f"{app_config.DOWNLOAD_DIR}/{info.get('id')}_info.json")

        formats = info.get('formats', [])
        available_formats = []
        http_headers = info.get('http_headers', {})  # Get required headers

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
                'http_headers': http_headers  # Include headers for each format
            })
        sorted_formats = sorted(available_formats, key=lambda x: (x['filesize'] is None, x['filesize']))
        selected_format = sorted_formats[-1] if sorted_formats else None

        return {
            'message': 'Video info retrieved successfully',
            'video_info': {
                "title": info.get("title"),
                "duration": info.get("duration"),
                "video_id": info.get("id"),
                "size": selected_format.get('filesize') if selected_format else None,
                "size_in_mb": (selected_format.get('filesize') / (1024 * 1024)) if selected_format and selected_format.get('filesize') else None,
                "thumbnail": info.get("thumbnail"),
                'video_url': info.get('webpage_url'), 
                'webpage_url': info.get('webpage_url'),  # Original YouTube URL for viewing
                'direct_download_url': selected_format.get('url') if selected_format else None,  # Use with http_headers for download
                'http_headers': http_headers,  
                'available_formats': sorted_formats
            }
        }

    except Exception as e:
        raise ValueError(f"[video_info]: {str(e)}")


def extract_youtube_video_id(url: str) -> str:
    pattern = r'(?:https?:\/\/)?(?:www\.)?(?:youtube\.com\/(?:watch\?v=|embed\/|shorts\/)|youtu\.be\/)([a-zA-Z0-9_-]{11})'
    match = re.search(pattern, url)
    if match:
        return match.group(1)
    return url





def get_audio_url(video_url: str, region: str):
    """Get audio URL using yt-dlp Python package"""
    try:
        video_id = extract_youtube_video_id(video_url)
        video_url = f"https://www.youtube.com/watch?v={video_id}"
        print({'video_url': video_url, 'video_id': video_id})

        options = {
            "format": "bestaudio/best",
            "noplaylist": True,
            "quiet": True,
            'skip_download': True,
            'legacy_server_connect': True,
            'geo_bypass': True,
            'geo_bypass_country': region if region else 'US',
        }

        # Add proxy if available
        if app_config.settings.prepare_proxy(region):
            options['proxy'] = app_config.settings.prepare_proxy(region)

        with yt_dlp.YoutubeDL(options) as ydl:
            info = ydl.extract_info(video_url, download=False)

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
            'http_headers': http_headers,  # Required headers
            'warning': 'Audio URL expires in 5-6 hours. Use http_headers when accessing.',
            'webpage_url': info.get('webpage_url')
        }
        return audio_details

    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error {str(e)}")


