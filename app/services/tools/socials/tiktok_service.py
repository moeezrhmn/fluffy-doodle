import re, os
from fastapi import HTTPException
from app import config as app_config
from app.utils import helper
import yt_dlp



async def video_info(url, region: str, base_url: str = None):
    try:
        video_id = None

        info_options = {
            "quiet": True,
            'skip_download': True,
            'nocheckcertificate': True,  # Bypass SSL certificate verification
            'legacy_server_connect': True,  # Use legacy server connection
        }

        if app_config.settings.prepare_proxy(region):
            info_options['proxy'] = app_config.settings.prepare_proxy(region)
        
        with yt_dlp.YoutubeDL(info_options) as ydl:
            info = ydl.extract_info(url, download=False)

        video_id = info.get('id')

        # Save full info to a JSON file for debugging
        helper.save_json_to_file(info, f"{app_config.DOWNLOAD_DIR}/tiktok_{video_id}_info.json")

        # Now download the actual video
        output_filename = f"{app_config.DOWNLOAD_DIR}/tiktok_{video_id}.%(ext)s"

        download_options = {
            "quiet": True,
            'outtmpl': output_filename,
            # Add retry logic for handling temporary 403 errors
            'retries': 3,
            'fragment_retries': 3,
            # Select best format with video+audio
            'format': 'best[ext=mp4]/best',
            # SSL and connection options
            'nocheckcertificate': True,  # Bypass SSL certificate verification
            'legacy_server_connect': True,  # Use legacy server connection
        }

        with yt_dlp.YoutubeDL(download_options) as ydl:
            ydl.extract_info(url, download=True)

        downloaded_file = f"{app_config.DOWNLOAD_DIR}/tiktok_{video_id}.mp4"

        server_video_url = None
        if base_url:
            server_video_url = f"{base_url}/downloads/tiktok_{video_id}.mp4"

        # Get available formats info
        formats = info.get('formats', [])
        available_formats = []

        for fmt in formats:
            # Extract format fields
            protocol = fmt.get('protocol', '')
            vcodec = fmt.get('vcodec', 'none')
            acodec = fmt.get('acodec', 'none')

            # Skip if not http/https protocol
            if protocol not in ['https', 'http', 'http_dash_segments', 'm3u8', 'm3u8_native']:
                continue

            # Skip if no video codec (audio-only formats)
            if not vcodec or vcodec == 'none':
                continue

            # Get format details
            resolution = fmt.get('resolution')
            format_note = fmt.get('format_note') or resolution or 'unknown'
            ext = fmt.get('ext')
            filesize = fmt.get('filesize') or fmt.get('filesize_approx')
            format_id = fmt.get('format_id')
            width = fmt.get('width')
            height = fmt.get('height')
            tbr = fmt.get('tbr')

            available_formats.append({
                'format_id': format_id,
                'ext': ext,
                'resolution': resolution or f"{width}x{height}" if width and height else 'unknown',
                'format_note': format_note,
                'width': width,
                'height': height,
                'filesize': filesize,
                'filesize_mb': round(filesize / (1024 * 1024), 2) if filesize else None,
                'protocol': protocol,
                'vcodec': vcodec,
                'acodec': acodec,
                'bitrate': tbr,
            })

        # Sort by filesize (prefer larger/better quality)
        sorted_formats = sorted(available_formats, key=lambda x: x['filesize'] or 0)
        selected_format = sorted_formats[-1] if sorted_formats else None

        os.remove(f"{app_config.DOWNLOAD_DIR}/tiktok_{video_id}_info.json")

        return {
            'message': 'Video downloaded successfully',
            'region': region,
            'video_info': {
                "title": info.get("title"),
                "duration": info.get("duration"),
                "video_id": video_id,
                "size": selected_format.get('filesize') if selected_format else None,
                "size_in_mb": round(selected_format.get('filesize') / (1024 * 1024), 2) if selected_format and selected_format.get('filesize') else None,
                "thumbnail": info.get("thumbnail"),
                'webpage_url': info.get('webpage_url'),  # Original TikTok URL
                'video_url': server_video_url,  # URL to downloaded file on your server
                'download_url': server_video_url,  # URL to downloaded file on your server
                'local_path': downloaded_file,  # Local file path on server
                'available_formats': sorted_formats,
                'total_formats': len(sorted_formats)
            }
        }

    except Exception as e:
        raise ValueError(f"[video_info]: {str(e)}")

