from pydantic_ai.mcp import MCPServerSSE
from pydantic_ai import Agent, RunContext
import os
from pydantic_ai.models.openai import OpenAIResponsesModelSettings
 

home_assistant_mcp_server = MCPServerSSE(
    "http://192.168.50.30:8123/mcp_server/sse",
    headers={"Authorization": f"Bearer {os.getenv('HOME_ASSISTANT_TOKEN')}"},
)

HOME_ASSISTANT_AGENT_PROMPT = """
You are an interface to the Home Assistant API.
"""
settings = OpenAIResponsesModelSettings(
    openai_reasoning_effort='minimal',
    openai_reasoning_summary='concise',
)
    
home_assistant_agent = Agent(
    "openai:gpt-5-mini",
    toolsets=[home_assistant_mcp_server],
    instructions=HOME_ASSISTANT_AGENT_PROMPT,
    model_settings=settings,
)

@home_assistant_agent.system_prompt
async def add_devices_info(ctx: RunContext) -> str:
    tools = await home_assistant_mcp_server.list_tools()
    get_live_context_tool = next((t for t in tools if "getlivecontext" in getattr(t, 'name').lower()), None)
    if not get_live_context_tool:
        print("GetLiveContext tool not found")
        return ""
    tool_name = getattr(get_live_context_tool, 'name')
    result = await home_assistant_mcp_server.call_tool(tool_name, {}, None, get_live_context_tool)
    return result.get("result", "")