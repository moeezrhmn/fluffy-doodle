
from fastapi import APIRouter, Request
from app.services.tools.socials import instagram_service, youtube_service, yt_dlp_service
from fastapi import HTTPException


router = APIRouter()

# Instagram video download
@router.post("/tools/social/instagram/video-download")
async def get_user(request: Request):
    
    payload = await request.json()
    url = payload.get("url")
    if not url or not url.startswith("https://www.instagram.com"):
        raise HTTPException(status_code=400, detail="Invalid or missing Instagram URL.")
    
    try:
    
        return instagram_service.download_video(url, request)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to download video: {str(e)}")


# Youtube videos download
@router.post("/tools/social/youtube/video-download")
async def get_user(request: Request):
    
    payload = await request.json()
    url = payload.get("url")
    if not url or not url.startswith("https://youtube.com") and not url.startswith("https://youtu.be"):
        raise HTTPException(status_code=400, detail="Invalid or missing Youtube URL.")
    
    try:
    
        return youtube_service.download_video(url, request)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to download video: {str(e)}")

# yt-dlp supprting facebook, youtube, instagram
@router.post("/download-video")
async def get_user(request: Request):
    
    try:
        payload = await request.json()
        url = payload.get("url")
    
        return await yt_dlp_service.download_video(url)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to download video: {str(e)}")

@router.post("/get-video-info")
async def get_user(request: Request):
    
    payload = await request.json()
    url = payload.get("url")
    try:
        return await yt_dlp_service.video_info(url)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to download video: {str(e)}")