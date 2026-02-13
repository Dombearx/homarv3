import os
from pydantic_ai import Agent, RunContext
from pydantic_ai.mcp import MCPServerStreamableHTTP, MCPServerSSE
import httpx
import asyncio
import time
from dotenv import load_dotenv
from pydantic_ai import Agent, ModelMessage, ModelResponse, TextPart
from pydantic_ai.models.function import AgentInfo, FunctionModel
from pydantic_ai.models.openai import OpenAIResponsesModel, OpenAIResponsesModelSettings
from loguru import logger

load_dotenv()
from src.agents_as_tools.todoist_agent import todoist_agent
from src.agents_as_tools.home_assistant_agent import home_assistant_agent
from src.agents_as_tools.image_generation_agent import image_generation_agent
from src.delayed_message_scheduler import get_scheduler
from src.models.schemas import MyDeps

# Constants
MAX_DELAY_SECONDS = 86400 * 7  # 7 days


def _format_delay_seconds(seconds: int) -> str:
    """Convert seconds to human-readable time format."""
    if seconds < 60:
        return f"{seconds} seconds"
    elif seconds < 3600:
        return f"{seconds // 60} minutes"
    else:
        hours = seconds // 3600
        minutes = (seconds % 3600) // 60
        if minutes:
            return f"{hours} hours and {minutes} minutes"
        else:
            return f"{hours} hours"


settings = OpenAIResponsesModelSettings(
    openai_reasoning_effort="low",
    openai_reasoning_summary="concise",
)

homar = Agent(
    "openai:gpt-5-mini",
    deps_type=MyDeps,
    instructions="Nazywasz się Homar. Jesteś domowym asystentem. Wykonuj polecenia użytkownika korzystając z swojej wiedzy i dostępnych narzędzi. Odpowiadaj krótko i zwięźle, nie oferuj dodatkowej pomocy i proponuj kolejnych działań. Jesteś dokładny i masz poczucie humoru. Jesteś domyślny, potrafisz zrozumieć polecenie nawet jeżeli nie było do końca sprecyzowane. Korzystaj z swojej wiedzy. Najczęściej będziesz musiał wykorzystać narzędzia do wykonania polecenia.",
    model_settings=settings,
)


@homar.tool
async def todoist_api(ctx: RunContext[MyDeps], command: str) -> str:
    """Use this tool to interact with the Todoist API - todos, shopping list, tasks, things to remember, etc.

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
async def home_assistant_api(ctx: RunContext[MyDeps], command: str) -> str:
    """Use this tool to interact with the Home Assistant API - check status and control devices such as: lights, pc.

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


@homar.tool
async def image_generation_api(ctx: RunContext[MyDeps], description: str) -> str:
    """Use this tool to generate images.

    Args:
        ctx: The run context, including usage metadata.
        description: The simple natural language description of image that should contains all imporant details.

    Returns:
        The filepath of the generted image.
    """
    r = await image_generation_agent.run(
        description,
        usage=ctx.usage,
    )
    return r.output


@homar.tool
async def grocy_api(ctx: RunContext[MyDeps], command: str) -> str:
    """Use this tool to interact with the Grocy API - home groceries management. Allows to add products, check stock, consume stock, open stock, etc.
    Use whenever user informs about groceries - added to fridge, opened, consumed, etc.

    Args:
        ctx: The run context, including usage metadata.
        command: The natural language command to execute.

    Returns:
        The response from the Grocy API as a string.
    """
    from src.agents_as_tools.grocy_agent import grocy_agent

    r = await grocy_agent.run(
        command,
        usage=ctx.usage,
    )
    return r.output


@homar.tool_plain
def calculate_sum(a: int, b: int) -> int:
    """Use this tool to calculate the sum of two integers."""
    return a + b


@homar.tool
async def send_delayed_message(
    ctx: RunContext[MyDeps], 
    message: str, 
    delay_seconds: int
) -> str:
    """Schedule a message to be sent to yourself in this thread after a specified delay.
    
    Use this tool when the user asks you to perform an action after a certain amount of time.
    For example: "turn off the light in 1 hour" or "remind me in 30 minutes".
    
    The message will be sent back to you in the same Discord thread after the delay,
    and you will be able to execute the command at that time.
    
    Args:
        ctx: The run context with thread information
        message: The message/command to send to yourself after the delay
        delay_seconds: How many seconds to wait before sending the message
    
    Returns:
        Confirmation that the message has been scheduled
    """
    deps = ctx.deps
    
    # Validate that we have the required context
    if not deps or not deps.thread_id or not deps.send_message_callback:
        return "Error: Cannot schedule delayed message - missing thread context"
    
    # Validate delay
    if delay_seconds < 1:
        return "Error: Delay must be at least 1 second"
    
    if delay_seconds > MAX_DELAY_SECONDS:
        return f"Error: Maximum delay is 7 days ({MAX_DELAY_SECONDS} seconds)"
    
    # Schedule the message
    scheduler = get_scheduler()
    
    # Create a special marker to identify this as a delayed message from the bot
    marked_message = f"[DELAYED_COMMAND] {message}"
    
    try:
        message_id = await scheduler.schedule_message(
            message=marked_message,
            thread_id=deps.thread_id,
            delay_seconds=delay_seconds,
            send_callback=deps.send_message_callback
        )
        
        time_str = _format_delay_seconds(delay_seconds)
        
        logger.info(f"Scheduled delayed message {message_id} for {time_str}")
        return f"Scheduled to send '{message}' in {time_str}"
        
    except Exception as e:
        logger.error(f"Error scheduling delayed message: {e}")
        return f"Error scheduling message: {str(e)}"


async def run_homar_with_messages(messages: list[ModelMessage], deps: MyDeps = None) -> str:
    if deps is None:
        deps = MyDeps()
    agent_response = await homar.run(messages, deps=deps)
    return agent_response.output, agent_response.new_messages()


async def run_homar(message: str, channel: str = None, deps: MyDeps = None) -> str:
    if deps is None:
        deps = MyDeps()
    agent_response = await homar.run(message, deps=deps)
    return agent_response.output


async def run_homar_with_history(
    new_message: str, history: list[ModelMessage], deps: MyDeps = None
) -> tuple[str, list[ModelMessage]]:
    if deps is None:
        deps = MyDeps()
    agent_response = await homar.run(new_message, message_history=history, deps=deps)
    return agent_response.output, agent_response.new_messages()


def print_schema(messages: list[ModelMessage], info: AgentInfo) -> ModelResponse:
    tool = info.function_tools[2]
    print(tool.description)
    print(tool.parameters_json_schema)
    return ModelResponse(parts=[TextPart("calculate_sum")])


if __name__ == "__main__":
    homar.run_sync("hello", model=FunctionModel(print_schema))
