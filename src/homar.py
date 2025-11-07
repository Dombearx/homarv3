import os
from pydantic_ai import Agent, RunContext
from pydantic_ai.mcp import MCPServerStreamableHTTP, MCPServerSSE
import httpx
import asyncio
import time
from dotenv import load_dotenv

load_dotenv()
from src.agents_as_tools.todoist_agent import todoist_agent
from src.agents_as_tools.home_assistant_agent import home_assistant_agent

homar = Agent(
    "openai:gpt-5-mini",
    instructions="You are a helpful AI assistant. Provide clear, concise, and accurate responses.",
)


@homar.tool
async def todoist_api(ctx: RunContext[None], command: str) -> str:
    """Use this tool to interact with the Todoist API.

    Args:
        ctx: The run context, including usage metadata.
        command: The natural language command to execute.

    Returns:
        The response from the Todoist API as a string.
    """
    r = await todoist_agent.run(
        command,
        usage=ctx.usage,
    )
    return r.output


@homar.tool
async def home_assistant_api(ctx: RunContext[None], command: str) -> str:
    """Use this tool to interact with the Home Assistant API.

    Args:
        ctx: The run context, including usage metadata.
        command: The natural language command to execute.

    Returns:
        The response from the Home Assistant API as a string.
    """
    r = await home_assistant_agent.run(
        command,
        usage=ctx.usage,
    )
    return r.output


@homar.tool_plain
def calculate_sum(a: int, b: int) -> int:
    """Use this tool to calculate the sum of two integers."""
    return a + b

async def run_homar_with_messages(messages: list[ModelMessage]) -> str:
    agent_response = await homar.run(messages)
    return agent_response.output


async def run_homar(message: str) -> str:
    agent_response = await homar.run(message)
    return agent_response.output


from pydantic_ai import Agent, ModelMessage, ModelResponse, TextPart
from pydantic_ai.models.function import AgentInfo, FunctionModel
def print_schema(messages: list[ModelMessage], info: AgentInfo) -> ModelResponse:
    tool = info.function_tools[2]
    print(tool.description)
    print(tool.parameters_json_schema)
    return ModelResponse(parts=[TextPart('calculate_sum')])

if __name__ == "__main__":
    homar.run_sync("hello", model=FunctionModel(print_schema))
