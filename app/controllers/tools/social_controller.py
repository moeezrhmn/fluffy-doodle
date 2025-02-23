
from fastapi import APIRouter, Request
from app.services.tools.socials import instagram_service, youtube_service, facebook_service, x_service, yt_dlp_service
from fastapi import HTTPException
import traceback
from app import config as  app_config


router = APIRouter()

# Instagram video download
@router.post("/tools/social/instagram/video-download")
async def instagram_download(request: Request):
    
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
async def youtube_download(request: Request):
    
    payload = await request.json()
    url = payload.get("url")
    if not url or not url.startswith("https://youtube.com") and not url.startswith("https://youtu.be") and not url.startswith('https://www.youtube.com'):
        raise HTTPException(status_code=400, detail="Invalid or missing Youtube URL.")
    
    try:
    
        return youtube_service.download_video(url, request, app_config.DOWNLOAD_DIR)
    except Exception as e:
        tb = traceback.format_exc()
        print('Error:[youtube] ' , (e) , '\n ' , tb)
        raise HTTPException(status_code=400, detail=f"Error: {str(e)}\nTraceback: {tb}")

# Facebook videos download
@router.post("/tools/social/facebook/video-download")
async def facebook_dowbload(request: Request):
    
    payload = await request.json()
    url = payload.get("url")
    if not url or not url.startswith("https://facebook.com") and not url.startswith('https://www.facebook.com'):
        raise HTTPException(status_code=400, detail="Invalid or missing Facebook URL.")
    
    try:
    
        return facebook_service.download_video(url, request, app_config.DOWNLOAD_DIR)
    except Exception as e:
        tb = traceback.format_exc()
        print('Error:[facebook] ' , (e) , '\n ' , tb)
        raise HTTPException(status_code=400, detail=f"Error: {str(e)}\nTraceback: {tb}")

# X videos download
@router.post("/tools/social/x-twitter/video-download")
async def facebook_dowbload(request: Request):
    
    payload = await request.json()
    url = payload.get("url")
    try:
    
        return x_service.download_video(url, request, app_config.DOWNLOAD_DIR)
    except Exception as e:
        tb = traceback.format_exc()
        print('Error:[X(twitter)] ' , (e) , '\n ' , tb)
        raise HTTPException(status_code=400, detail=f"Error: {str(e)}\nTraceback: {tb}")



# yt-dlp supprting facebook, youtube, instagram
@router.post("/download-video")
async def get_user(request: Request):
    
    try:
        payload = await request.json()
        url = payload.get("url")
    
        return await yt_dlp_service.download_video(url, request)
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