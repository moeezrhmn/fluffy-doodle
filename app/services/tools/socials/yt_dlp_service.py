from fastapi import Request, HTTPException
from yt_dlp import YoutubeDL
import os, json, re, uuid, math
from datetime import datetime
from pydantic import BaseModel
import typing, urllib.parse
from app.utils.helper import (
    bytes_to_mb,
    get_video_size,
    create_json_fileoutput
)
from app.config import (
    DOWNLOAD_DIR,
    MAX_SIZE_LIMIT,
    VIDEO_FORMAT_QUALITY,
    IP2WORLD_PROXY
)

VALID_VIDEO_DOMAINS = re.compile(r"^(https?:\/\/)?(www\.)?"
                                r"(facebook\.com|fb\.watch|instagram\.com|instagr\.am|youtube\.com|youtu\.be)", re.IGNORECASE)

class VideoRequest(BaseModel):
    url: str
    
class VideoDownloadRequest(BaseModel):
    url: str
    format_id: typing.Optional[str] = VIDEO_FORMAT_QUALITY



async def download_video(video_url, request: Request):
    """
    Downloads a Facebook video and returns the file stream URL.
    """

    # Validate URL
    if not video_url or not VALID_VIDEO_DOMAINS.match(video_url):
        raise HTTPException(status_code=400, detail="Invalid or unsupported video URL.")

    try:
        v_info = video_info(video_url)

        if v_info['size_in_mb'] > MAX_SIZE_LIMIT:
            raise HTTPException(status_code=400, detail=f"File size exceeds {MAX_SIZE_LIMIT} MB limit.")
        

        ydl_opts = {
            'proxy': IP2WORLD_PROXY,
            "format": 'best',
            # "quiet": False,
            "outtmpl": f"{DOWNLOAD_DIR}/{datetime.today().strftime('%Y-%m-%d')}-{str(uuid.uuid4())[:8]}.%(ext)s",
            'progress_hooks': [lambda d: print(f"Status: {d['status']}, Downloaded: {d.get('downloaded_bytes', 0)} bytes")],
            # "postprocessors": [
            #     {
            #         "key": "FFmpegVideoConvertor",
            #         "preferedformat": "mp4"
            #     }
            # ],
        }

        # Download the video
        with YoutubeDL(ydl_opts) as ydl:
            print('Start Downloader: ⏳⏳')
            info = ydl.extract_info(video_url, download=True)
            file_path = ydl.prepare_filename(info)
            print('Start Downloader: ⏳⏳')

            print('file_path: ', file_path)
            # Process file name
            file_name = os.path.basename(file_path)
 

        download_url = str(request.url_for("get_file", file_name=file_name))
        response = {
            "title": info.get("title"),
            "duration": info.get("duration"),
            "size_in_mb": v_info['size_in_mb'],
            "size": v_info['size'],
            "thumbnail": info.get("thumbnail"),
            'download_url': download_url,
        }
        return response

    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error {str(e)}")




def video_info(url):
    try:
        ydl_opts = {
            "quiet": True,
            'proxy':IP2WORLD_PROXY,
            "format": 'best',
            #   VIDEO_FORMAT_QUALITY,
            "noplaylist": True,
            "list-formats": True
        }
        with YoutubeDL(ydl_opts) as ydl:
            print('Starting scraping ⌛⌛')
            info = ydl.extract_info(url, download=False)
            print('Scraping Completed ✅')

        
        selected_format = next((f for f in info.get("formats", []) if f.get("format_id") == info.get("format_id")), None)
        file_size = selected_format.get("filesize", 0) if selected_format else 0
        file_size_mb = round(file_size / (1024 * 1024), 2)

        # file_path = "data.json"
        # create_json_fileoutput(file_path, info)

        video_details = {
            "title": info.get("title"),
            "duration": info.get("duration"),
            "size": file_size,
            "size_in_mb": file_size_mb,
            "thumbnail": info.get("thumbnail"), 
        }
        return video_details
    except Exception as e:
        raise ValueError(f"[video_info]: {str(e)}")