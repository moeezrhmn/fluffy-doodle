# Database interactions

from app.models.user import User

def get_user(user_id: int) -> User:
    return User(id=user_id, name="John Doe", email="john@example.com")