"""Authentication utilities for Keystone."""

import warnings
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import Header
from jose import JWTError, jwt
from passlib.context import CryptContext

# Suppress bcrypt version warning
warnings.filterwarnings("ignore", message=".*bcrypt.*", category=UserWarning)

from ...common.config import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash."""
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """Generate password hash."""
    return pwd_context.hash(password)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Create JWT access token."""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(hours=24)

    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.secret_key, algorithm="HS256")
    return encoded_jwt


def verify_token(token: str) -> Optional[dict]:
    """Verify and decode JWT token."""
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=["HS256"])
        return payload
    except JWTError:
        return None


def generate_token_hash(token: str) -> str:
    """Generate hash for token storage."""
    return pwd_context.hash(token)


def get_current_user_info(
    x_auth_token: str = Header(..., alias="X-Auth-Token")
) -> dict:
    """Extract user information from authentication token.

    For the mock implementation, we'll return default values.
    In a real implementation, this would validate the token and extract user info.
    """
    from fastapi import HTTPException, status

    # For mock implementation, we'll validate the token format
    if not x_auth_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication token required",
        )

    # Verify token
    payload = verify_token(x_auth_token)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication token",
        )

    return {
        "user_id": payload.get("sub", "default-user"),
        "username": payload.get("username", "admin"),
        "project_id": payload.get("project_id", "default-project"),
        "domain_id": payload.get("domain_id", "default-domain"),
    }
