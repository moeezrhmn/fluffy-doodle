from typing import Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile

from app.services.tools.media import audio_service, compress_service
from app.services.tools.media.compress_service import JobStatus
from app.utils.auth import authorize_user

VALID_FORMATS  = {"mp3", "wav"}
VALID_QUALITIES = {"high", "medium", "low"}

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


# ── Audio extraction ────────────────────────────────────────────────────────

@router.post("/tools/media/extract-audio")
async def extract_audio(
    request: Request,
    file: UploadFile = File(...),
    format: str = Form("mp3"),
    quality: str = Form("high"),
    auth_data: dict = Depends(authorize_user),
):
    content = await file.read()

    if len(content) > audio_service.MAX_FILE_SIZE_BYTES:
        raise HTTPException(status_code=413, detail="File too large. Maximum size is 200MB.")

    if file.content_type not in audio_service.ALLOWED_INPUT_TYPES:
        raise HTTPException(status_code=415, detail="Unsupported file type.")

    if format not in VALID_FORMATS:
        raise HTTPException(status_code=400, detail="Invalid format. Use: mp3, wav.")

    if format == "mp3" and quality not in VALID_QUALITIES:
        raise HTTPException(status_code=400, detail="Invalid quality. Use: high, medium, low.")

    base_url = str(request.base_url)
    job = await audio_service.enqueue(content, format, quality, base_url)
    position = audio_service.queue_position(job.job_id)

    return {
        "job_id": job.job_id,
        "status": job.status,
        "position": position,
    }


@router.get("/tools/media/audio-job/{job_id}")
async def get_audio_job_status(job_id: str, auth_data: dict = Depends(authorize_user)):
    job = audio_service.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found.")

    response = {"job_id": job_id, "status": job.status, "format": job.format}

    if job.status == audio_service.JobStatus.QUEUED:
        response["position"] = audio_service.queue_position(job_id)
    elif job.status == audio_service.JobStatus.DONE:
        response["download_url"] = job.download_url
    elif job.status == audio_service.JobStatus.ERROR:
        response["error"] = job.error

    return response


@router.delete("/tools/media/audio-job/{job_id}")
async def delete_audio_job(job_id: str, auth_data: dict = Depends(authorize_user)):
    job = audio_service.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found.")

    if job.status == audio_service.JobStatus.PROCESSING:
        raise HTTPException(status_code=400, detail="Cannot delete a job that is currently processing.")

    audio_service.remove_job(job_id)
    return {"job_id": job_id, "deleted": True}
