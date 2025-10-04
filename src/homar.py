"""
Simple AI Agent using PydanticAI
"""

import os
from pydantic_ai import Agent
from pydantic_ai.mcp import MCPServerStreamableHTTP
import httpx

todoist_mcp_server = MCPServerStreamableHTTP(
        "https://ai.todoist.net/mcp",
        headers={"Authorization": f"Bearer {os.getenv('TODOIST_TOKEN')}"}
    )

homar = Agent(
    "openai:gpt-4o-mini",
    toolsets=[todoist_mcp_server],
    instructions="You are a helpful AI assistant. Provide clear, concise, and accurate responses."
)

@homar.tool_plain
async def calculate_sum(a: int, b: int) -> int:
    return a + b


async def run_homar(message: str) -> str:
    return (await homar.run(message)).output

