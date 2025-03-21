# Route handlers

from fastapi import APIRouter, Depends, HTTPException, status, Header, Response
from sqlalchemy.orm import Session
from app.database import get_db
from app.schemas.user_schema import UserCreate, UserResponse, UserLogin
from app.utils.auth import verify_password, create_access_token, authorize_user
from app.repositories.user_repository import get_user_by_username, create_user
from app.models.user import User
from typing import Optional

router = APIRouter(prefix="/users", tags=["Users"])


@router.post("/signup")
def signup(user: UserCreate, db: Session = Depends(get_db)):
    try:
        return {'message': 'signup is disabled for now!'}
        # existing_user = get_user_by_username(db, user.username)
        # if existing_user:
        #     raise HTTPException(status_code=400, detail="Username already registered")
        # return create_user(db, user)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/login")
def login(user: UserLogin, db: Session = Depends(get_db)):
    try:
        db_user = get_user_by_username(db, user.username)
        if not db_user or not verify_password(user.password, db_user.hashed_password):
            raise HTTPException(status_code=400, detail="Invalid credentials")

        access_token = create_access_token(data={"sub": db_user.username})
        return {"access_token": access_token, "token_type": "bearer"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/me", response_model=UserResponse)
async def get_current_user_info(auth_data: dict = Depends(authorize_user)):
    return auth_data["user"]



# Example of a protected route that requires authentication
@router.post("/change-password")
async def change_password(
    auth_data: dict = Depends(authorize_user),
    new_password: str = None,
    db: Session = Depends(get_db)
):
    try:
        user = auth_data["user"]
        if new_password:
            # Add password update logic here
            return {"message": "Password updated successfully"}
        raise HTTPException(status_code=400, detail="New password is required")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

