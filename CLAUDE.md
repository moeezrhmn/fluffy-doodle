# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Development Commands

### Running the Application
```bash
# Activate virtual environment
source venv/bin/activate

# Install dependencies
pip install -r requirements.common.txt

# Run development server
uvicorn main:app --reload
```

### Database Management
```bash
# Run database migrations
alembic upgrade head

# Create new migration
alembic revision --autogenerate -m "migration description"
```

### Dependencies
```bash
# Update requirements files (uses custom script)
./scripts/update_requirements.sh
```

## Architecture Overview

### Core Structure
- **FastAPI Application**: Main application in `main.py` with timeout middleware
- **Modular Router System**: Routers separated into `app/routers/` (user_router, tools_router)
- **Service Layer**: Business logic organized in `app/services/` with specialized modules:
  - `plagiarism/`: Text similarity detection and analysis
  - `tools/socials/`: Social media platform integrations (Instagram, YouTube, X/Twitter, VK, Facebook)
  - `ai_detection.py`: AI content detection using GoWinston API
  - `temp_mail_service.py`: Temporary email functionality
- **Controller Layer**: API endpoint handlers in `app/controllers/`
- **Repository Pattern**: Database access layer in `app/repositories/`
- **Configuration**: Centralized config management in `app/config.py` with Redis integration

### Key Features
- **Social Media Tools**: Video/content downloading from major platforms using yt-dlp
- **Plagiarism Detection**: Advanced text similarity analysis with preprocessing and crawling capabilities
- **AI Content Detection**: Integration with GoWinston API for AI-generated content identification
- **Temporary Email**: Service for generating and managing temporary email addresses
- **Request Timeout Middleware**: Configurable timeout handling for all requests

### Environment Configuration
- Uses `.env` file for configuration
- Redis for caching and session management
- PostgreSQL database with Alembic migrations
- Multiple proxy configurations for external requests
- API keys for various third-party services (Google Search, HuggingFace, GoWinston, RapidAPI)

### Dependencies Structure
- `requirements.common.txt`: Shared dependencies for all environments
- `requirements.dev.txt`: Development-specific packages
- `requirements.prod.txt`: Production-specific packages
- Custom script `scripts/update_requirements.sh` manages requirement file separation

### Social Media Integration
- Cookie-based authentication for platforms (X_cookies.txt, yt_cookies.txt)
- Video quality settings and download limits configured in `app/config.py`
- Multiple proxy fallback system for reliable external requests