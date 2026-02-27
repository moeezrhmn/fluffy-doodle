# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Development Commands

### Running the Application
```bash
# Activate virtual environment
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Run development server with auto-reload
uvicorn main:app --reload

# Run production server
gunicorn main:app -w 4 -k uvicorn.workers.UvicornWorker
```

### Testing
```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=app

# Run specific test file
pytest tests/test_example.py

# Run tests with verbose output
pytest -v
```

### Database Management
```bash
# Run database migrations
alembic upgrade head

# Create new migration
alembic revision --autogenerate -m "migration description"

# Rollback one migration
alembic downgrade -1
```

### Production Deployment
```bash
# Systemd service management
sudo systemctl daemon-reload
sudo systemctl start fastapi
sudo systemctl enable fastapi
sudo systemctl status fastapi

# NGINX configuration
sudo nano /etc/nginx/sites-available/fastapi
sudo ln -s /etc/nginx/sites-available/fastapi /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx
```

## Architecture Overview

### Layered Architecture
The application follows a clean layered architecture pattern:
- **Routers** (`app/routers/`): Route definitions and API grouping
  - `user_router.py`: User authentication and management endpoints
  - `tools_router.py`: Aggregates all tool-related controllers
- **Controllers** (`app/controllers/`): HTTP request/response handling and validation
  - `user_controller.py`: User signup, login, and password management endpoints
  - `tools/social_controller.py`: Social media download endpoints
  - `plagiarism_controller.py`: Plagiarism detection endpoints
  - `temp_mail_controller.py`: Temporary email endpoints
  - `file_controller.py`: File management endpoints
- **Services** (`app/services/`): Business logic implementation
- **Repositories** (`app/repositories/`): Database access layer
- **Models** (`app/models/`): SQLAlchemy ORM models
- **Schemas** (`app/schemas/`): Pydantic models for validation

### Core Components

**Main Application** ([main.py:1-56](main.py#L1-L56))
- FastAPI application with custom timeout middleware
- Configurable request timeout (default 120 seconds)
- Returns 504 for timeout errors, 500 for internal errors

**Configuration** ([app/config.py:1-67](app/config.py#L1-L67))
- Centralized settings management via `.env` file
- Redis client configuration for caching
- Proxy configuration with regional support via IP2World
- API keys for external services (Google Search, HuggingFace, GoWinston, RapidAPI)
- Video download settings (quality, size limits, download directory)

**Database** ([app/database.py:1-31](app/database.py#L1-L31))
- PostgreSQL with SQLAlchemy ORM
- Connection pooling via `SessionLocal`
- `get_db()` dependency for request-scoped sessions

**Authentication** ([app/utils/auth.py](app/utils/auth.py))
- JWT-based authentication with HS256 algorithm
- Token expiration configurable via `ACCESS_TOKEN_EXPIRE_MINUTES`
- `authorize_user` dependency for protected endpoints

### Key Features

**Social Media Downloaders** ([app/services/tools/socials/](app/services/tools/socials/))
- **YouTube** (`youtube_service.py`): yt-dlp-based video/audio extraction with proxy support and regional routing
- **Instagram** (`instagram_service.py`): Multi-tiered fallback system with account rotation
  - Primary: Instaloader (fast, anonymous)
  - Secondary: Instagrapi with authenticated account rotation (handles age-restricted)
  - Tertiary: yt-dlp (final fallback)
  - Account Manager (`instagram_account_manager.py`): Manages multiple Instagram accounts with intelligent rotation, rate limiting (180 req/hour), session persistence, and health monitoring
- **Facebook** (`facebook_service.py`): Video extraction
- **X/Twitter** (`x_service.py`): Video downloading with regional proxy support
- **TikTok** (`tiktok_service.py`): TikTok video downloading with regional proxy and SSL bypass
- **VK** (`vk_service.py`): VK platform video downloads
- **Generic** (`yt_dlp_service.py`): Fallback downloader supporting multiple platforms

**Plagiarism Detection** ([app/services/plagiarism/](app/services/plagiarism/))
- Text preprocessing and normalization
- Web crawling for comparison sources via Google Custom Search
- Similarity calculation using sentence transformers and FAISS
- Support for various file formats (PDF, DOCX, TXT)

**AI Content Detection** ([app/services/ai_detection.py](app/services/ai_detection.py))
- Integration with GoWinston API
- Detects AI-generated content

**Temporary Email** ([app/services/temp_mail_service.py](app/services/temp_mail_service.py))
- Generates temporary email addresses
- Redis-backed email session management
- Configurable expiry (default 11 minutes)

### Environment Configuration

**Required Environment Variables:**
- `DATABASE_HOST`, `DATABASE_NAME`, `DATABASE_USERNAME`, `DATABASE_PASSWORD`, `DATABASE_PORT`
- `SECRET_KEY`, `ACCESS_TOKEN_EXPIRE_MINUTES`, `ALGORITHM`
- `REDIS_HOST`, `REDIS_PORT`, `REDIS_DB`
- `REQUEST_TIMEOUT`: Global request timeout in seconds
- `TEMP_MAIL_DOMAIN`, `TEMP_MAIL_USERNAME`, `TEMP_MAIL_PASSWORD`
- `IP2WORLD_USERNAME`, `IP2WORLD_PASSWORD`, `IP2WORLD_HOST`: Proxy credentials
- `GOOGLE_CUSTOM_SEARCH_API_KEY`, `GOOGLE_CUSTOM_SEARCH_ENGINE_ID`
- `HUGGING_FACE_API_KEY`, `GO_WINSTON_AI_API_KEY`, `RAPID_API_KEY`

**Optional Instagram Account Rotation (for age-restricted content):**
- `INSTAGRAM_USERNAME`, `INSTAGRAM_PASSWORD`: Primary account
- `INSTAGRAM_USERNAME_2`, `INSTAGRAM_PASSWORD_2`: Additional account
- `INSTAGRAM_USERNAME_3`, `INSTAGRAM_PASSWORD_3`: Additional account
- Pattern continues: `USERNAME_4`, `USERNAME_5`, etc.
- See [INSTAGRAM_SETUP.md](INSTAGRAM_SETUP.md) for complete setup guide

### Important Implementation Notes

**YouTube Service Regional Proxies and URL Handling:**
- The `youtube_service.py` accepts a `region` parameter to route requests through regional proxies via IP2World
- **IMPORTANT**: YouTube video URLs expire in 5-6 hours and require HTTP headers to access
- The API returns:
  - `video_url`/`download_url`: Direct download URL (requires `http_headers` to access)
  - `http_headers`: Required headers for accessing the URL (User-Agent, Accept, etc.)
  - `webpage_url`: Original YouTube URL (use this to view in browser)
  - `video_id`: YouTube video ID for reference
- **Direct URLs cannot be opened in browser** - they're meant for programmatic download with headers
- To view the video, use the `webpage_url` field instead
- To download, include the `http_headers` when making HTTP requests to the `download_url`

**Download Directory:**
All downloaded media is stored in `downloads/` directory with metadata JSON files.

**Proxy Fallback System:**
`config.py` defines a list of fallback proxies in `PROXIES` array that services can iterate through if primary proxies fail.

**Video Quality Settings:**
Default video quality is configured via `VIDEO_FORMAT_QUALITY` constant: `'best[height<=480]/best[height<=720]/best'`

**Request Timeout Middleware:**
All requests are subject to the timeout defined in `REQUEST_TIMEOUT` environment variable. Long-running operations should be handled asynchronously or have appropriate timeout configuration.

**Instagram Account Rotation System:**
The Instagram service uses a sophisticated account rotation system to handle age-restricted content:
- Automatically rotates through configured accounts
- Session persistence (saves login sessions to `instagram_sessions/`)
- Rate limiting (180 requests/hour per account, auto-resets)
- Health monitoring (tracks bans, errors, quota usage)
- Falls back gracefully if no accounts configured
- Monitor via `GET /tools/social/instagram/account-stats`

**Instagram Fallback Strategy:**
1. Try Instaloader (anonymous, fast) for public content
2. If fails → Try Instagrapi with authenticated rotation
3. If fails → Try yt-dlp (unauthenticated)
4. If all fail → Return clear error message
