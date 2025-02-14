
from fastapi import APIRouter, Request
from app.services.tools.socials import instagram_service, youtube_service
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
    
        return instagram_service.download_video(url)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to download video: {str(e)}")


# Youtube videos download
@router.post("/tools/social/youtube/video-download")
async def get_user(request: Request):
    
    payload = await request.json()
    url = payload.get("url")
    if not url or not url.startswith("https://www.youtube.com") and not url.startswith("https://youtu.be"):
        raise HTTPException(status_code=400, detail="Invalid or missing Youtube URL.")
    
    try:
    
        return youtube_service.download_video(url)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to download video: {str(e)}")