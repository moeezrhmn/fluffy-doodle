import os
import json


download_dir = 'downloads'

if not os.path.exists(download_dir):
    os.makedirs(download_dir)

# Find the first JSON file in the download directory and load its data
first_json_file = None
for root, dirs, files in os.walk(download_dir):
    for file in files:
        if file.endswith('.json'):
            first_json_file = os.path.join(root, file)
            break
    if first_json_file:
        break

file_data = None
if first_json_file:
    with open(first_json_file, 'r') as f:
        file_data = json.load(f)
else:
    print("No JSON file found.")

video_formats = []
print('formats: ', len(file_data.get('formats', [])))

for fmt in file_data.get('formats', []):
    if not fmt.get('protocol') in ['https', 'http'] or fmt.get('audio_channels') is None or fmt.get('resolution') == 'audio only':
            continue  

    resolution = fmt.get('format_note')
    ext = fmt.get('ext')
    filesize = fmt.get('filesize') or fmt.get('filesize_approx')
    url = fmt.get('url')

    video_formats.append({
        'ext': ext,
        'resolution': resolution,
        'filesize': filesize,
        'url': url
    })
    
print('video_formats: ', video_formats)
