from pydantic_ai.mcp import MCPServerSSE
from pydantic_ai import Agent
import os

home_assistant_mcp_server = MCPServerSSE(
    "http://192.168.50.30:8123/mcp_server/sse",
    headers={"Authorization": f"Bearer {os.getenv('HOME_ASSISTANT_TOKEN')}"},
)

HOME_ASSISTANT_AGENT_PROMPT = """
You are an interface to the Home Assistant API.
Whenever you are asked to perform an action and no specific device is mentioned, use GetLiveContext tool first to determine available devices.
"""

home_assistant_agent = Agent(
    "openai:gpt-5-mini",
    toolsets=[home_assistant_mcp_server],
    instructions=HOME_ASSISTANT_AGENT_PROMPT,
)
