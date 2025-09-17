import re
import subprocess
import json
from fastapi import HTTPException
from app import config as app_config
from app.utils import helper
import yt_dlp





async def download_video(video_url: str):
    """Get YouTube video information"""
    try:
        video_id = extract_youtube_video_id(video_url)
        video_url = f"https://www.youtube.com/watch?v={video_id}"
        print({'video_url': video_url, 'video_id': video_id})

        v_info = await video_info(video_url)
        return v_info

    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error {str(e)}")


async def video_info(url):
    """Get video information using yt-dlp command line tool"""
    try:
        options = {
            "format": "best",
            "noplaylist": True,
            "quiet": True,
            'skip_download': True,
            'legacy_server_connect': True,
        }
        
        # Add proxy if available
        if app_config.IP2WORLD_STICKY_PROXY:
            options['proxy'] = app_config.IP2WORLD_STICKY_PROXY
            

        with yt_dlp.YoutubeDL(options) as ydl:
            info = ydl.extract_info(url, download=False)

        
        # Save the full info to file
        helper.save_json_to_file(info, f"{app_config.DOWNLOAD_DIR}/{info.get('id')}_info.json")

        return {
            'message': 'Video info retrieved successfully',
            'video_info': {
                "title": info.get("title"),
                "duration": info.get("duration"),
                "size": None,
                "size_in_mb": None,
                "thumbnail": info.get("thumbnail"),
                'video_url': info.get('url'),
                'download_url': info.get('url'),
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


def get_audio_url(video_url):
    """Get audio URL using yt-dlp command line tool"""
    try:
        video_id = extract_youtube_video_id(video_url)
        video_url = f"https://www.youtube.com/watch?v={video_id}"
        print({'video_url': video_url, 'video_id': video_id})

        # Use yt-dlp command line for audio
        cmd = [
            'yt-dlp',
            '--dump-json',
            '--format', 'bestaudio/best',
        ]

        if app_config.IP2WORLD_STICKY_PROXY:
            cmd.extend(['--proxy', app_config.IP2WORLD_STICKY_PROXY])
            
        cmd.append(video_url)
        
        # Run the command
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        
        if result.returncode != 0:
            raise ValueError(f"yt-dlp command failed: {result.stderr}")
            
        # Parse the JSON output
        info = json.loads(result.stdout)

        audio_url = info.get('url')
        if not audio_url:
            raise ValueError("Audio URL not found in the extracted information.")

        audio_details = {
            "title": info.get("title"),
            "duration": info.get("duration"),
            "size": None,
            "size_in_mb": None,
            "thumbnail": info.get("thumbnail"),
            'audio_url': audio_url,
            'download_url': audio_url,
        }
        return audio_details

    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error {str(e)}")

