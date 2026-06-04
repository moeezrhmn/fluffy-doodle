import asyncio
import os
import re
import subprocess
import uuid
from dataclasses import dataclass
from typing import Dict, List, Optional

import aiofiles

from app import config as app_config

TEMP_DIR             = "/tmp/multsaver"
MAX_FILE_SIZE_BYTES  = 500 * 1024 * 1024   # 500 MB
ALLOWED_VIDEO_TYPES  = {"video/mp4", "video/webm", "video/quicktime", "video/x-msvideo"}
NUM_WORKERS          = 2

# Accepts HH:MM:SS, MM:SS, or plain seconds (int / float as string)
_TIME_RE = re.compile(r"^(\d+:)?(\d+:)?\d+(\.\d+)?$")


class JobStatus:
    QUEUED     = "queued"
    PROCESSING = "processing"
    DONE       = "done"
    ERROR      = "error"


@dataclass
class TrimJob:
    job_id:       str
    input_path:   str
    output_path:  str
    start:        str
    end:          str
    mode:         str
    status:       str = JobStatus.QUEUED
    error:        Optional[str] = None
    download_url: Optional[str] = None


jobs:   Dict[str, TrimJob] = {}
_queue: asyncio.Queue      = asyncio.Queue()


def validate_time(value: str) -> bool:
    return bool(_TIME_RE.match(value.strip()))


def _to_seconds(t: str) -> float:
    """Convert HH:MM:SS, MM:SS, or plain seconds string to float."""
    parts = t.strip().split(':')
    if len(parts) == 1:
        return float(parts[0])
    elif len(parts) == 2:
        return int(parts[0]) * 60 + float(parts[1])
    else:
        return int(parts[0]) * 3600 + int(parts[1]) * 60 + float(parts[2])


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


def _run_trim(input_path: str, output_path: str, start: str, end: str, mode: str) -> None:
    # Use duration instead of -to so output length is always correct.
    # With -ss before -i, -to is an absolute input timestamp which causes
    # the output to be longer than expected when FFmpeg snaps start to a keyframe.
    duration = str(round(_to_seconds(end) - _to_seconds(start), 6))

    if mode == "fast":
        # -ss before -i = fast keyframe seek (start may be slightly early)
        # -t duration = correct output length regardless of keyframe snap
        # -map 0 = include all streams (video + audio)
        _ffmpeg([
            "-ss", start,
            "-i", input_path,
            "-t", duration,
            "-map", "0",
            "-c", "copy",
            "-avoid_negative_ts", "make_zero",
            output_path,
        ])
    else:
        # -ss after -i = slow decode but frame-accurate start
        # -t duration = exact output length
        _ffmpeg([
            "-i", input_path,
            "-ss", start,
            "-t", duration,
            "-map", "0:v:0",
            "-map", "0:a:0?",
            "-c:v", "libx264",
            "-preset", "fast",
            "-c:a", "aac",
            "-movflags", "+faststart",
            output_path,
        ])


async def _worker() -> None:
    while True:
        job: TrimJob = await _queue.get()
        job.status = JobStatus.PROCESSING
        try:
            await asyncio.get_event_loop().run_in_executor(
                None, _run_trim,
                job.input_path, job.output_path, job.start, job.end, job.mode,
            )
            job.status = JobStatus.DONE
            cleanup(job.input_path)
        except Exception as e:
            job.status = JobStatus.ERROR
            job.error  = str(e)
            print(f"[trim] Error for job {job.job_id}:\n{e}")
            cleanup(job.input_path, job.output_path)
        finally:
            _queue.task_done()


def start_workers() -> None:
    for _ in range(NUM_WORKERS):
        asyncio.create_task(_worker())


async def enqueue(content: bytes, start: str, end: str, mode: str, base_url: str) -> TrimJob:
    os.makedirs(TEMP_DIR, exist_ok=True)
    os.makedirs(app_config.DOWNLOAD_DIR, exist_ok=True)

    job_id          = str(uuid.uuid4())
    input_path      = f"{TEMP_DIR}/{job_id}_input.mp4"
    output_filename = f"{job_id}_trimmed.mp4"
    output_path     = os.path.join(app_config.DOWNLOAD_DIR, output_filename)
    download_url    = f"{base_url.rstrip('/')}/downloads/{output_filename}"

    async with aiofiles.open(input_path, "wb") as f:
        await f.write(content)

    job = TrimJob(
        job_id=job_id,
        input_path=input_path,
        output_path=output_path,
        start=start,
        end=end,
        mode=mode,
        download_url=download_url,
    )
    jobs[job_id] = job
    await _queue.put(job)
    return job


def get_job(job_id: str) -> Optional[TrimJob]:
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
