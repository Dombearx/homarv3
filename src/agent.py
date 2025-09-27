"""Agent module for processing interactions and generating responses."""

import asyncio
import time
from datetime import datetime
from typing import Optional

from src.models import InteractRequest, InteractResponse


async def generate_response(request: InteractRequest, request_id: str) -> InteractResponse:
    """
    Generate a response for an interaction request.
    
    Args:
        request: The interaction request containing message and optional user_id
        request_id: Unique identifier for this request
        
    Returns:
        InteractResponse: The generated response with processing details
        
    Raises:
        Exception: If processing fails
    """
    start_time = time.time()
    
    try:
        # Mock processing logic with 1 second sleep
        await asyncio.sleep(1)
        
        # Generate response message
        response_message = f"Processed your message: '{request.message}'"
        if request.user_id:
            response_message += f" (User: {request.user_id})"
        
        processing_time = time.time() - start_time
        
        return InteractResponse(
            message=response_message,
            processed_at=datetime.utcnow(),
            request_id=request_id,
            processing_time=processing_time
        )
        
    except Exception as e:
        raise Exception(f"Processing failed: {str(e)}")
