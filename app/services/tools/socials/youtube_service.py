from pytubefix import YouTube
import requests, os, re

def download_video(video_url, save_dir="downloads"):
    """Download YouTube video and extract its metadata"""

    if "youtu.be/" in video_url:
        video_id = video_url.split("/")[-1].split("?")[0]  # Extract video ID
        video_url = f"https://www.youtube.com/watch?v={video_id}"

    # Check if URL is a valid YouTube video or Shorts link
    if not re.search(r"(youtube\.com/watch\?v=|youtube\.com/shorts/)", video_url):
        raise ValueError("Invalid YouTube video or Shorts URL!")

    
    # Load YouTube video
    yt = YouTube(video_url)
    # return yt
    # Get video metadata
    title = 'No Title Found'
    description = yt.description if yt.description else 'No Description Found'
    thumbnail_url = yt.thumbnail_url if yt.thumbnail_url else 'No Thumbnail Found'
    video_stream = yt.streams.get_highest_resolution()  # Get highest quality video
    file_size = video_stream.filesize / (1024 * 1024)  # Convert to MB

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
        "thumbnail_url": thumbnail_url,
        "video_url": video_stream.url,
        "file_size": f'{file_size:.2f} MB',
    }

