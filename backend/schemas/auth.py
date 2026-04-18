"""
Request and response schemas for the /api/auth routes.
Pydantic handles all validation that express-validator did in Node.js.
"""

from pydantic import BaseModel, EmailStr, Field


# ── Request bodies ────────────────────────────────────────────────────────────

class RegisterRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=50, description="Full name")
    email: EmailStr
    password: str = Field(..., min_length=6, description="Min 6 characters")


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=1)


# ── Response shapes ───────────────────────────────────────────────────────────

class UserOut(BaseModel):
    id: str
    name: str
    email: str


class AuthResponse(BaseModel):
    success: bool = True
    message: str
    data: dict  # { user: UserOut, token: str }
