"""
routers/auth.py
~~~~~~~~~~~~~~~
Auth routes — exact API-compatible replacement for the Node.js Express routes:

  POST /api/auth/register  →  register a new account
  POST /api/auth/login     →  authenticate and get a JWT
  GET  /api/auth/me        →  return the current user's profile

Response envelope matches the Node.js format:
  { success: true, message: "...", data: { user: {...}, token: "..." } }
"""

from fastapi import APIRouter, Depends, status

from core.dependencies import get_current_user
from models.user import User
from schemas.auth import LoginRequest, RegisterRequest
from services import auth_service

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/register", status_code=status.HTTP_201_CREATED)
async def register(body: RegisterRequest):
    result = await auth_service.register_user(
        name=body.name,
        email=body.email,
        password=body.password,
    )
    return {
        "success": True,
        "message": "Account created successfully",
        "data": result,
    }


@router.post("/login", status_code=status.HTTP_200_OK)
async def login(body: LoginRequest):
    result = await auth_service.login_user(
        email=body.email,
        password=body.password,
    )
    return {
        "success": True,
        "message": "Login successful",
        "data": result,
    }


@router.get("/me", status_code=status.HTTP_200_OK)
async def get_me(current_user: User = Depends(get_current_user)):
    return {
        "success": True,
        "data": {
            "user": {
                "id": str(current_user.id),
                "name": current_user.name,
                "email": current_user.email,
            }
        },
    }
