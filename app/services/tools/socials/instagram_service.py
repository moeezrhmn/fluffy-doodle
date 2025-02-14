
import instaloader, requests, os
from urllib.parse import urlparse, parse_qs




L = instaloader.Instaloader()


def download_video(post_url, save_dir="downloads"):
    """Download Instagram video and extract its metadata"""
    
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

    # Create directory if not exists
    # os.makedirs(save_dir, exist_ok=True)

    # Download Video
    # video_path = os.path.join(save_dir, f"{shortcode}.mp4")
    # response = requests.get(video_url, stream=True)
    
    # with open(video_path, "wb") as f:
    #     for chunk in response.iter_content(chunk_size=1024):
    #         f.write(chunk)

    # Get video size
    # video_size = os.path.getsize(video_path) / (1024 * 1024)  # Convert to MB

    # Download Thumbnail
    # thumbnail_path = os.path.join(save_dir, f"{shortcode}.jpg")
    # thumb_response = requests.get(thumbnail_url)
    # with open(thumbnail_path, "wb") as f:
    #     f.write(thumb_response.content)

    # Print extracted information
    # print(f"Video downloaded: {video_url}")
    # print(f"Thumbnail downloaded: {thumbnail_url}")
    # print(f"Title (Caption): {caption}")
    # print(f"Video Size: {video_size:.2f} MB")
    # print(f"Is Reel: {is_reel}")

    return {
        "video_url": video_url,
        "thumbnail_url": thumbnail_url,
        "caption": caption,
        'video_duration':post.video_duration,
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
