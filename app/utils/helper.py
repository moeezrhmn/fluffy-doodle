# Utility functions


from urllib.parse import urlparse
from datetime import datetime, timedelta
import glob, os, hashlib, math, json, requests, random
from app import config as app_config
from concurrent.futures import ThreadPoolExecutor
from tqdm import tqdm



def is_valid_url(url: str) -> bool:
    parsed = urlparse(url)
    return bool(parsed.netloc) and bool(parsed.scheme)


def cleanup_old_files(directory: str, days: int):
    """
    Delete files in the specified directory older than `days` days.
    """
    now = datetime.now()
    cutoff_time = now - timedelta(days=days)  # Get the exact cutoff time

    for file_path in glob.glob(os.path.join(directory, "*")):
        if os.path.isfile(file_path):
            file_mtime = datetime.fromtimestamp(os.path.getmtime(file_path))  # Get last modified time
            
            if file_mtime < cutoff_time:  # Check if older than allowed days
                try:
                    os.remove(file_path)
                    print(f"✅ Deleted old file: {file_path}")
                except Exception as e:
                    print(f"❌ Failed to delete {file_path}: {e}")
            else:
                print(f"⏳ File not old enough: {file_path} (Modified: {file_mtime})")
                

def generate_filename_from_url(url: str) -> str:
    """
    Generate a unique filename based on the URL to prevent duplicate downloads.
    """
    hash_object = hashlib.md5(url.encode())  
    return f"{hash_object.hexdigest()}.mp4"

def bytes_to_mb(bytes_size):
    return math.floor(bytes_size / (1024 * 1024))  # 1 MB = 1024 * 1024 bytes

def create_json_fileoutput(file_path, info):
    
    if not os.path.exists(file_path):
        with open(file_path, 'w') as json_file:
            json.dump(info, json_file, indent=4)
    else:
        with open(file_path, 'r+') as json_file:
            existing_data = json.load(json_file)
            existing_data.update(info)  # Merge data
            json_file.seek(0)
            json.dump(existing_data, json_file, indent=4)


def get_video_size(video_url, proxies=None):
    """Fetch video size from the Content-Length header."""
    response = requests.head(video_url, proxies=proxies) 
    content_length = response.headers.get('Content-Length')
    print('content-length: ', content_length)
    if content_length:
        return round(int(content_length) / (1024 * 1024), 2)
    return None


def get_random_proxy():
    proxy = random.choice(app_config.PROXIES)
    return proxy
    

def download_part(url, start, end, filename, proxies=None):
    headers = {"Range": f"bytes={start}-{end}", "User-Agent": "Mozilla/5.0"}
    
    try:
        response = requests.get(url, headers=headers, stream=True, proxies=proxies, timeout=30)
        response.raise_for_status()

        # Write content to file with proper thread safety
        if response.status_code in [200, 206]:  # 206 = Partial Content
            with open(filename, "r+b") as f:
                f.seek(start)
                f.write(response.content)
        else:
            print(f"Failed to download part {start}-{end}. Status code: {response.status_code}")

    except Exception as e:
        print(f"Error downloading part {start}-{end}: {e}")

def download_video_parallel(url, video_path, num_threads=4, proxies=None):
    try:
        response = requests.get(url, proxies=proxies, timeout=30, headers={"User-Agent": "Mozilla/5.0"})
        response.raise_for_status()
        file_size = int(response.headers.get("content-length", 0))

        if file_size == 0:
            print("Failed to get content length from the server.")
            return

        part_size = file_size // num_threads

        # Pre-allocate the file with the expected size
        with open(video_path, "wb") as f:
            f.truncate(file_size)

        with ThreadPoolExecutor(max_workers=num_threads) as executor:
            futures = []
            for i in range(num_threads):
                start = i * part_size
                # Ensure the last part covers up to the last byte
                end = (i + 1) * part_size - 1 if i < num_threads - 1 else file_size - 1
                
                futures.append(executor.submit(download_part, url, start, end, video_path, proxies))
            
            for future in futures:
                future.result()

        print("Parallel download completed successfully.")

    except Exception as e:
        print(f"Error during parallel download: {e}")

# def download_video(url, video_path, chunk_size=8192, proxies=None):   
#     response = requests.get(url, stream=True, proxies=proxies)
#     with open(video_path, "wb") as f:
#         for chunk in response.iter_content(chunk_size=chunk_size):
#             print(f'downloading video. Chunk: {chunk_size} ')
#             f.write(chunk)

def download_video(url, video_path, chunk_size=8192, proxies=None):
    response = requests.get(url, stream=True, proxies=proxies)
    total_size = int(response.headers.get('content-length', 0))

    # Show progress bar
    with open(video_path, "wb") as f, tqdm(
        desc="Downloading Video",
        total=total_size,
        unit='B',
        unit_scale=True,
        unit_divisor=1024,
    ) as progress_bar:
        for chunk in response.iter_content(chunk_size=chunk_size):
            if chunk:
                f.write(chunk)
                progress_bar.update(len(chunk))

    print("Download completed!")
    

def save_json_to_file(data, file_path):
    os.makedirs(os.path.dirname(file_path), exist_ok=True)
    with open(file_path, 'w') as json_file:
        json.dump(data, json_file, indent=4)