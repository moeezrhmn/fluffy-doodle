import asyncio

# Max concurrent yt-dlp / ffmpeg processes across all download services.
# Each yt-dlp call can spike one CPU core to 100%, so cap at (cores - 1).
MAX_CONCURRENT_DOWNLOADS = 3  # 4-core AMD EPYC — reserve 1 core for event loop

_download_semaphore: asyncio.Semaphore | None = None


def get_download_semaphore() -> asyncio.Semaphore:
    global _download_semaphore
    if _download_semaphore is None:
        _download_semaphore = asyncio.Semaphore(MAX_CONCURRENT_DOWNLOADS)
    return _download_semaphore
