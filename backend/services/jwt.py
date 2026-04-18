"""
jwt.py
~~~~~~
JWT token generation and verification.
Direct port of Node.js utils/jwt.js.

Uses python-jose with HS256 algorithm (same as jsonwebtoken default).
"""

from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import HTTPException, status
from jose import JWTError, jwt

from core.config import settings

_ALGORITHM = "HS256"


def create_access_token(user_id: str) -> str:
    """
    Generate a signed JWT for *user_id*.

    Expiry is controlled by JWT_EXPIRES_IN (e.g. "7d", "24h", "3600").
    Defaults to 7 days if not set.
    """
    expire = datetime.now(timezone.utc) + _parse_expiry(settings.jwt_expires_in)
    payload = {"sub": user_id, "exp": expire}
    return jwt.encode(payload, settings.jwt_secret, algorithm=_ALGORITHM)


def decode_access_token(token: str) -> str:
    """
    Verify *token* and return the user_id (sub claim).

    Raises:
        HTTPException 401 — token invalid or expired
    """
    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=[_ALGORITHM])
        user_id: Optional[str] = payload.get("sub")
        if user_id is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token",
            )
        return user_id
    except JWTError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token invalid or expired",
        ) from exc


# ── Internal helpers ──────────────────────────────────────────────────────────

def _parse_expiry(value: str) -> timedelta:
    """
    Parse a human-readable expiry string into a timedelta.

    Supported suffixes: d (days), h (hours), m (minutes), s / plain int (seconds).
    Examples: "7d", "24h", "3600", "30m"
    """
    value = value.strip()
    if value.endswith("d"):
        return timedelta(days=int(value[:-1]))
    if value.endswith("h"):
        return timedelta(hours=int(value[:-1]))
    if value.endswith("m"):
        return timedelta(minutes=int(value[:-1]))
    # seconds or plain integer
    return timedelta(seconds=int(value.rstrip("s")))
