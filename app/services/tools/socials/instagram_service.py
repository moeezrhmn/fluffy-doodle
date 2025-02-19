
import instaloader, requests, os
from urllib.parse import urlparse, parse_qs
import math
from fastapi import Request
from app import config as app_config
from app.utils import helper


os.environ['https_proxy'] = "SOCKS5://198.12.249.249:62529"
# os.environ['https_proxy'] = 'https://' + app_config.IP2WORLD_PROXY


def download_video(post_url, request: Request, save_dir="downloads"):
    """Download Instagram video and extract its metadata"""
    
    L = instaloader.Instaloader()
    shortcode = extract_reel_id(post_url)
    # print('shortcode: ', shortcode)
    
    post = instaloader.Post.from_shortcode(L.context, shortcode)

    if not post.is_video:
        raise ValueError("The provided URL does not point to a video.")

    # Get video details
    video_url = post.video_url
    thumbnail_url = post.url
    caption = post.caption if post.caption else "No Caption"
    likes = post.likes if post.likes else "No Likes"
    profile = post.profile if post.profile else "No Profile"
    is_reel = post.is_video and post.typename == "GraphVideo"

    video_size = helper.get_video_size(video_url)
    if video_size and video_size > app_config.MAX_SIZE_LIMIT:
        raise ValueError(f'Max video size {app_config.MAX_SIZE_LIMIT} exceeded!')

    # Create directory if not exists
    # os.makedirs(save_dir, exist_ok=True)

    # Download Video
    file_name = f"{shortcode}.mp4"
    video_path = os.path.join(save_dir, file_name)
    if not os.path.exists(video_path):
        # response = requests.get(video_url, stream=True)
        # with open(video_path, "wb") as f:
        #     for chunk in response.iter_content(chunk_size=1024):
        #         f.write(chunk)
        helper.download_video(video_url, video_path)
    
    
    download_url = str(request.url_for("get_file", file_name=file_name))

    # Get video size
    video_size = os.path.getsize(video_path) / (1024 * 1024)  # Convert to MB

    # Download Thumbnail
    # thumbnail_path = os.path.join(save_dir, f"{shortcode}.jpg")
    # thumb_response = requests.get(thumbnail_url)
    # with open(thumbnail_path, "wb") as f:
    #     f.write(thumb_response.content)


    return {
        "download_url": download_url,
        "thumbnail": thumbnail_url,
        'size':f'{video_size} MB',
        'duration':post.video_duration,
        "title": caption,
        "is_reel": is_reel,
        'likes':post.likes,
        'profile':post.profile,
    }


def extract_reel_id(post_url):
    # Parse the URL
    parsed_url = urlparse(post_url)
    # Extract the path component (e.g., "/reel/DFZdkn-px3Y/")
    path = parsed_url.path
    # Split the path by '/' and get the reel ID
    parts = path.strip("/").split("/")
    # The reel ID is the second part (e.g., "reel/DFZdkn-px3Y" -> "DFZdkn-px3Y")
    if len(parts) >= 2 and parts[0] == "reel":
        return parts[1]
    
    return None
