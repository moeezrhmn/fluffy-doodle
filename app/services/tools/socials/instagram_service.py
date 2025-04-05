
import instaloader, requests, os, math, yt_dlp
from urllib.parse import urlparse, parse_qs
from fastapi import Request, HTTPException
from app import config as app_config
from app.utils import helper

os.environ['https_proxy'] = app_config.IP2WORLD_STICKY_PROXY


def download_video(post_url, request: Request, save_dir="downloads"):
    """Download Instagram video and extract its metadata"""
    try:
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
        likes = post.likes if post.likes else 0
        profile = post.profile if post.profile else "No Profile"
        is_reel = post.is_video and post.typename == "GraphVideo"
        
        # Response with video URL and metadata
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
    except Exception as ex:
        raise ValueError(f"[instagram][video can be age restricted require login to download]: {str(ex)}")

    # Download Video
    # file_name = f"{shortcode}.mp4"
    # video_path = os.path.join(save_dir, file_name)
    # if not os.path.exists(video_path):
    #     # response = requests.get(video_url, stream=True)
    #     # with open(video_path, "wb") as f:
    #     #     for chunk in response.iter_content(chunk_size=1024):
    #     #         f.write(chunk)
    #     helper.download_video(video_url, video_path)
    
    
    # download_url = str(request.url_for("get_file", file_name=file_name))

    # Get video size
    # video_size = os.path.getsize(video_path) / (1024 * 1024)  # Convert to MB



def extract_reel_id(post_url):

    parsed_url = urlparse(post_url)
    path = parsed_url.path
    parts = path.strip("/").split("/")
    if len(parts) >= 2 and parts[0] == "reel":
        return parts[1]
    
    return None
