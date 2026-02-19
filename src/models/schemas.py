"""Pydantic models for Homarv3 API."""

import json
import os
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


def _load_user_registry() -> dict[str, UserType]:
    """Load user registry from the HOMAR_USER_REGISTRY environment variable.

    The variable should be a JSON object mapping Discord display_name to a
    user type string ("admin", "default" or "guest"), e.g.:
        HOMAR_USER_REGISTRY={"alice": "admin", "guest_user": "guest"}

    Unknown usernames fall back to DEFAULT at lookup time.
    """
    raw = os.getenv("HOMAR_USER_REGISTRY", "")
    if not raw:
        return {}
    try:
        data = json.loads(raw)
        return {name: UserType(role.lower()) for name, role in data.items()}
    except (json.JSONDecodeError, ValueError) as exc:
        import warnings

        warnings.warn(
            f"HOMAR_USER_REGISTRY could not be parsed and will be ignored: {exc}",
            stacklevel=2,
        )
        return {}


# Registry mapping Discord display_name → UserType, loaded from env at startup.
USER_REGISTRY: dict[str, UserType] = _load_user_registry()


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
