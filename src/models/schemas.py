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

# Discord role name → UserType mapping (case-insensitive).
# The first match in priority order (ADMIN > DEFAULT > GUEST) wins.
_DISCORD_ROLE_MAP: dict[str, UserType] = {
    "admin": UserType.ADMIN,
    "guest": UserType.GUEST,
}


def get_user_type_from_discord_roles(role_names: list[str]) -> UserType:
    """Derive a UserType from a Discord member's role names.

    Roles are matched case-insensitively against the known role names.
    ADMIN takes priority over GUEST; members with no matching role get DEFAULT.
    """
    lower_roles = {name.lower() for name in role_names}
    if "admin" in lower_roles:
        return UserType.ADMIN
    if "guest" in lower_roles:
        return UserType.GUEST
    return UserType.DEFAULT


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
