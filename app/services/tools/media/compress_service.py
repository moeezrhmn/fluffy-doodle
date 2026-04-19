import asyncio
import os
import shutil
import subprocess
import uuid
from dataclasses import dataclass
from typing import Dict, List, Optional

import aiofiles
import ffmpeg

TEMP_DIR = "/tmp/multsaver"
MAX_FILE_SIZE_BYTES = 200 * 1024 * 1024
ALLOWED_VIDEO_TYPES = {"video/mp4", "video/webm", "video/quicktime", "video/x-msvideo"}
NUM_WORKERS = 2

# Target sizes in MB per preset
PRESETS = {
    "discord":  {"target_mb": 25, "scale": "1280:720", "audio_kbps": 128},
    "whatsapp": {"target_mb": 16, "scale": "1280:720", "audio_kbps": 96},
    "email":    {"target_mb": 10, "scale": "854:480",  "audio_kbps": 96},
}

class JobStatus:
    QUEUED     = "queued"
    PROCESSING = "processing"
    DONE       = "done"
    ERROR      = "error"


@dataclass
class Job:
    job_id: str
    input_path: str
    output_path: str
    preset: str
    target_mb: Optional[int]
    status: str = JobStatus.QUEUED
    error: Optional[str] = None


jobs: Dict[str, Job] = {}
_queue: asyncio.Queue = asyncio.Queue()


def cleanup(*paths: str) -> None:
    for path in paths:
        try:
            os.remove(path)
        except Exception:
            pass


def _get_duration(input_path: str) -> float:
    probe = ffmpeg.probe(input_path)
    return float(probe["format"]["duration"])


def _ffmpeg(args: List[str]) -> None:
    cmd = ["nice", "-n", "15", "ffmpeg", "-y"] + args
    result = subprocess.run(cmd, capture_output=True)
    if result.returncode != 0:
        raise RuntimeError(result.stderr.decode("utf-8", errors="replace"))


def _run_ffmpeg(input_path: str, output_path: str, preset: str, target_mb: Optional[int]) -> None:
    p = PRESETS.get(preset)
    size_mb = target_mb if preset == "custom" else p["target_mb"]
    audio_kbps = 128 if preset == "custom" else p["audio_kbps"]

    input_size_mb = os.path.getsize(input_path) / (1024 * 1024)

    # Skip compression if input is already under target — copy as-is
    if input_size_mb <= size_mb:
        shutil.copy2(input_path, output_path)
        return

    duration = _get_duration(input_path)
    video_kbps = max(100, int((size_mb * 1024 * 8) / duration) - audio_kbps)
    passlog = output_path.replace(".mp4", "")
    scale_filter = f'scale={p["scale"]}:force_original_aspect_ratio=decrease,scale=trunc(iw/2)*2:trunc(ih/2)*2' if p else None

    base_args = ["-i", input_path, "-c:v", "libx264", "-b:v", f"{video_kbps}k", "-preset", "fast"]
    if scale_filter:
        base_args += ["-vf", scale_filter]

    # Pass 1 — analysis only
    _ffmpeg(base_args + ["-pass", "1", "-passlogfile", passlog, "-an", "-f", "null", "/dev/null"])

    # Pass 2 — encode with audio
    _ffmpeg(base_args + [
        "-pass", "2", "-passlogfile", passlog,
        "-c:a", "aac", "-b:a", f"{audio_kbps}k",
        "-movflags", "+faststart",
        output_path,
    ])

    # Clean up 2-pass log files
    for ext in ("-0.log", "-0.log.mbtree"):
        try:
            os.remove(passlog + ext)
        except Exception:
            pass


async def _worker() -> None:
    while True:
        job: Job = await _queue.get()
        job.status = JobStatus.PROCESSING
        try:
            await asyncio.get_event_loop().run_in_executor(
                None, _run_ffmpeg, job.input_path, job.output_path, job.preset, job.target_mb
            )
            job.status = JobStatus.DONE
            cleanup(job.input_path)  # input no longer needed after compression
        except Exception as e:
            job.status = JobStatus.ERROR
            job.error = str(e)
            print(f"[compress] Error for job {job.job_id}:\n{e}")
            cleanup(job.input_path, job.output_path)
        finally:
            _queue.task_done()


def start_workers() -> None:
    for _ in range(NUM_WORKERS):
        asyncio.create_task(_worker())


async def enqueue(content: bytes, preset: str, target_mb: Optional[int]) -> Job:
    os.makedirs(TEMP_DIR, exist_ok=True)
    job_id = str(uuid.uuid4())
    input_path = f"{TEMP_DIR}/{job_id}_input.mp4"
    output_path = f"{TEMP_DIR}/{job_id}_output.mp4"

    async with aiofiles.open(input_path, "wb") as f:
        await f.write(content)

    job = Job(
        job_id=job_id,
        input_path=input_path,
        output_path=output_path,
        preset=preset,
        target_mb=target_mb,
    )
    jobs[job_id] = job
    await _queue.put(job)
    return job


def get_job(job_id: str) -> Optional[Job]:
    return jobs.get(job_id)


def queue_position(job_id: str) -> int:
    pos = 0
    for jid, job in jobs.items():
        if jid == job_id:
            return pos + 1
        if job.status == JobStatus.QUEUED:
            pos += 1
    return 0


def remove_job(job_id: str) -> None:
    job = jobs.pop(job_id, None)
    if job:
        cleanup(job.input_path, job.output_path)
