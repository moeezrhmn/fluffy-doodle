# Entry point of the app
from fastapi import FastAPI
from fastapi.responses import FileResponse, JSONResponse
from apscheduler.schedulers.background import BackgroundScheduler

from app.utils import helper
from app import config as app_config 


# routers imports
from app.routers import user_router, tools_router

app = FastAPI()
app.include_router(user_router.router)
app.include_router(tools_router.router)


# Root path
@app.get('/')
async def root():
    return {'message':'Tools APIs developed by MOEEZ UR REHMAN - [Profile: moeezrehman.dev] '}



scheduler = BackgroundScheduler()
scheduler.add_job(lambda: helper.cleanup_old_files(app_config.DOWNLOAD_DIR, days=1), 'interval', hours=24, replace_existing=True)
scheduler.start()

