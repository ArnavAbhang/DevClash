"""
core/database.py
~~~~~~~~~~~~~~~~
MongoDB connection lifecycle using Motor + Beanie.
Called from the FastAPI lifespan context manager in main.py.
"""

from beanie import init_beanie
from motor.motor_asyncio import AsyncIOMotorClient

from core.config import settings
from models.task import Task
from models.user import User


async def connect_db() -> None:
    """Open the Motor connection and initialise Beanie document models."""
    client = AsyncIOMotorClient(settings.mongo_uri)
    await init_beanie(
        database=client[settings.mongo_db_name],
        document_models=[User, Task],
    )


async def close_db() -> None:
    """No-op — Motor manages its own connection pool lifecycle."""
    pass
