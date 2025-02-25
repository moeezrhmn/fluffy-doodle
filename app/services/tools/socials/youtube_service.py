import yt_dlp
import requests, os, re, subprocess, json, uuid, asyncio
from typing import Tuple
from  pytubefix import YouTube
from fastapi import Request, HTTPException
# from pytubefix.helpers import reset_cache
from app import config as app_config
from app.utils import helper
from datetime import datetime

proxies = {"http": app_config.IP2WORLD_PROXY, "https": app_config.IP2WORLD_PROXY}
sticky_proxies = {"http": app_config.IP2WORLD_STICKY_PROXY, "https": app_config.IP2WORLD_STICKY_PROXY}

# async def download_video(video_url:str, request: Request, save_dir="downloads"):
#     """Download YouTube video and extract its metadata"""    
#     video_id = extract_youtube_video_id(video_url)  
#     video_url = f"https://www.youtube.com/watch?v={video_id}"
#     print({'video_id':video_id, 'video_url':video_url})
    

#     print('Starting youtube instance! ⌛')
#     yt = YouTube(
#         video_url,
#         proxies=proxies,
#     )

#     # Get video metadata
#     title = yt.title if yt.title else 'No title Found'
#     description = yt.description if yt.description else 'No Description Found'
#     thumbnail_url = yt.thumbnail_url if yt.thumbnail_url else 'No Thumbnail Found'
#     video_stream = yt.streams.get_highest_resolution()  

#     print(f'TITLE: {title}')
#     print(f'DESCRIPTION: {description[:100]} \n')

#     # video_stream = yt.streams.filter(progressive=True, file_extension="mp4", res="720p").first()
    
#     # if not video_stream:
#     #     video_stream = yt.streams.filter(progressive=True, file_extension="mp4").order_by("resolution").desc().first()
#     # if not video_stream:
#     #     raise ValueError("No valid video streams available for download!")


#     file_size = video_stream.filesize / (1024 * 1024)
#     # if file_size > app_config.MAX_SIZE_LIMIT:
#     #     raise ValueError(f'Max file size {app_config.MAX_SIZE_LIMIT} exceeded!')

#     # Create directory if not exists
#     # os.makedirs(save_dir, exist_ok=True)

#     # # Download video
#     # file_name = f"{datetime.today().strftime('%Y-%m-%d')}_{yt.video_id}.mp4"
#     # video_path = os.path.join(save_dir, file_name)
#     # if not os.path.exists(video_path):
#     #     # video_stream.download(output_path=save_dir, filename=file_name)
#     #     helper.download_video(video_stream.url, video_path, proxies=proxies)
        
#     # if  os.path.exists(video_path):
#     #     download_url = str(request.url_for("get_file", file_name=file_name))
#     # else:
#     #     download_url = video_stream.url

#     return {
#         "title": title,
#         "duration": 0,
#         "description": f"{description[:200]}...",
#         "thumbnail": thumbnail_url,
#         "size": round(video_stream.filesize, 2),
#         "size_in_mb": round(file_size, 2),
#         'url':video_stream.url,
#         "download_url": video_stream.url,
#     }

async def download_video(video_url:str, request: Request, save_dir="downloads"):

    try:
        video_id = extract_youtube_video_id(video_url)
        video_url = f"https://www.youtube.com/watch?v={video_id}"
        print({'video_url':video_url, 'video_id':video_id,})

        v_info = await video_info(video_url)
        return v_info

    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error {str(e)}")



async def video_info(url):
    try:
        ydl_opts = {
            "quiet": True,
            'nocheckcertificate': True,
            'proxy':app_config.IP2WORLD_PROXY,
            "format": 'best[ext=mp4]/best',
            "noplaylist": True,
            "list-formats": True,
            "socket_timeout": 30, 
            "http_chunk_size": 1048576,  
            "retries": 3, 
            "timeout": 60,
            'cookies-from-browser': 'chrome',
            'http_headers': {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.5735.110 Safari/537.36',
                'Accept-Language': 'en-US,en;q=0.9',
            }
            # 'cookies':'/var/www/fluffy-doodle/yt_cookies.txt'
        }
        def extract_info_async(url, ydl_opts):
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                print('[video_info] Starting scraping ⌛⌛')
                return ydl.extract_info(url, download=False)
        
        info = await asyncio.wait_for(asyncio.to_thread(extract_info_async, url, ydl_opts), timeout=60)
        print('[video_info] Scraping Completed ✅')

        # with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        #     print('[video_info] Starting scraping ⌛⌛')
        #     info = ydl.extract_info(url, download=False)
        #     print('[video_info] Scraping Completed ✅')

        
        selected_format = next((f for f in info.get("formats", []) if f.get("format_id") == info.get("format_id")), None)
        file_size = selected_format.get("filesize", 0) if selected_format else 0
        file_size_mb = round(file_size / (1024 * 1024), 2)
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