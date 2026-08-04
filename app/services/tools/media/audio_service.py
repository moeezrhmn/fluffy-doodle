import os
import subprocess
import uuid
from dataclasses import dataclass
from typing import List, Optional

import aiofiles
from starlette.concurrency import run_in_threadpool

from app import config as app_config
from app.utils.job_queue import JobStatus, RedisJobQueue

TEMP_DIR = "/tmp/multsaver"
MAX_FILE_SIZE_BYTES = 200 * 1024 * 1024
ALLOWED_INPUT_TYPES = {
    "video/mp4", "video/webm", "video/quicktime", "video/x-msvideo",
    "audio/mpeg", "audio/wav", "audio/ogg", "audio/mp4",
}
NUM_WORKERS = 2

MP3_QUALITY = {
    "high":   "320k",
    "medium": "192k",
    "low":    "128k",
}

AAC_QUALITY = {
    "high":   "256k",
    "medium": "192k",
    "low":    "128k",
}


@dataclass
class AudioJob:
    job_id: str
    input_path: str
    output_path: str
    format: str
    quality: str
    status: str = JobStatus.QUEUED
    error: Optional[str] = None
    download_url: Optional[str] = None


def cleanup(*paths: str) -> None:
    for path in paths:
        try:
            os.remove(path)
        except Exception:
            pass


def _ffmpeg(args: List[str]) -> None:
    cmd = ["nice", "-n", "15", "ffmpeg", "-y"] + args
    result = subprocess.run(cmd, capture_output=True)
    if result.returncode != 0:
        raise RuntimeError(result.stderr.decode("utf-8", errors="replace"))


def _run_extraction(input_path: str, output_path: str, fmt: str, quality: str) -> None:
    if fmt == "mp3":
        bitrate = MP3_QUALITY.get(quality, MP3_QUALITY["high"])
        _ffmpeg(["-i", input_path, "-vn", "-c:a", "libmp3lame", "-b:a", bitrate, output_path])
    elif fmt == "aac":
        bitrate = AAC_QUALITY.get(quality, AAC_QUALITY["high"])
        _ffmpeg(["-i", input_path, "-vn", "-c:a", "aac", "-b:a", bitrate, output_path])
    else:
        _ffmpeg(["-i", input_path, "-vn", "-c:a", "pcm_s16le", output_path])


async def _process(job: AudioJob) -> None:
    try:
        await run_in_threadpool(_run_extraction, job.input_path, job.output_path, job.format, job.quality)
        cleanup(job.input_path)
    except Exception:
        cleanup(job.input_path, job.output_path)
        raise


queue = RedisJobQueue(name="audio", job_class=AudioJob, process=_process, num_workers=NUM_WORKERS)


def start_workers() -> None:
    queue.start_workers()


async def enqueue(content: bytes, fmt: str, quality: str, base_url: str) -> AudioJob:
    os.makedirs(TEMP_DIR, exist_ok=True)
    os.makedirs(app_config.DOWNLOAD_DIR, exist_ok=True)

    job_id = str(uuid.uuid4())
    input_path = f"{TEMP_DIR}/{job_id}_input"
    output_filename = f"{job_id}_audio.{fmt}"
    output_path = os.path.join(app_config.DOWNLOAD_DIR, output_filename)
    download_url = f"{base_url.rstrip('/')}/downloads/{output_filename}"

    async with aiofiles.open(input_path, "wb") as f:
        await f.write(content)

    job = AudioJob(
        job_id=job_id,
        input_path=input_path,
        output_path=output_path,
        format=fmt,
        quality=quality,
        download_url=download_url,
    )
    await queue.enqueue(job)
    return job


def get_job(job_id: str) -> Optional[AudioJob]:
    return queue.get_job(job_id)


def queue_position(job_id: str) -> int:
    return queue.queue_position(job_id)


def remove_job(job_id: str) -> None:
    job = queue.get_job(job_id)
    queue.remove_job(job_id)
    if job:
        cleanup(job.input_path, job.output_path)
