from pydantic import BaseModel
import subprocess, urllib, os, json, re
from datetime import datetime
from yt_dlp import YoutubeDL
from fastapi import  HTTPException
from helper_functions import generate_filename_from_url

video_format_quality = 'best[height<=720]'
MAX_FILE_SIZE_MB = 100


def sanitize_filename(filename):
    """
    Sanitize the filename by replacing spaces with hyphens and removing special characters.
    """
    filename = filename.lower().replace(" ", "-")
    return re.sub(r"[^a-z0-9\-\.]", "", filename)

def download_facebook_video(video_url, output_path="downloads"):

    filename = f"{datetime.today().strftime('%Y-%m-%d')}-{sanitize_filename(video_url)}"
    expected_file_path = os.path.join(output_path, f"{filename}.mp4")
    
    # Delete if already exists
    if os.path.exists(expected_file_path):
        os.remove(expected_file_path)
        print(f"✅ Deleted existing file: {expected_file_path}")

    ydl_opts = {
        "format": "best",
        "quiet": False,
        "outtmpl": f"{output_path}/{filename}.%(ext)s",
        "postprocessors": [
            {"key": "FFmpegVideoConvertor", "preferedformat": "mp4"}
        ],
    }

    with YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(video_url, download=True)
        file_path = ydl.prepare_filename(info)

        # Rename the file properly
        modified_file_name = sanitize_filename(os.path.basename(file_path))
        new_file_path = os.path.join(output_path, modified_file_name)

        os.rename(file_path, new_file_path)
        print(f"Downloaded and renamed file: {new_file_path}")

    # Create a downloadable URL
    encoded_filename = urllib.parse.quote(modified_file_name)
    return encoded_filename

def download_youtube_video(video_url, output_path='downloads', format_id=video_format_quality):
 
    filename = f"{datetime.today().strftime('%Y-%m-%d')}-{sanitize_filename(video_url)}"
    expected_file_path = os.path.join(output_path, f"{filename}.mp4")
    
    # Delete if already exists
    if os.path.exists(expected_file_path):
        os.remove(expected_file_path)
        print(f"✅ Deleted existing file: {expected_file_path}")

    # Proceed with the download
    ydl_opts = {
        "format": format_id or "best",
        "quiet": False,
        "outtmpl": f"{output_path}/{filename}.%(ext)s",
        "postprocessors": [
            {"key": "FFmpegVideoConvertor", "preferedformat": "mp4"}
        ],
    }

    with YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(video_url, download=True)
        file_path = ydl.prepare_filename(info)

        modified_file_name = os.path.basename(file_path)
        new_file_path = os.path.join(output_path, modified_file_name)

        os.rename(file_path, new_file_path)
        print(f"Downloaded and renamed file: {new_file_path}")

    return urllib.parse.quote(modified_file_name)



def get_video_info(url: str):
    """Extract video metadata using yt-dlp with cookies."""
    ydl_opts = {
        'quiet': False,
        'format':'best'
        # 'simulate': True,
        # 'cookies': 'cookies.txt',
        # 'verbose': True,
        # 'http_headers': {
        # 'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        # 'Accept-Language': 'en-US,en;q=0.9',
    }
    
    with YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=False)
        print('info here : ', info)
        return info