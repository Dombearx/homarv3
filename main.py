#!/usr/bin/env python3
"""Simple FastAPI application with health and interact endpoints."""

import uuid
from datetime import datetime, timezone
import time

from fastapi import FastAPI, HTTPException, Depends
import logfire
from dotenv import load_dotenv
from loguru import logger

load_dotenv()
# logfire.install_auto_tracing(modules=['src'], min_duration=0)

from src.models import InteractRequest, HealthResponse
from src.models.schemas import ChatResponse, Message, Role
from src.homar import run_homar, run_homar_with_history, run_homar_with_messages
from src.database_json import db_json as database_pi


# Create FastAPI app
app = FastAPI(
    title="Homarv3 API",
    version="0.1.0",
    description="A simple FastAPI application with health and interact endpoints",
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
        status="healthy", timestamp=datetime.utcnow(), version="0.1.0"
    )


@app.post("/interact", response_model=Message)
async def interact(request: InteractRequest):
    """
    Process an interaction request using the Homar AI agent.
    """
    request_id = str(uuid.uuid4())

    try:
        # Generate response using the AI agent
        current_chat = database_pi.get_chat(request.chat_id)
        current_chat_messages = current_chat.messages if current_chat else []
        logger.debug(f"Current chat messages: {current_chat_messages}")
        response_message, new_messages = await run_homar_with_history(new_message=request.message.content, history=current_chat_messages)
        for message in new_messages:
            database_pi.add_message(request.chat_id, message)

        return Message(
            timestamp=datetime.now(timezone.utc),
            message_id=str(uuid.uuid4()),
            chat_id=request.chat_id,
            content=response_message,
            role=Role.ASSISTANT,
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/chats", response_model=ChatResponse)
async def get_chats():
    return database_pi.get_chats()


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8070, reload=True)
