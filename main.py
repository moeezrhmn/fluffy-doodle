# Entry point of the app
from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
import asyncio
from asyncio import timeout
import os

from app.utils import helper
from app import config as app_config 


# routers imports
from app.routers import user_router, tools_router

# Get timeout from environment variable (default 30 seconds)
REQUEST_TIMEOUT = int(os.getenv("REQUEST_TIMEOUT", "30"))

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

app = FastAPI()

# Add timeout middleware
app.add_middleware(TimeoutMiddleware)

app.include_router(user_router.router)
app.include_router(tools_router.router)


# Root path
@app.get('/')
async def root():
    return {'message':'Tools APIs developed by MOEEZ UR REHMAN - [Profile: moeezrehman.dev] '}



