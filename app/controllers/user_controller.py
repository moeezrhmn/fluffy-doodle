# Route handlers

from fastapi import APIRouter
from app.services import user_service

router = APIRouter()

@router.get("/users/{user_id}")
def get_user(user_id: int):
    return user_service.fetch_user(user_id)