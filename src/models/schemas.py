"""Pydantic models for Homarv3 API."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class InteractRequest(BaseModel):
    """Request model for interact endpoint."""
    message: str = Field(..., min_length=1, max_length=1000, description="Message to process")
    user_id: Optional[str] = Field(None, description="Optional user identifier")


class InteractResponse(BaseModel):
    """Response model for interact endpoint."""
    message: str = Field(..., description="Response message")
    processed_at: datetime = Field(..., description="Processing timestamp")
    request_id: str = Field(..., description="Unique request identifier")
    processing_time: float = Field(..., description="Processing time in seconds")


class HealthResponse(BaseModel):
    """Response model for health endpoint."""
    status: str = Field(..., description="Service status")
    timestamp: datetime = Field(..., description="Current timestamp")
    version: str = Field(..., description="Application version")
