"""Authentication utilities for PC Dashboard."""

from datetime import datetime, timedelta, timezone

from fastapi import HTTPException, status, WebSocket
from jose import JWTError, jwt

from config import settings


def create_access_token(data: dict) -> str:
    """Create a JWT access token.

    Args:
        data: Dictionary with claims to encode in the token.

    Returns:
        Encoded JWT token string.
    """
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def verify_token(token: str) -> dict:
    """Verify and decode a JWT token.

    Args:
        token: JWT token string.

    Returns:
        Decoded token payload.

    Raises:
        HTTPException: If token is invalid or expired.
    """
    try:
        payload = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
        return payload
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )


def get_token_from_header(authorization: str) -> str:
    """Extract token from Authorization header.

    Args:
        authorization: Full Authorization header value.

    Returns:
        Token string.

    Raises:
        HTTPException: If header format is invalid.
    """
    parts = authorization.split()
    if len(parts) != 2 or parts[0].lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authorization header format. Use: Bearer <token>",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return parts[1]


def verify_ws_token(token: str) -> dict:
    """Verify token for WebSocket connection.

    Args:
        token: JWT token string.

    Returns:
        Decoded token payload.

    Raises:
        WebSocketException: If token is invalid.
    """
    try:
        payload = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
        return payload
    except JWTError:
        from fastapi import WebSocketException

        raise WebSocketException(code=status.WS_1008_POLICY_VIOLATION)