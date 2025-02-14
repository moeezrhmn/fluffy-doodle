# Business logic

from app.repositories import user_repository

def fetch_user(user_id: int):
    return user_repository.get_user(user_id)