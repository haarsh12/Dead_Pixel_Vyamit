from datetime import datetime, timedelta
from typing import Optional
from jose import jwt, JWTError
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlmodel import Session, select
import os

# 1. Configuration
_DEFAULT_DEV_SECRET = "super-secret-key-change-this-in-prod"
SECRET_KEY = os.getenv("SECRET_KEY", _DEFAULT_DEV_SECRET)
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 * 7  # 7 Days

# Render and other hosts: never use the dev default in production.
if os.getenv("RENDER") and (not os.getenv("SECRET_KEY") or SECRET_KEY == _DEFAULT_DEV_SECRET):
    raise RuntimeError(
        "SECRET_KEY must be set to a long random value in production (Render Dashboard > Environment)."
    )

# 2. Security scheme for Bearer token
security = HTTPBearer()

# 3. Function to Create a Token
def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    """
    Generates a JWT Token.
    data: Dictionary containing user info (e.g., {"sub": "user_id"})
    """
    to_encode = data.copy()
    
    # Set expiration time
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode.update({"exp": expire})
    
    # Encode the token
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

# 4. Function to Verify Token and Get Current User
def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """
    Validates JWT Token and returns the current user.
    This is used as a dependency in protected routes.
    
    Usage in routes:
    @router.get("/protected")
    def protected_route(
        current_user: User = Depends(get_current_user),
        session: Session = Depends(get_session)
    ):
        return {"user_id": current_user.id}
    """
    # Import here to avoid circular imports
    from app.db.models import User
    
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        # Extract token from Bearer credentials
        token = credentials.credentials
        
        # Decode the JWT token
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: str = payload.get("sub")
        
        if user_id is None:
            raise credentials_exception

    except JWTError:
        raise credentials_exception
    
    # Return the user_id - the actual user lookup will happen in the endpoint
    # This is a partial user object that contains just the ID
    class UserStub:
        def __init__(self, user_id: int):
            self.id = user_id
    
    return UserStub(int(user_id))