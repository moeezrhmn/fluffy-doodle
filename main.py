# Entry point of the app
from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.responses import FileResponse, JSONResponse
from yt_dlp import YoutubeDL
import os, json, re, uuid
from datetime import datetime
from pydantic import BaseModel
import typing, urllib.parse
from app.utils.helper import (
    cleanup_old_files,
    bytes_to_mb,
)
from app.config import (
    DOWNLOAD_DIR,
    MAX_SIZE_LIMIT,
    VIDEO_FORMAT_QUALITY
)


# routers imports
from app.routers import user_router, tools_router

app = FastAPI()
app.include_router(user_router.router)
app.include_router(tools_router.router)


class VideoRequest(BaseModel):
    url: str
    
class VideoDownloadRequest(BaseModel):
    url: str
    format_id: typing.Optional[str] = VIDEO_FORMAT_QUALITY


# Root path
@app.get('/')
async def root():
    return {'message':'Tools APIs developed by MOEEZ UR REHMAN - [Profile: moeezrehman.dev] '}


@app.post("/download-video")
async def download_video(request: Request):
    """
    Downloads a Facebook video and returns the file stream URL.
    """
    body = await request.json()
    video_url = body.get("url")

    # Validate URL
    # if not video_url or not video_url.startswith("https://www.facebook.com"):
    #     raise HTTPException(status_code=400, detail="Invalid or missing Facebook URL.")

    try:
        v_info = await video_info(video_url)
        file_size = bytes_to_mb(v_info['size'])

        if file_size > MAX_SIZE_LIMIT:
            raise HTTPException(status_code=400, detail=f"File size exceeds {MAX_SIZE_LIMIT} MB limit.")
        
        cleanup_old_files(DOWNLOAD_DIR, days=1)

        ydl_opts = {
            "format": "best",
            "quiet": False,
            "outtmpl": f"{DOWNLOAD_DIR}/{datetime.today().strftime('%Y-%m-%d')}-{str(uuid.uuid4())[:8]}.%(ext)s",
            "postprocessors": [
                {
                    "key": "FFmpegVideoConvertor",
                    "preferedformat": "mp4"
                }
            ],
        }
        if 'https://youtu.be' in video_url:
            ydl_opts['cookiefile'] = "/tmp/cookies.txt"

        # Download the video
        with YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(video_url, download=True)
            file_path = ydl.prepare_filename(info)

            # Process file name
            file_name = os.path.basename(file_path)
            modified_file_name = file_name.lower().replace(" ", "-")
            modified_file_name = re.sub(r"[^a-z0-9\-\.]", "", modified_file_name)
            new_file_path = os.path.join(DOWNLOAD_DIR, modified_file_name)

            # Rename file
            os.rename(file_path, new_file_path)

        # Create a downloadable URL
        encoded_filename = urllib.parse.quote(modified_file_name)
        download_url = str(request.url_for("get_file", file_name=encoded_filename))
        response = {
            "title": info.get("title"),
            "duration": info.get("duration"),
            "size": file_size,
            "thumbnail": info.get("thumbnail"),
            'download_url': download_url,
            "formats": [
                {
                    "format_id": f["format_id"],
                    "resolution": f.get("resolution"), 
                    "filesize": f.get("filesize")
                }
                for f in info.get("formats", [])
            ],
        }
        return response

    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to download video: {str(e)}")


@app.post("/get-video-info")
async def get_video_info(request: Request):
    """
    Fetches metadata of a Facebook video without downloading.
    """
    try:
        body = await request.json()
        video_url = body.get("url")

        info = await video_info(video_url)
        # if not video_url or not video_url.startswith("https://www.facebook.com"):

        return JSONResponse(content={"video_info": info})
    except Exception as ex:
        raise HTTPException(status_code=400, detail=f"Error: {str(ex)}")



def get_file_size(info):
    import requests
    formats = info.get("formats", [])
    file_sizes = [f.get("filesize") for f in formats if f.get("filesize")]
    video_size = max(file_sizes) if file_sizes else None
    
    # if not video_size:
    #     bitrate = info.get("abr", 0) * 1024 
    #     duration = info.get("duration", 0) 
    #     video_size = int((bitrate * duration) / 8) if bitrate and duration else None

    if not video_size:
        response = requests.head(info["url"], allow_redirects=True)
        video_size = response.headers.get("Content-Length")
        if video_size:
            video_size = int(video_size) 

    return video_size






async def video_info(url):
    try:
        ydl_opts = {
            "quiet": True,
            "format": "best",
            "noplaylist": True,
            "skip_download": True,
            # "cookiefile": "/tmp/cookies.txt",
        }
        
        if 'https://youtu.be' in url:
            ydl_opts['cookiefile'] = "/tmp/cookies.txt"
        
        with YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)

        # file_path = "data.json"
        # create_json_fileoutput(file_path, info)

        file_size = get_file_size(info)
        video_details = {
            "title": info.get("title"),
            "duration": info.get("duration"),
            "size": file_size,
            "thumbnail": info.get("thumbnail"), 
            "formats": [
                {
                    "format_id": f["format_id"],
                    "resolution": f.get("resolution"), 
                    "filesize": f.get("filesize")
                }
                for f in info.get("formats", [])
            ],
        }
        return video_details
    except Exception as e:
        raise ValueError(f"[video_info]: {str(e)}")