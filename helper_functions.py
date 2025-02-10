from urllib.parse import urlparse
from datetime import datetime, timedelta
import glob, os, hashlib, math, json


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
