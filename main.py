# Entry point of the app
from starlette.middleware.base import BaseHTTPMiddleware
from app.routers import user_router, tools_router

from fastapi.responses import JSONResponse
from fastapi import FastAPI, Request

from app.config import settings
from asyncio import timeout
import asyncio



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

app = FastAPI()

# Add timeout middleware
app.add_middleware(TimeoutMiddleware)

app.include_router(user_router.router)
app.include_router(tools_router.router)


# Root path
@app.get('/')
async def root():
    return {'message':'Tools APIs developed by MOEEZ UR REHMAN - [Profile: moeezrehman.dev] '}



