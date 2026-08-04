import os
import subprocess
import uuid
from dataclasses import dataclass
from typing import Optional

from starlette.concurrency import run_in_threadpool

from app.services.tools.pdf import common
from app.utils.job_queue import JobStatus, RedisJobQueue

MAX_FILE_SIZE_BYTES = 100 * 1024 * 1024
ALLOWED_CONTENT_TYPES = {"application/pdf"}

NUM_WORKERS = 2
MAX_QUEUE_DEPTH = 20  # beyond this, enqueue() raises QueueFullError -> caller returns 429

PRESETS = {
    # (dPDFSETTINGS, target color/gray image resolution) — minimal -> maximum compression
    "low": ("/prepress", 150),
    "recommended": ("/ebook", 150),
    "extreme": ("/screen", 72),
}


@dataclass
class PdfCompressJob:
    job_id: str
    input_path: str
    output_path: str
    download_url: str
    preset: str
    size_before: Optional[int] = None
    size_after: Optional[int] = None
    status: str = JobStatus.QUEUED
    error: Optional[str] = None


def _run_ghostscript(input_path: str, output_path: str, preset: str) -> None:
    pdf_settings, resolution = PRESETS[preset]
    cmd = [
        "gs", "-sDEVICE=pdfwrite", "-dCompatibilityLevel=1.4",
        f"-dPDFSETTINGS={pdf_settings}",
        # -dPDFSETTINGS alone silently no-ops on PDFs whose images are already
        # JPEG-encoded (the common case: scans, phone photos) — Ghostscript
        # passes already-JPEG streams through untouched by default. Forcing a
        # decode + downsample + re-encode is what actually shrinks these.
        "-dPassThroughJPEGImages=false",
        "-dDownsampleColorImages=true", f"-dColorImageResolution={resolution}",
        "-dColorImageDownsampleType=/Average",
        "-dAutoFilterColorImages=false", "-dColorImageFilter=/DCTEncode",
        "-dDownsampleGrayImages=true", f"-dGrayImageResolution={resolution}",
        "-dGrayImageDownsampleType=/Average",
        "-dAutoFilterGrayImages=false", "-dGrayImageFilter=/DCTEncode",
        "-dNOPAUSE", "-dQUIET", "-dBATCH",
        f"-sOutputFile={output_path}", input_path,
    ]
    result = subprocess.run(cmd, capture_output=True)
    if result.returncode != 0:
        raise RuntimeError(result.stderr.decode("utf-8", errors="replace"))


async def _process(job: PdfCompressJob) -> None:
    try:
        await run_in_threadpool(_run_ghostscript, job.input_path, job.output_path, job.preset)
        job.size_before = os.path.getsize(job.input_path)
        job.size_after = os.path.getsize(job.output_path)
        common.cleanup(job.input_path)
    except Exception:
        common.cleanup(job.input_path, job.output_path)
        raise


queue = RedisJobQueue(
    name="pdf_compress", job_class=PdfCompressJob, process=_process,
    num_workers=NUM_WORKERS, max_queue_depth=MAX_QUEUE_DEPTH,
)


def start_workers() -> None:
    queue.start_workers()


async def enqueue(content: bytes, preset: str, base_url: str) -> PdfCompressJob:
    input_path = await common.save_upload(content)
    output_path, download_url = common.make_output_path(base_url, prefix="compressed")

    job = PdfCompressJob(
        job_id=str(uuid.uuid4()),
        input_path=input_path,
        output_path=output_path,
        download_url=download_url,
        preset=preset,
    )
    await queue.enqueue(job)
    return job


def get_job(job_id: str) -> Optional[PdfCompressJob]:
    return queue.get_job(job_id)


def queue_position(job_id: str) -> int:
    return queue.queue_position(job_id)


def remove_job(job_id: str) -> None:
    job = queue.get_job(job_id)
    queue.remove_job(job_id)
    if job:
        common.cleanup(job.input_path, job.output_path)
