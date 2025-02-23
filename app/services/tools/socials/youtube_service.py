import yt_dlp
import requests, os, re, subprocess, json, uuid
from typing import Tuple
from fastapi import Request, HTTPException
# from pytubefix.helpers import reset_cache
from app import config as app_config
from app.utils import helper
from datetime import datetime

proxies = {"http": app_config.IP2WORLD_PROXY, "https": app_config.IP2WORLD_PROXY}
sticky_proxies = {"http": app_config.IP2WORLD_STICKY_PROXY, "https": app_config.IP2WORLD_STICKY_PROXY}

# def download_video(video_url:str, request: Request, save_dir="downloads"):
#     """Download YouTube video and extract its metadata"""    
#     if "youtu.be/" in video_url:
#         video_id = video_url.split("/")[-1].split("?")[0]  # Extract video ID
#         video_url = f"https://www.youtube.com/watch?v={video_id}"

#     if not re.search(r"(youtube\.com/watch\?v=|youtube\.com/shorts/)", video_url):
#         raise ValueError("Invalid YouTube video or Shorts URL!")
#     # po_tv = po_token_verifier()

#     print('starting youtube instance!')
#     yt = YouTube(
#         video_url,
#         proxies=proxies,
#     )

#     # Get video metadata
#     title = yt.title if yt.title else 'No title Found'
#     description = yt.description if yt.description else 'No Description Found'
#     thumbnail_url = yt.thumbnail_url if yt.thumbnail_url else 'No Thumbnail Found'
#     # video_stream = yt.streams.get_highest_resolution()  

#     print(f'TITLE: {title}')
#     print(f'DESCRIPTION: {description[:100]} \n')

#     video_stream = yt.streams.filter(progressive=True, file_extension="mp4", res="720p").first()
    
#     if not video_stream:
#         video_stream = yt.streams.filter(progressive=True, file_extension="mp4").order_by("resolution").desc().first()
#     if not video_stream:
#         raise ValueError("No valid video streams available for download!")


#     file_size = video_stream.filesize / (1024 * 1024)  # Convert to MB
#     if file_size > app_config.MAX_SIZE_LIMIT:
#         raise ValueError(f'Max file size {app_config.MAX_SIZE_LIMIT} exceeded!')

#     # Create directory if not exists
#     os.makedirs(save_dir, exist_ok=True)

#     # # Download video
#     file_name = f"{datetime.today().strftime('%Y-%m-%d')}_{yt.video_id}.mp4"
#     video_path = os.path.join(save_dir, file_name)
#     if not os.path.exists(video_path):
#         # video_stream.download(output_path=save_dir, filename=file_name)
#         helper.download_video(video_stream.url, video_path, proxies=proxies)
        
#     if  os.path.exists(video_path):
#         download_url = str(request.url_for("get_file", file_name=file_name))
#     else:
#         download_url = video_stream.url
#     return {
#         "title": title,
#         "description": f"{description[:200]}...",
#         "thumbnail": thumbnail_url,
#         "download_url": download_url,
#         "size": f'{file_size:.2f} MB',
#     }

def download_video(video_url:str, request: Request, save_dir="downloads"):

    try:
        video_id = extract_youtube_video_id(video_url)
        video_url = f"https://www.youtube.com/watch?v={video_id}"
        print({'video_url':video_url, 'video_id':video_id,})

        v_info = video_info(video_url)
        return v_info

    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error {str(e)}")



def video_info(url):
    try:
        ydl_opts = {
            "quiet": True,
            'proxy':app_config.IP2WORLD_PROXY,
            "format": 'best',
            "noplaylist": True,
            "list-formats": True,
            "socket_timeout": 30, 
            "http_chunk_size": 1048576,  
            "retries": 3, 
            "timeout": 60,
            'cookies':'/var/www/fluffy-doodle/yt_cookies.txt'
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            print('[video_info] Starting scraping ⌛⌛')
            info = ydl.extract_info(url, download=False)
            print('[video_info] Scraping Completed ✅')

        
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
            'url':info['url'],
            'download_url':info['url'],
        }
        return video_details
    except Exception as e:
        raise ValueError(f"[video_info]: {str(e)}")


def extract_youtube_video_id(url: str) -> str:
    pattern = r'(?:https?:\/\/)?(?:www\.)?(?:youtube\.com\/(?:watch\?v=|embed\/|shorts\/)|youtu\.be\/)([a-zA-Z0-9_-]{11})'
    match = re.search(pattern, url)
    if match:
        return match.group(1)
    return url