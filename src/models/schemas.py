"""Pydantic models for Homarv3 API."""

from datetime import datetime
from enum import StrEnum, auto
from typing import Optional

from pydantic import BaseModel, Field
from pydantic_ai import ModelMessage


class Role(StrEnum):
    """Role model."""

    USER = auto()
    ASSISTANT = auto()

class Message(BaseModel):
    timestamp: datetime = Field(..., description="Timestamp of the message")
    message_id: str = Field(..., description="Unique identifier for the message")
    chat_id: str = Field(..., description="Identifier for the chat")
    content: str = Field(..., description="Content of the message")
    role: Role = Field(..., description="Role of the message sender")
    
class Chat(BaseModel):
    chat_id: str
    messages: list[ModelMessage]


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
