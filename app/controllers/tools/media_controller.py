from typing import Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile

from app.services.tools.media import compress_service
from app.services.tools.media.compress_service import JobStatus
from app.utils.auth import authorize_user

router = APIRouter()

VALID_PRESETS = {"discord", "whatsapp", "email", "custom"}


@router.post("/tools/media/compress-video")
async def compress_video(
    request: Request,
    file: UploadFile = File(...),
    preset: str = Form("discord"),
    target_mb: Optional[int] = Form(None),
    auth_data: dict = Depends(authorize_user),
):
    content = await file.read()

    if len(content) > compress_service.MAX_FILE_SIZE_BYTES:
        raise HTTPException(status_code=413, detail="File too large. Maximum size is 200MB.")

    if file.content_type not in compress_service.ALLOWED_VIDEO_TYPES:
        raise HTTPException(status_code=415, detail="Unsupported file type.")

    if preset not in VALID_PRESETS:
        raise HTTPException(status_code=400, detail=f"Invalid preset. Use: {', '.join(VALID_PRESETS)}.")

    if preset == "custom" and not target_mb:
        raise HTTPException(status_code=400, detail="target_mb is required when preset is custom.")

    base_url = str(request.base_url)
    job = await compress_service.enqueue(content, preset, target_mb, base_url)
    position = compress_service.queue_position(job.job_id)

    return {
        "job_id": job.job_id,
        "status": job.status,
        "position": position,
    }


@router.get("/tools/media/job/{job_id}")
async def get_job_status(job_id: str, auth_data: dict = Depends(authorize_user)):
    job = compress_service.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found.")

    response = {"job_id": job_id, "status": job.status}

    if job.status == JobStatus.QUEUED:
        response["position"] = compress_service.queue_position(job_id)
    elif job.status == JobStatus.DONE:
        response["download_url"] = job.download_url
    elif job.status == JobStatus.ERROR:
        response["error"] = job.error

    return response


@router.delete("/tools/media/job/{job_id}")
async def delete_job(job_id: str, auth_data: dict = Depends(authorize_user)):
    job = compress_service.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found.")

    if job.status == JobStatus.PROCESSING:
        raise HTTPException(status_code=400, detail="Cannot delete a job that is currently processing.")

    compress_service.remove_job(job_id)
    return {"job_id": job_id, "deleted": True}
