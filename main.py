#!/usr/bin/env python3
"""Simple FastAPI application with health and interact endpoints."""

import uuid
from datetime import datetime
import time

from fastapi import FastAPI, HTTPException
import logfire
from dotenv import load_dotenv

from src.models import InteractRequest, InteractResponse, HealthResponse
from src.agent import generate_response

load_dotenv()

# Create FastAPI app
app = FastAPI(
    title="Homarv3 API",
    version="0.1.0",
    description="A simple FastAPI application with health and interact endpoints"
)

logfire.configure()
logfire.instrument_fastapi(app)

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
    request_id = str(uuid.uuid4())
    
    try:
        return await generate_response(request, request_id)
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

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