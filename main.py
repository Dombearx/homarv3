#!/usr/bin/env python3
"""Simple FastAPI application with health and interact endpoints."""

import asyncio
import time
import uuid
from datetime import datetime

from fastapi import FastAPI, HTTPException

from src.models import InteractRequest, InteractResponse, HealthResponse

# Create FastAPI app
app = FastAPI(
    title="Homarv3 API",
    version="0.1.0",
    description="A simple FastAPI application with health and interact endpoints"
)

# Track app start time for uptime
app_start_time = time.time()

@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint."""
    return HealthResponse(
        status="healthy",
        timestamp=datetime.utcnow(),
        version="0.1.0"
    )

@app.post("/interact", response_model=InteractResponse)
async def interact(request: InteractRequest):
    """
    Process an interaction request with mocked logic.
    
    Simulates processing with a 1-second delay.
    """
    start_time = time.time()
    request_id = str(uuid.uuid4())
    
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
        raise HTTPException(status_code=500, detail=f"Processing failed: {str(e)}")

@app.get("/")
async def root():
    """Root endpoint with basic information."""
    return {
        "message": "Welcome to Homarv3 API",
        "version": "0.1.0",
        "endpoints": {
            "health": "/health",
            "interact": "/interact",
            "docs": "/docs"
        }
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)