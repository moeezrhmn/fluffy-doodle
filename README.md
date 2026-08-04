# fluffy-doodle

FastAPI backend: social media downloaders, PDF tools, plagiarism detection, temp email, and related utilities.

## Docs

Supplementary docs live in [`docs/`](docs/):

- [`docs/PDF_TOOLS_API.md`](docs/PDF_TOOLS_API.md) — API integration guide for the PDF tools (`/tools/pdf/*`), for whoever is wiring up the frontend/client side.
- [`docs/INSTAGRAM_SETUP.md`](docs/INSTAGRAM_SETUP.md) — Instagram account rotation setup.
- [`docs/BGUTIL_SERVER_SETUP.md`](docs/BGUTIL_SERVER_SETUP.md), [`docs/YOUTUBE_YTDLP_NOTES.md`](docs/YOUTUBE_YTDLP_NOTES.md) — YouTube/yt-dlp notes.
- [`docs/VIDEO_COMPRESSOR_API.md`](docs/VIDEO_COMPRESSOR_API.md) — video compress/trim/audio-extract API notes.
- [`docs/systemd_run.txt`](docs/systemd_run.txt) — systemd service template.

`CLAUDE.md` stays at the repo root rather than moving into `docs/` — Claude Code loads it specifically from that location as project instructions, not as a browsable doc.

## System dependencies

Beyond `pip install -r requirements.txt`, some tools shell out to system binaries that must be installed separately on the host (dev machine or server):

| Binary | Used by | Install (macOS) | Install (Debian/Ubuntu) |
|---|---|---|---|
| `ffmpeg` | Video compress/trim, audio extraction (`app/services/tools/media/`) | `brew install ffmpeg` | `apt install ffmpeg` |
| `gs` (Ghostscript) | PDF Compress (`app/services/tools/pdf/compress_service.py`) | `brew install ghostscript` | `apt install ghostscript` |
| `deno` | YouTube n-challenge solving via yt-dlp | see [yt-dlp docs](https://github.com/yt-dlp/yt-dlp) | same |

Planned tools that will add further binary dependencies as they're built (not required yet):

| Binary | Will be used by |
|---|---|
| LibreOffice (`soffice`) | Word/PPT/Excel ↔ PDF conversions |
| Tesseract | OCR PDF (`ocrmypdf`) |
| Playwright/Chromium (`playwright install`) | HTML to PDF |

Redis must also be running locally for the app to start (`app.config.redis_client`, plus the Redis-backed job queue in `app/utils/job_queue.py`) — `brew install redis && redis-server` for local dev.