"""
auth_service.py
~~~~~~~~~~~~~~~
Business logic for user registration and login.

Password hashing strategy
--------------------------
bcrypt has a hard 72-byte input limit.  Passwords longer than 72 bytes are
silently truncated, meaning two different passwords can produce the same hash.
To prevent this we SHA-256 pre-hash the password before passing it to bcrypt:

    stored_hash = bcrypt.hashpw(sha256(password), bcrypt.gensalt())

This is the approach recommended by the bcrypt library maintainers and is safe
because SHA-256 output is always 32 bytes (well under the 72-byte limit) and
is a one-way function.

Why not passlib?
----------------
passlib 1.7.4 is incompatible with bcrypt ≥ 4.0 (the bcrypt.__about__ module
was removed, breaking passlib's version detection).  This causes passlib to
silently fall back to a pure-Python implementation that either:
  • truncates passwords at 72 bytes without warning, or
  • raises ValueError: password cannot be longer than 72 bytes, or
  • returns False from verify() for valid passwords (the 401 bug).

We call bcrypt directly instead, which is stable and well-maintained.
"""

import hashlib
import hmac

import bcrypt
from fastapi import HTTPException, status

from models.user import User
from services.jwt import create_access_token


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _pre_hash(plain: str) -> bytes:
    """
    SHA-256 pre-hash the password so bcrypt always receives ≤ 32 bytes.

    We use HMAC-SHA256 with an empty key rather than bare SHA-256 so the
    output is domain-separated from other SHA-256 uses in the codebase.
    Using hmac.digest is constant-time, which is a nice bonus.
    """
    return hmac.digest(b"", plain.encode("utf-8"), hashlib.sha256)


def _hash_password(plain: str) -> str:
    """Hash a plaintext password and return the bcrypt hash as a str."""
    pre_hashed = _pre_hash(plain)
    salt = bcrypt.gensalt(rounds=12)
    return bcrypt.hashpw(pre_hashed, salt).decode("utf-8")


def _verify_password(plain: str, hashed: str) -> bool:
    """
    Verify a plaintext password against a stored bcrypt hash.

    Returns False (never raises) so callers can treat any mismatch uniformly.
    """
    try:
        pre_hashed = _pre_hash(plain)
        return bcrypt.checkpw(pre_hashed, hashed.encode("utf-8"))
    except Exception:
        return False


# ---------------------------------------------------------------------------
# Public service functions
# ---------------------------------------------------------------------------

async def register_user(name: str, email: str, password: str) -> dict:
    """
    Create a new user account.

    Raises:
        HTTPException 409 — email already registered
    """
    existing = await User.find_one(User.email == email.lower())
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email already registered",
        )

    hashed = _hash_password(password)
    user = User(name=name, email=email.lower(), password=hashed)
    await user.insert()

    token = create_access_token(str(user.id))
    return {
        "user": {"id": str(user.id), "name": user.name, "email": user.email},
        "token": token,
    }


async def login_user(email: str, password: str) -> dict:
    """
    Authenticate a user and return a JWT token.

    Raises:
        HTTPException 401 — invalid credentials
    """
    user = await User.find_one(User.email == email.lower())

    if not user or not _verify_password(password, user.password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    token = create_access_token(str(user.id))
    return {
        "user": {"id": str(user.id), "name": user.name, "email": user.email},
        "token": token,
    }
