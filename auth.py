"""
JWT Authentication module for AgentZero.
Handles token creation, validation, and route protection.
"""

import os
from datetime import datetime, timedelta
from typing import Optional

from dotenv import load_dotenv
from fastapi import Depends, HTTPException, status, Query
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt
from passlib.context import CryptContext
from pydantic import BaseModel

load_dotenv()

# Configuration from environment
JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "CHANGE-ME-IN-PRODUCTION")
JWT_ALGORITHM = "HS256"
JWT_EXPIRY_HOURS = int(os.getenv("JWT_EXPIRY_HOURS", "24"))

# Admin credentials from environment
ADMIN_USERNAME = os.getenv("ADMIN_USERNAME", "admin")
ADMIN_PASSWORD_HASH = os.getenv("ADMIN_PASSWORD_HASH", "")

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# FastAPI security scheme
security = HTTPBearer()


# --- Models ---

class LoginRequest(BaseModel):
    username: str
    password: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int  # seconds


# --- Helpers ---

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

def hash_password(plain_password: str) -> str:
    """Utility to generate a bcrypt hash. Use this to create ADMIN_PASSWORD_HASH."""
    return pwd_context.hash(plain_password)

def create_access_token(subject: str, expires_delta: Optional[timedelta] = None) -> str:
    expire = datetime.utcnow() + (expires_delta or timedelta(hours=JWT_EXPIRY_HOURS))
    to_encode = {"sub": subject, "exp": expire}
    return jwt.encode(to_encode, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)

def decode_access_token(token: str) -> Optional[str]:
    """Returns the subject (username) if valid, None otherwise."""
    try:
        payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
        return payload.get("sub")
    except JWTError:
        return None


# --- FastAPI Dependencies ---

async def require_auth(credentials: HTTPAuthorizationCredentials = Depends(security)) -> str:
    """
    Dependency for protected routes. Returns the username if token is valid.
    Usage: @app.get("/protected", dependencies=[Depends(require_auth)])
    """
    username = decode_access_token(credentials.credentials)
    if username is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return username

def validate_ws_token(token: str) -> Optional[str]:
    """
    Validates a JWT token for WebSocket connections.
    WebSockets can't use headers easily, so token is passed as a query param.
    Returns username if valid, None otherwise.
    """
    return decode_access_token(token)


# --- Login Logic ---

def authenticate_user(username: str, password: str) -> bool:
    """Validates credentials against env-stored admin user."""
    if not ADMIN_PASSWORD_HASH:
        # No password hash configured — reject all logins
        return False
    if username != ADMIN_USERNAME:
        return False
    return verify_password(password, ADMIN_PASSWORD_HASH)
