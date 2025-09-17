from fastapi import APIRouter, Request, Depends
from app.services.tools.socials import instagram_service, youtube_service, facebook_service, x_service, yt_dlp_service, vk_service
from fastapi import HTTPException
from app.utils.auth import authorize_user
import traceback
from app import config as  app_config



router = APIRouter()

# Instagram video download
@router.post("/tools/social/instagram/video-download")
async def instagram_download(request: Request, auth_data: dict = Depends(authorize_user)):
    
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
async def youtube_download(request: Request, auth_data: dict = Depends(authorize_user)):
    payload = await request.json()
    url = payload.get("url")
    if not url or 'youtube.com' not in url and 'youtu.be' not in url:
        raise HTTPException(status_code=400, detail="Invalid or missing Youtube URL.")
    
    try:
    
        return await youtube_service.download_video(url)
    except Exception as e:
        tb = traceback.format_exc()
        print('Error:[youtube] ' , (e) , '\n ' , tb)
        raise HTTPException(status_code=400, detail=f"Error: {str(e)}\nTraceback: {tb}")

# Youtube videos download
@router.post("/tools/social/youtube/audio-download")
async def youtube_audio_download( request: Request,  auth_data: dict = Depends(authorize_user)):
    
    payload = await request.json()
    url = payload.get("url")
    if not url or 'youtube.com' not in url and 'youtu.be' not in url:
        raise HTTPException(status_code=400, detail="Invalid or missing Youtube URL.")
    
    try:
        return youtube_service.get_audio_url(url)
    except Exception as e:
        tb = traceback.format_exc()
        print('Error:[youtube_audio] ' , (e) , '\n ' , tb)
        raise HTTPException(status_code=400, detail=f"Error: {str(e)}\nTraceback: {tb}")


# Facebook videos download
@router.post("/tools/social/facebook/video-download")
async def facebook_dowbload(request: Request, auth_data: dict = Depends(authorize_user)):
    
    payload = await request.json()
    url = payload.get("url")
    if not url or 'facebook.com' not in url:
        raise HTTPException(status_code=400, detail="Invalid or missing Facebook URL.")
    
    try:
    
        return await facebook_service.download_video(url, request, app_config.DOWNLOAD_DIR)
    except Exception as e:
        tb = traceback.format_exc()
        print('Error:[facebook] ' , (e) , '\n ' , tb)
        raise HTTPException(status_code=400, detail=f"Error: {str(e)}\nTraceback: {tb}")



# X videos download
@router.post("/tools/social/x-twitter/video-download")
async def facebook_dowbload(request: Request, auth_data: dict = Depends(authorize_user)):
    
    payload = await request.json()
    url = payload.get("url")
    try:
    
        return await x_service.download_video(url, request, app_config.DOWNLOAD_DIR)
    except Exception as e:
        tb = traceback.format_exc()
        print('Error:[X(twitter)] ' , (e) , '\n ' , tb)
        raise HTTPException(status_code=400, detail=f"Error: {str(e)}\nTraceback: {tb}")


# VK videos download
@router.post("/tools/social/vk/video-download")
async def vk_dowbload(request: Request, auth_data: dict = Depends(authorize_user)):
    
    payload = await request.json()
    url = payload.get("url")
    try:
    
        return await vk_service.download_video(url, request, app_config.DOWNLOAD_DIR)
    except Exception as e:
        tb = traceback.format_exc()
        print('Error:[VK platform] ' , (e) , '\n ' , tb)
        raise HTTPException(status_code=400, detail=f"Error: {str(e)}\nTraceback: {tb}")



# yt-dlp supprting facebook, youtube, instagram
@router.post("/download-video")
async def get_user(request: Request, auth_data: dict = Depends(authorize_user)):
    try:
        payload = await request.json()
        url = payload.get("url")
    
        return await yt_dlp_service.download_video(url, request)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to download video: {str(e)}")



@router.post("/get-video-info")
async def get_user(request: Request, auth_data: dict = Depends(authorize_user)):
    
    payload = await request.json()
    url = payload.get("url")
    try:
        return await yt_dlp_service.video_info(url)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to download video: {str(e)}")