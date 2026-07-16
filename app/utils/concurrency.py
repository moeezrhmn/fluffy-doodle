import asyncio
from contextlib import asynccontextmanager

MAX_CONCURRENT_DOWNLOADS = 3  # 4-core AMD EPYC — reserve 1 core for event loop

_download_semaphore: asyncio.Semaphore | None = None

downloads_active: int = 0
downloads_queued: int = 0


def get_download_semaphore() -> asyncio.Semaphore:
    global _download_semaphore
    if _download_semaphore is None:
        _download_semaphore = asyncio.Semaphore(MAX_CONCURRENT_DOWNLOADS)
    return _download_semaphore


@asynccontextmanager
async def download_slot():
    """Use instead of `async with get_download_semaphore()` — also tracks counts."""
    global downloads_active, downloads_queued
    downloads_queued += 1
    try:
        async with get_download_semaphore():
            downloads_queued -= 1
            downloads_active += 1
            try:
                yield
            finally:
                downloads_active -= 1
    except Exception:
        downloads_queued = max(0, downloads_queued - 1)
        raise