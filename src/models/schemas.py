"""Pydantic models for Homarv3 API."""

from datetime import datetime
from enum import StrEnum, auto
from typing import Optional

from pydantic import BaseModel, Field


class Role(StrEnum):
    """Role model."""

    USER = auto()
    ASSISTANT = auto()


class Message(BaseModel):
    """Message model."""

    timestamp: datetime
    message_id: str
    chat_id: str
    content: str
    role: Role


class Chat(BaseModel):
    chat_id: str
    last_message_timestamp: datetime
    messages: list[Message]


class ChatResponse(BaseModel):
    chats: list[Chat]


class InteractRequest(BaseModel):
    """Request model for interact endpoint."""

    message: Message = Field(..., description="Message to process")
    chat_id: str = Field(..., description="Chat identifier")
    user_id: Optional[str] = Field(None, description="Optional user identifier")


class HealthResponse(BaseModel):
    """Response model for health endpoint."""

    status: str = Field(..., description="Service status")
    timestamp: datetime = Field(..., description="Current timestamp")
    version: str = Field(..., description="Application version")
