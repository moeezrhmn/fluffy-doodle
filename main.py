# Entry point of the app
from contextlib import asynccontextmanager
from starlette.middleware.base import BaseHTTPMiddleware
from app.routers import user_router, tools_router
from app.services.tools.media import compress_service, audio_service

from fastapi.responses import JSONResponse
from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles

from app.config import settings
from asyncio import timeout
import asyncio
import os
from app import config


REQUEST_TIMEOUT = int(settings.REQUEST_TIMEOUT)

class TimeoutMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        try:
            async with timeout(REQUEST_TIMEOUT):
                response = await call_next(request)
                return response
        except asyncio.TimeoutError:
            return JSONResponse(
                status_code=504,
                content={
                    "error": "Request timeout",
                    "message": f"Request took longer than {REQUEST_TIMEOUT} seconds to process",
                    "timeout": REQUEST_TIMEOUT
                }
            )
        except Exception as e:
            return JSONResponse(
                status_code=500,
                content={
                    "error": "Internal server error",
                    "message": str(e)
                }
            )


@asynccontextmanager
async def lifespan(app: FastAPI):
    compress_service.start_workers()
    audio_service.start_workers()
    yield


app = FastAPI(lifespan=lifespan)

# Add timeout middleware
app.add_middleware(TimeoutMiddleware)

# Mount downloads directory for static file serving
if not os.path.exists(config.DOWNLOAD_DIR):
    os.makedirs(config.DOWNLOAD_DIR)
app.mount("/downloads", StaticFiles(directory=config.DOWNLOAD_DIR), name="downloads")

app.include_router(user_router.router)
app.include_router(tools_router.router)


# Root path
@app.get('/')
async def root():
    return {'message':'Tools APIs developed by MOEEZ UR REHMAN - [Portfolio: moeezrehman.quanter.dev] '}



