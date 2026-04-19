"""
core/dependencies.py
~~~~~~~~~~~~~~~~~~~~
FastAPI dependency functions.

get_current_user() is the equivalent of the Express `protect` middleware:
it extracts the Bearer token, verifies it, fetches the user from MongoDB,
and injects the User document into the route handler.
"""

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from beanie import PydanticObjectId

from models.user import User
from services.jwt import decode_access_token

_bearer = HTTPBearer(auto_error=True)


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(_bearer),
) -> User:
    """
    Verify the JWT in the Authorization header and return the User document.

    Raises:
        HTTPException 401 — missing / invalid / expired token
        HTTPException 401 — user no longer exists in the database
    """
    token = credentials.credentials
    user_id_str = decode_access_token(token)   # raises 401 on bad token
    
    try:
        user_id = PydanticObjectId(user_id_str)
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid user ID in token",
        )

    user = await User.get(user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authorized, user not found",
        )
    return user
