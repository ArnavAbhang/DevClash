"""
User document model (Beanie ODM → MongoDB).

Mirrors the Mongoose User schema:
  - name        (str, max 50)
  - email       (str, unique, lowercase)
  - password    (str, hashed, excluded from default serialisation)
  - created_at / updated_at  (auto-managed by Beanie)
"""

from datetime import datetime
from typing import Optional

from beanie import Document, Indexed
from pydantic import EmailStr, Field


class User(Document):
    name: str = Field(..., max_length=50)
    email: Indexed(EmailStr, unique=True)  # type: ignore[valid-type]
    # password is stored hashed; excluded from .model_dump() by default via
    # the Settings class below so it is never accidentally serialised.
    password: str = Field(..., exclude=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    class Settings:
        name = "users"
        use_state_management = True

    model_config = {"populate_by_name": True}
