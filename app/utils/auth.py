from passlib.context import CryptContext
from jose import JWTError, jwt
from fastapi import HTTPException, Depends, status, Header
from fastapi.security import OAuth2PasswordBearer
from datetime import datetime, timedelta
import os
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.user import User

# Print the value to verify it's being read correctly
SECRET_KEY = os.getenv("SECRET_KEY")
ALGORITHM = os.getenv("ALGORITHM")
ACCESS_TOKEN_EXPIRE_MINUTES = float(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "1"))

pwd_context = CryptContext(
    schemes=["bcrypt"],
    deprecated="auto",
    bcrypt__rounds=12,  # You can adjust the rounds for security/performance
    bcrypt__ident="2b"  # Use the modern bcrypt identifier
)

# OAuth2 scheme for token handling
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="users/login")

def hash_password(password: str) -> str:
    """Hash a password using bcrypt."""
    return pwd_context.using(scheme="bcrypt").hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against a hash using bcrypt."""
    return pwd_context.verify(plain_password, hashed_password)

def create_access_token(data: dict, expires_delta: timedelta = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now() + expires_delta
    else:
        expire = datetime.now() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire.timestamp()})  # Store as timestamp
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def decode_access_token(token: str):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except JWTError:
        raise HTTPException(status_code=401, detail="Could not validate credentials")

async def authorize_user(authorization: str = Header(None), db: Session = Depends(get_db)):
    if not authorization or not authorization.startswith('Bearer '):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authorization header"
        )
        
    try:
        token = authorization.split(' ')[1]
        
        # Decode and verify the token
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        
        # Extract username from token
        username = payload.get("sub")
        if username is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token payload"
            )
        # Verify user still exists in database
        user = db.query(User).filter(User.username == username).first()
        if user is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User no longer exists"
            )
            
        # Return both payload and user for route handlers
        return {"token_data": payload, "user": user}
        
    except JWTError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"{str(e)}"
        )