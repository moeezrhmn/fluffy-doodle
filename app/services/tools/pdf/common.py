import os
import uuid
from functools import partial
from typing import Any, Callable

import aiofiles
from starlette.concurrency import run_in_threadpool

from app import config as app_config

TEMP_DIR = "/tmp/filemutate"

# Above this page count, a Lane A (sync) tool should hand the request off to a
# Lane B queued job instead of running inline — keeps a single oversized file
# from tying up a thread-pool slot for everyone else.
PAGE_COUNT_ESCALATION_THRESHOLD = 50


async def run_cpu_bound(fn: Callable, *args: Any, **kwargs: Any) -> Any:
    """Runs a blocking pikepdf/img2pdf/PyMuPDF call off the event loop via Starlette's threadpool."""
    return await run_in_threadpool(partial(fn, *args, **kwargs))


def cleanup(*paths: str) -> None:
    for path in paths:
        try:
            os.remove(path)
        except Exception:
            pass


async def save_upload(content: bytes, suffix: str = ".pdf") -> str:
    os.makedirs(TEMP_DIR, exist_ok=True)
    input_path = os.path.join(TEMP_DIR, f"{uuid.uuid4()}_input{suffix}")
    async with aiofiles.open(input_path, "wb") as f:
        await f.write(content)
    return input_path


def make_output_path(base_url: str, suffix: str = ".pdf", prefix: str = "output") -> tuple[str, str]:
    """Returns (output_path, download_url) for a file that will be served from DOWNLOAD_DIR."""
    os.makedirs(app_config.DOWNLOAD_DIR, exist_ok=True)
    filename = f"{uuid.uuid4()}_{prefix}{suffix}"
    output_path = os.path.join(app_config.DOWNLOAD_DIR, filename)
    download_url = f"{base_url.rstrip('/')}/downloads/{filename}"
    return output_path, download_url
