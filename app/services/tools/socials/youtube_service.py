from pytubefix import YouTube
import requests, os, re, subprocess, json
from typing import Tuple
# from pytubefix.helpers import reset_cache
from app import config as app_config
from app.utils import helper



def download_video(video_url, save_dir="downloads"):
    """Download YouTube video and extract its metadata"""    
    if "youtu.be/" in video_url:
        video_id = video_url.split("/")[-1].split("?")[0]  # Extract video ID
        video_url = f"https://www.youtube.com/watch?v={video_id}"

    if not re.search(r"(youtube\.com/watch\?v=|youtube\.com/shorts/)", video_url):
        raise ValueError("Invalid YouTube video or Shorts URL!")
    # po_tv = po_token_verifier()
    
    proxy = {
        "https": "https://164.163.42.2:10000"
    }
    yt = YouTube(
        video_url, 
        proxies=proxy
        # 'WEB'
    )

    # Get video metadata
    title = 'No Title Found'
    description = yt.description if yt.description else 'No Description Found'
    thumbnail_url = yt.thumbnail_url if yt.thumbnail_url else 'No Thumbnail Found'
    video_stream = yt.streams.get_highest_resolution()  # Get highest quality video
    file_size = video_stream.filesize / (1024 * 1024)  # Convert to MB

    if file_size > app_config.MAX_SIZE_LIMIT:
        raise ValueError(f'Max file size {app_config.MAX_SIZE_LIMIT} exceeded!')

    # Create directory if not exists
    # os.makedirs(save_dir, exist_ok=True)

    # # Download video
    # video_path = os.path.join(save_dir, f"{yt.video_id}.mp4")
    # video_stream.download(output_path=save_dir, filename=f"{yt.video_id}.mp4")

    # Download thumbnail
    # thumbnail_path = os.path.join(save_dir, f"{yt.video_id}.jpg")
    # thumb_response = requests.get(thumbnail_url)
    # with open(thumbnail_path, "wb") as f:
    #     f.write(thumb_response.content)

    # Print extracted information
    # print(f"Video Title: {title}")
    # print(f"Description: {description[:200]}...")  # Limit description preview
    # print(f"Thumbnail URL: {thumbnail_url}")
    # print(f"Video Size: {file_size:.2f} MB")
    # print(f"Video url: {video_stream.url}")
    # print(f"Thumbnail url: {thumbnail_url}")

    return {
        "title": title,
        "description": description,
        "thumbnail": thumbnail_url,
        "download_url": video_stream.url,
        "size": f'{file_size:.2f} MB',
    }




# def po_token_verifier() -> Tuple[str, str]:
#     token_object = generate_youtube_token()
#     return token_object["visitorData"], token_object["poToken"]

def po_token_verifier():
    result = subprocess.run(
        ["youtube-po-token-generator"],
        capture_output=True,
        text=True
    )
    data = json.loads(result.stdout)
    print('PO token: ', data)
    return data["visitorData"], data["poToken"]

def generate_youtube_token() -> dict:
    print("Generating YouTube token")
    result = cmd("node scripts/youtube-token-generator.js")
    data = json.loads(result.stdout)
    print(f"Result: {data}")
    return data


def cmd(command, check=True, shell=True, capture_output=True, text=True):
    """
    Runs a command in a shell and throws an exception if the return code is non-zero.
    """
    print(f"Running command: {command}")  # Debugging log
    try:
        result = subprocess.run(command, check=check, shell=shell, capture_output=capture_output, text=text)
        print(f"Command Output: {result.stdout}")  # Debugging log
        return result
    except subprocess.CalledProcessError as error:
        print(f"Error running command: {command}")  # Debugging log
        print(f"STDOUT: {error.stdout}")
        print(f"STDERR: {error.stderr}")
        raise
