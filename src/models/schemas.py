"""Pydantic models for Homarv3 API."""

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum, auto
from typing import Optional, Any

from pydantic import BaseModel, Field
from pydantic_ai import ModelMessage


class Role(StrEnum):
    """Role model."""

    USER = auto()
    ASSISTANT = auto()


class InteractRequest(BaseModel):
    """Request model for interact endpoint."""

    message: str = Field(..., description="Message to process")
    user_id: Optional[str] = Field(None, description="Optional user identifier")


class HealthResponse(BaseModel):
    """Response model for health endpoint."""

    status: str = Field(..., description="Service status")
    timestamp: datetime = Field(..., description="Current timestamp")
    version: str = Field(..., description="Application version")


@dataclass
class MyDeps:
    """Dependencies for agents."""

    mode: str = "standard"
    thread_id: Optional[int] = None
    send_message_callback: Optional[Any] = None
    generated_images: list[str] = None  # List of image file paths generated during run

    def __post_init__(self):
        if self.generated_images is None:
            self.generated_images = []
