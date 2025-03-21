# API route grouping

from fastapi import APIRouter
from app.controllers import file_controller
from app.controllers.tools import social_controller 
from app.controllers import temp_mail_controller

router = APIRouter()
router.include_router(file_controller.router)
router.include_router(social_controller.router)
router.include_router(temp_mail_controller.router)
