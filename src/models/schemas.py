"""Pydantic models for Homarv3 API."""

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum, auto
from typing import Any

from pydantic import BaseModel, Field
from pydantic_ai import ModelMessage


class Role(StrEnum):
    """Role model."""

    USER = auto()
    ASSISTANT = auto()


class UserType(StrEnum):
    """User permission type."""

    ADMIN = auto()
    DEFAULT = auto()
    GUEST = auto()


# Tools accessible to Guest users (restricted accounts)
GUEST_ALLOWED_TOOLS: set[str] = {"home_assistant_api"}

# Registry mapping Discord usernames to user types.
# Unknown users fall back to DEFAULT.
USER_REGISTRY: dict[str, UserType] = {}


def get_user_type(username: str) -> UserType:
    """Return the UserType for a Discord username, defaulting to DEFAULT."""
    return USER_REGISTRY.get(username, UserType.DEFAULT)


class InteractRequest(BaseModel):
    """Request model for interact endpoint."""

    message: str = Field(..., description="Message to process")
    user_id: str | None = Field(None, description="Optional user identifier")


class HealthResponse(BaseModel):
    """Response model for health endpoint."""

    status: str = Field(..., description="Service status")
    timestamp: datetime = Field(..., description="Current timestamp")
    version: str = Field(..., description="Application version")


@dataclass
class MyDeps:
    """Dependencies for agents."""

    mode: str = "standard"
    thread_id: int | None = None
    send_message_callback: Any | None = None
    generated_images: list[str] | None = (
        None  # List of image file paths generated during run
    )
    username: str | None = None
    user_type: UserType = UserType.DEFAULT

    def __post_init__(self):
        if self.generated_images is None:
            self.generated_images = []
