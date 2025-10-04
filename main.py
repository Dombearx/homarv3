#!/usr/bin/env python3
"""Simple FastAPI application with health and interact endpoints."""

import uuid
from datetime import datetime
import time

from fastapi import FastAPI, HTTPException, Depends
import logfire
from dotenv import load_dotenv
from loguru import logger

load_dotenv()
# logfire.install_auto_tracing(modules=['src'], min_duration=0)

from src.models import InteractRequest, InteractResponse, HealthResponse
from src.homar import run_homar


# Create FastAPI app
app = FastAPI(
    title="Homarv3 API",
    version="0.1.0",
    description="A simple FastAPI application with health and interact endpoints"
)

logfire.configure(send_to_logfire=True)
logfire.instrument_fastapi(app)
logfire.instrument_pydantic_ai()
# logfire.instrument_system_metrics()

logger.configure(handlers=[logfire.loguru_handler()])


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
    Process an interaction request using the Homar AI agent.
    
    Uses PydanticAI to generate intelligent responses.
    """
    request_id = str(uuid.uuid4())
    start_time = time.time()
    
    try:
        # Generate response using the AI agent
        ai_response = await run_homar(request.message)
        
        processing_time = time.time() - start_time
        
        return InteractResponse(
            message=ai_response,
            processed_at=datetime.utcnow(),
            request_id=request_id,
            processing_time=processing_time
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)