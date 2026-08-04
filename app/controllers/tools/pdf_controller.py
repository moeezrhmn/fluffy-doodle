from typing import List, Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile

from app.services.tools.pdf import compress_service, image_convert_service, merge_service, split_service
from app.utils.auth import authorize_user
from app.utils.job_queue import JobStatus, QueueFullError

router = APIRouter()

VALID_SPLIT_OUTPUTS = {"files", "zip"}


@router.post("/tools/pdf/merge")
async def merge_pdfs(
    request: Request,
    files: List[UploadFile] = File(...),
    auth_data: dict = Depends(authorize_user),
):
    if len(files) < 2:
        raise HTTPException(status_code=400, detail="Provide at least 2 PDF files to merge.")
    if len(files) > merge_service.MAX_FILES:
        raise HTTPException(status_code=400, detail=f"Too many files. Maximum is {merge_service.MAX_FILES}.")

    contents = []
    for file in files:
        if file.content_type not in merge_service.ALLOWED_CONTENT_TYPES:
            raise HTTPException(status_code=415, detail=f"Unsupported file type: {file.content_type}.")
        content = await file.read()
        if len(content) > merge_service.MAX_FILE_SIZE_BYTES:
            raise HTTPException(status_code=413, detail="File too large. Maximum size is 50MB per file.")
        contents.append(content)

    base_url = str(request.base_url)
    try:
        download_url = await merge_service.merge(contents, base_url)
    except Exception as e:
        raise HTTPException(status_code=422, detail=f"Failed to merge PDFs: {e}")

    return {"download_url": download_url}


@router.post("/tools/pdf/split")
async def split_pdf(
    request: Request,
    file: UploadFile = File(...),
    ranges: Optional[str] = Form(None),
    every_n: Optional[int] = Form(None),
    output: str = Form("files"),
    auth_data: dict = Depends(authorize_user),
):
    if file.content_type not in split_service.ALLOWED_CONTENT_TYPES:
        raise HTTPException(status_code=415, detail=f"Unsupported file type: {file.content_type}.")

    content = await file.read()
    if len(content) > split_service.MAX_FILE_SIZE_BYTES:
        raise HTTPException(status_code=413, detail="File too large. Maximum size is 50MB.")

    if not ranges and not every_n:
        raise HTTPException(status_code=400, detail="Provide either 'ranges' or 'every_n'.")

    if output not in VALID_SPLIT_OUTPUTS:
        raise HTTPException(status_code=400, detail="Invalid output. Use: files, zip.")

    base_url = str(request.base_url)
    try:
        result = await split_service.split(content, ranges, every_n, output, base_url)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=422, detail=f"Failed to split PDF: {e}")

    return result


@router.post("/tools/pdf/jpg-to-pdf")
async def jpg_to_pdf(
    request: Request,
    files: List[UploadFile] = File(...),
    auth_data: dict = Depends(authorize_user),
):
    if not files:
        raise HTTPException(status_code=400, detail="Provide at least 1 image.")
    if len(files) > image_convert_service.MAX_IMAGES:
        raise HTTPException(status_code=400, detail=f"Too many images. Maximum is {image_convert_service.MAX_IMAGES}.")

    contents = []
    for file in files:
        if file.content_type not in image_convert_service.ALLOWED_IMAGE_TYPES:
            raise HTTPException(status_code=415, detail=f"Unsupported file type: {file.content_type}.")
        content = await file.read()
        if len(content) > image_convert_service.MAX_FILE_SIZE_BYTES:
            raise HTTPException(status_code=413, detail="File too large. Maximum size is 25MB per image.")
        contents.append(content)

    base_url = str(request.base_url)
    try:
        download_url = await image_convert_service.images_to_pdf(contents, base_url)
    except Exception as e:
        raise HTTPException(status_code=422, detail=f"Failed to convert images to PDF: {e}")

    return {"download_url": download_url}


@router.post("/tools/pdf/pdf-to-jpg")
async def pdf_to_jpg(
    request: Request,
    file: UploadFile = File(...),
    format: str = Form("jpg"),
    dpi: int = Form(image_convert_service.DEFAULT_DPI),
    output: str = Form("files"),
    auth_data: dict = Depends(authorize_user),
):
    if file.content_type not in image_convert_service.ALLOWED_PDF_TYPES:
        raise HTTPException(status_code=415, detail=f"Unsupported file type: {file.content_type}.")

    content = await file.read()
    if len(content) > image_convert_service.MAX_PDF_SIZE_BYTES:
        raise HTTPException(status_code=413, detail="File too large. Maximum size is 50MB.")

    if format not in image_convert_service.VALID_IMAGE_FORMATS:
        raise HTTPException(status_code=400, detail="Invalid format. Use: jpg, png.")

    if not (image_convert_service.MIN_DPI <= dpi <= image_convert_service.MAX_DPI):
        raise HTTPException(
            status_code=400,
            detail=f"Invalid dpi. Use a value between {image_convert_service.MIN_DPI} and {image_convert_service.MAX_DPI}.",
        )

    if output not in VALID_SPLIT_OUTPUTS:
        raise HTTPException(status_code=400, detail="Invalid output. Use: files, zip.")

    base_url = str(request.base_url)
    try:
        result = await image_convert_service.pdf_to_images(content, format, dpi, output, base_url)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=422, detail=f"Failed to convert PDF to images: {e}")

    return result


@router.post("/tools/pdf/compress")
async def compress_pdf(
    request: Request,
    file: UploadFile = File(...),
    preset: str = Form("recommended"),
    auth_data: dict = Depends(authorize_user),
):
    if file.content_type not in compress_service.ALLOWED_CONTENT_TYPES:
        raise HTTPException(status_code=415, detail=f"Unsupported file type: {file.content_type}.")

    content = await file.read()
    if len(content) > compress_service.MAX_FILE_SIZE_BYTES:
        raise HTTPException(status_code=413, detail="File too large. Maximum size is 100MB.")

    if preset not in compress_service.PRESETS:
        raise HTTPException(status_code=400, detail=f"Invalid preset. Use: {', '.join(compress_service.PRESETS)}.")

    base_url = str(request.base_url)
    try:
        job = await compress_service.enqueue(content, preset, base_url)
    except QueueFullError as e:
        raise HTTPException(status_code=429, detail=str(e))

    position = compress_service.queue_position(job.job_id)
    return {"job_id": job.job_id, "status": job.status, "position": position}


@router.get("/tools/pdf/compress/job/{job_id}")
async def get_compress_job(job_id: str, auth_data: dict = Depends(authorize_user)):
    job = compress_service.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found.")

    response = {"job_id": job_id, "status": job.status}

    if job.status == JobStatus.QUEUED:
        response["position"] = compress_service.queue_position(job_id)
    elif job.status == JobStatus.DONE:
        response["download_url"] = job.download_url
        response["size_before"] = job.size_before
        response["size_after"] = job.size_after
    elif job.status == JobStatus.ERROR:
        response["error"] = job.error

    return response


@router.delete("/tools/pdf/compress/job/{job_id}")
async def delete_compress_job(job_id: str, auth_data: dict = Depends(authorize_user)):
    job = compress_service.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found.")

    if job.status == JobStatus.PROCESSING:
        raise HTTPException(status_code=400, detail="Cannot delete a job that is currently processing.")

    compress_service.remove_job(job_id)
    return {"job_id": job_id, "deleted": True}
