"""
models/detected_task.py
~~~~~~~~~~~~~~~~~~~~~~~
Database model for AI-detected tasks from voice commands.
"""

from datetime import datetime
from typing import Optional

from beanie import Document
from pydantic import Field


class DetectedTask(Document):
    """AI-detected task from voice commands."""
    
    title: str = Field(..., max_length=200)
    assignee: Optional[str] = Field(None, max_length=100)
    deadline: Optional[str] = Field(None)  # ISO date string
    description: str = Field("", max_length=500)
    priority: str = Field("medium")  # low, medium, high
    status: str = Field("pending")   # pending, in-progress, done
    confidence: float = Field(..., ge=0.0, le=1.0)
    source_text: str = Field(..., max_length=1000)
    user_id: str = Field(...)  # User who was in the meeting
    meeting_id: Optional[str] = Field(None)  # Optional meeting identifier
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    
    class Settings:
        name = "detected_tasks"
        indexes = [
            "user_id",
            "status",
            "assignee",
            "created_at",
            [("user_id", 1), ("status", 1)],
            [("assignee", 1), ("status", 1)],
        ]
    
    def to_dict(self) -> dict:
        """Convert to dictionary for API responses."""
        return {
            "id": str(self.id),
            "title": self.title,
            "assignee": self.assignee,
            "deadline": self.deadline,
            "description": self.description,
            "priority": self.priority,
            "status": self.status,
            "confidence": self.confidence,
            "source_text": self.source_text,
            "user_id": self.user_id,
            "meeting_id": self.meeting_id,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }