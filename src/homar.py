"""
Simple AI Agent using PydanticAI
"""

import os
from pydantic_ai import Agent
from pydantic_ai.mcp import MCPServerStreamableHTTP, MCPServerSSE
import httpx
import asyncio
import time

todoist_mcp_server = MCPServerStreamableHTTP(
    "https://ai.todoist.net/mcp",
    headers={"Authorization": f"Bearer {os.getenv('TODOIST_TOKEN')}"}
)

home_assistant_mcp_server = MCPServerSSE(
    "http://192.168.50.30:8123/mcp_server/sse",
    headers={"Authorization": f"Bearer {os.getenv('HOME_ASSISTANT_TOKEN')}"}
)

homar = Agent(
    "openai:gpt-5-mini",
    toolsets=[todoist_mcp_server, home_assistant_mcp_server],
    instructions="You are a helpful AI assistant. Provide clear, concise, and accurate responses. If asked to perform smart home action and no specific device is mentioned, use GetLiveContext tool first to determine available devices."
)

@homar.tool_plain
async def calculate_sum(a: int, b: int) -> int:
    return a + b

# TODO Review this concept
@homar.tool_plain
async def get_todoist_tools_additional_description() -> str:
    """Gives additional context for todoist tools"""
    return "When asked to create a subtasks, first create or get parent task"


async def run_homar(message: str) -> str:    
    agent_response = await homar.run(message)
    return agent_response.output

