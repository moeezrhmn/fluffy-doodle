# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Development Commands

### Running the Application
```bash
# Activate virtual environment
source venv/bin/activate

# Install dependencies (see README.md for the system binaries these assume)
pip install -r requirements.txt

# Redis must be running first — the app raises at startup if it can't PING
redis-server

# Run development server with auto-reload
uvicorn main:app --reload

# Run production server
gunicorn main:app -w 4 -k uvicorn.workers.UvicornWorker
```

`requirements.txt` currently contains **two concatenated `pip freeze` dumps** (424 lines; every package is pinned twice, e.g. `yt-dlp` at both line 210 and line 422). When changing a pin, change both occurrences.

### Testing
There is no test suite. `pytest`, `pytest-asyncio`, and `pytest-cov` are installed but no `tests/` directory exists, and root-level `test.py` is a throwaway script that reads JSON metadata out of `downloads/` — not a test. Verify changes by running the server and exercising endpoints.

### Database Management
```bash
alembic upgrade head                                  # apply migrations
alembic revision --autogenerate -m "description"      # create migration
alembic downgrade -1                                  # roll back one
```
Only one model exists (`app/models/user.py`) and one migration. Postgres backs authentication only — every tool feature stores its state in Redis or on disk, not in the database.

### Production Deployment
```bash
# Systemd service management
sudo systemctl daemon-reload
sudo systemctl restart fastapi
sudo systemctl status fastapi

# NGINX
sudo nginx -t && sudo systemctl restart nginx
```
See [docs/systemd_run.txt](docs/systemd_run.txt) for the service template and firewall notes.

## Architecture Overview

### Layered Architecture
Request flow: **Router → Controller → Service** (→ Repository → Model for the user/auth path only).

- **Routers** (`app/routers/`): `tools_router.py` aggregates every tool controller; `user_router.py` covers auth.
- **Controllers** (`app/controllers/`): HTTP handling, upload validation, Pydantic request models. Routes are declared with full paths on an unprefixed `APIRouter` (`@router.post("/tools/pdf/merge")`) rather than router prefixes — except `user_controller.py`, which uses `prefix="/users"`.
- **Services** (`app/services/`): all business logic; where the real complexity lives.
- **Repositories / Models / Schemas**: used only by the user/auth path.

Every `/tools/*` endpoint is protected by `Depends(authorize_user)`. `POST /users/signup` is intentionally stubbed out to return `"signup is disabled for now!"` — new accounts are inserted into the database by hand.

### The two execution lanes (most important pattern here)

Tool endpoints are split into two lanes, and which lane a new tool belongs in is the first design decision to make:

**Lane A — synchronous.** Fast operations (PDF merge/split, JPG↔PDF, all social downloads) respond in the same request. Blocking CPU work goes through `run_in_threadpool` — see `common.run_cpu_bound()` in [app/services/tools/pdf/common.py](app/services/tools/pdf/common.py). Do not add custom semaphores to Lane A tools.

**Lane B — queued jobs.** Heavy operations (PDF compress, video compress/trim, audio extract) return a `job_id` immediately and are polled via a status endpoint, because they outlast a normal HTTP timeout. All of them are built on `RedisJobQueue` ([app/utils/job_queue.py](app/utils/job_queue.py)):
- Queue and job state live in **Redis**, using the existing *sync* client — deliberately, so `get_job()`/`queue_position()` stay plain functions and job status is consistent across gunicorn worker processes (an in-process dict cannot guarantee that).
- A service defines a JSON-serializable `@dataclass` job + an async `process(job)`, and the base class owns the `QUEUED → PROCESSING → DONE/ERROR` transitions and persistence.
- `max_queue_depth` makes `enqueue()` raise `QueueFullError`; controllers translate that to **429**.
- Workers are started in the `lifespan` hook in [main.py](main.py) — a new Lane B service must add its `start_workers()` call there or its jobs will queue forever.
- Job metadata TTL is 2h (`JOB_TTL_SECONDS`), deliberately longer than the output-file lifetime.

`PAGE_COUNT_ESCALATION_THRESHOLD` (50 pages) in `pdf/common.py` marks where a Lane A tool should hand off to Lane B. `pdf-to-jpg` currently hard-caps at that number instead, as a stand-in until it gets a queue.

### Concurrency for social downloads
[app/utils/concurrency.py](app/utils/concurrency.py) holds a process-wide `asyncio.Semaphore` (`MAX_CONCURRENT_DOWNLOADS = 7`, I/O-bound not CPU-bound) exposed as the `download_slot()` async context manager. Every social service wraps its actual fetch in it. `RequestLogMiddleware` in [main.py](main.py) rejects new `/tools/social` requests with **429** once `downloads_queued` exceeds `MAX_QUEUE_THRESHOLD` (6) — i.e. backpressure is applied at the edge, before a request ever reaches a service.

### Middleware stack and monitoring
Two middlewares wrap every request. Starlette applies the last-added one outermost, so `RequestLogMiddleware` sees the request first and `TimeoutMiddleware`'s 504s are logged as ordinary failed responses:
- `RequestLogMiddleware` (outer): applies the social backpressure check, records `/tools/*` and `/users/*` traffic into Redis via [app/utils/monitor.py](app/utils/monitor.py), and buffers 4xx/5xx response bodies so failures are visible in the dashboard.
- `TimeoutMiddleware` (inner): enforces `REQUEST_TIMEOUT`; 504 on timeout, 500 otherwise.

`GET /monitor` serves a self-contained HTML dashboard (inlined as a string in `main.py`) that reads a live snapshot over the `/ws/monitor` WebSocket. Proxy bytes are attributed per-request through a `ContextVar` set by the middleware and incremented by services.

### Storage and file serving
- `downloads/` is mounted at `/downloads` as static files; Lane B jobs write their output there and return a URL built by `common.make_output_path()`.
- Uploads land in scratch dirs first — `/tmp/filemutate` (PDF) and `/tmp/multsaver` (media) — and are cleaned up on both success and failure paths.
- `app/utils/cache.py` is a thread-safe in-memory TTL cache (15 min default) used for hot lookups; it is per-process, so it is not a substitute for Redis when state must be shared across gunicorn workers.

### Key features

**Social media downloaders** ([app/services/tools/socials/](app/services/tools/socials/)): YouTube, Instagram, Facebook, X/Twitter, TikTok, VK, plus `yt_dlp_service.py` as a generic fallback. Most accept a `region` parameter that selects an IP2World proxy via `settings.prepare_proxy(region)`.

**PDF tools** ([app/services/tools/pdf/](app/services/tools/pdf/)): merge/split (`pikepdf`), JPG→PDF (`img2pdf`), PDF→JPG (`PyMuPDF`), compress (Ghostscript, Lane B). This is the backend for FileMutate, a separate Laravel frontend repo — [docs/PDF_TOOLS_API.md](docs/PDF_TOOLS_API.md) is the client integration contract and [docs/TOOLS-ROADMAP.md](docs/TOOLS-ROADMAP.md) tracks shipped vs. planned tools (mirrored from the FileMutate repo — keep both in sync).

**Media tools** ([app/services/tools/media/](app/services/tools/media/)): video compress, trim, and audio extraction — all Lane B, all shelling out to `ffmpeg` under `nice -n 15`. Compress uses size-target presets (`discord`/`whatsapp`/`email`) and short-circuits to a plain copy when the input is already under target.

**Plagiarism detection** ([app/services/plagiarism/](app/services/plagiarism/)): preprocessing → Google Custom Search crawling → sentence-transformer + FAISS similarity.

**AI content detection** ([app/services/ai_detection.py](app/services/ai_detection.py)): GoWinston API wrapper.

**Temporary email** ([app/services/temp_mail_service.py](app/services/temp_mail_service.py)): Redis-backed throwaway addresses, expiry via `EMAIL_EXPIRY`.

## Environment Configuration

**Required:**
- `DATABASE_HOST`, `DATABASE_NAME`, `DATABASE_USERNAME`, `DATABASE_PASSWORD`, `DATABASE_PORT`
- `SECRET_KEY`, `ACCESS_TOKEN_EXPIRE_MINUTES` (currently set to roughly a year), `ALGORITHM`
- `REDIS_HOST`, `REDIS_PORT`, `REDIS_DB` — Redis is a hard startup dependency
- `REQUEST_TIMEOUT`: global request timeout in seconds
- `TEMP_MAIL_DOMAIN`, `TEMP_MAIL_USERNAME`, `TEMP_MAIL_PASSWORD`, `EMAIL_EXPIRY`
- `IP2WORLD_USERNAME`, `IP2WORLD_PASSWORD`, `IP2WORLD_HOST`, `IP2WORLD_PROXY`, `IP2WORLD_STICKY_PROXY`
- `GOOGLE_CUSTOM_SEARCH_API_KEY`, `GOOGLE_CUSTOM_SEARCH_ENGINE_ID`
- `HUGGING_FACE_API_KEY`, `GO_WINSTON_BASE_URL`, `GO_WINSTON_AI_API_KEY`, `RAPID_API_KEY`

Note: the proxy provider in `.env` has drifted from the variable names — the active credentials are a 711proxy endpoint stored in the `IP2WORLD_*` variables, with the original IP2World entries commented out as no longer working.

**Optional Instagram account rotation (for age-restricted content):** `INSTAGRAM_USERNAME`/`INSTAGRAM_PASSWORD`, then `_2`, `_3`, … See [docs/INSTAGRAM_SETUP.md](docs/INSTAGRAM_SETUP.md).

## Important Implementation Notes

**YouTube URL handling:** extracted URLs expire in 5–6 hours and require HTTP headers. Responses carry `video_url`/`download_url` (programmatic use only — pass the returned `http_headers` with the request), `http_headers`, `webpage_url` (the one to open in a browser), and `video_id`. Direct URLs opened in a browser will fail; that is expected, not a bug.

**YouTube extraction is fragile by nature:** the `web` client needs the EJS solver plus Deno ≥ 2.3.0 on PATH, and other clients are broken for their own reasons. Read [docs/YOUTUBE_YTDLP_NOTES.md](docs/YOUTUBE_YTDLP_NOTES.md) before touching `youtube_service.py` extractor args — the `js_runtimes`/`remote_components` option shapes are easy to break. Install/upgrade with `pip install -U "yt-dlp[default]"`; plain `yt-dlp` ships without the solver.

**Ghostscript compression:** a bare `-dPDFSETTINGS` silently no-ops on PDFs whose images are already JPEG-encoded (scans, phone photos — the common case). The explicit `-dPassThroughJPEGImages=false` plus downsample/filter flags in `pdf/compress_service.py` are what actually shrink those; don't "simplify" them away.

**Proxy fallback:** `config.PROXIES` holds hardcoded fallback proxies that services can iterate through when the primary proxy fails.

**Default video quality:** `VIDEO_FORMAT_QUALITY = 'best[height<=480]/best[height<=720]/best'`.

**Instagram fallback chain:** Instaloader (anonymous, fast) → Instagrapi with authenticated account rotation → yt-dlp (unauthenticated) → clear error. `instagram_account_manager.py` handles rotation, 180 req/hour rate limiting, session persistence in `instagram_sessions/`, and ban/error health tracking. Inspect via `GET /tools/social/instagram/account-stats`.

**System binaries:** `ffmpeg`, `gs` (Ghostscript), and `deno` must be installed on the host — `pip install` does not provide them. See the table in [README.md](README.md) for install commands and the binaries planned tools will add.
