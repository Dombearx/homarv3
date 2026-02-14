import os
from pydantic_ai import Agent, RunContext
from pydantic_ai.mcp import MCPServerStreamableHTTP, MCPServerSSE
import httpx
import asyncio
import time
from datetime import datetime
from dotenv import load_dotenv
from pydantic_ai import Agent, ModelMessage, ModelResponse, TextPart
from pydantic_ai.models.function import AgentInfo, FunctionModel
from pydantic_ai.models.openai import OpenAIResponsesModel, OpenAIResponsesModelSettings
from loguru import logger

load_dotenv()
from src.agents_as_tools.todoist_agent import todoist_agent
from src.agents_as_tools.home_assistant_agent import home_assistant_agent
from src.agents_as_tools.image_generation_agent import image_generation_agent
from src.agents_as_tools.google_calendar_agent import google_calendar_agent
from src.delayed_message_scheduler import get_scheduler
from src.models.schemas import MyDeps

# Constants
MAX_DELAY_SECONDS = 86400 * 7  # 7 days


def _format_delay_seconds(seconds: int) -> str:
    """Convert seconds to human-readable time format."""
    if seconds < 60:
        return f"{seconds} seconds"
    if seconds < 3600:
        return f"{seconds // 60} minutes"

    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    if minutes:
        return f"{hours} hours and {minutes} minutes"
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
        The filepath of the generated image.
    """
    from src.agents_as_tools.image_generation_agent import generate_image

    r = await image_generation_agent.run(
        description,
        usage=ctx.usage,
    )

    # Generate the actual image file
    image_filename = generate_image(r.output, "homar_generated")

    # Store the image filename in deps so it can be sent back
    if ctx.deps:
        from src.agents_as_tools.consts import IMAGE_GENERATION_OUTPUT_DIR

        image_path = IMAGE_GENERATION_OUTPUT_DIR / image_filename
        ctx.deps.generated_images.append(str(image_path))

    return f"Image generated successfully: {image_filename}"


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


@homar.tool
async def google_calendar_api(ctx: RunContext[MyDeps], command: str) -> str:
    """Use this tool to interact with Google Calendar - manage events, appointments, meetings, reminders with dates.
    Use whenever user asks about calendar, schedule, events, appointments, or wants to create/check/modify calendar entries.

    Args:
        command: The natural language command to execute.

    Returns:
        The response from the Google Calendar API as a string.
    """
    r = await google_calendar_agent.run(
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
    ctx: RunContext[MyDeps], message: str, delay_seconds: int
) -> str:
    """Schedule a message to be sent to yourself in this thread after a specified delay.

    This is NOT a PydanticAI deferred tool - it completes immediately by scheduling a
    background asyncio task. The actual delay happens in the background, and when the
    time expires, the scheduled message triggers a new agent run in the same thread.

    Use this tool when the user asks you to perform an action after a certain amount of time.
    For example: "turn off the light in 1 hour" or "remind me in 30 minutes".

    Args:
        message: The message/command to send to yourself after the delay
        delay_seconds: How many seconds to wait before sending the message (1 to 604800)

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
            send_callback=deps.send_message_callback,
        )

        time_str = _format_delay_seconds(delay_seconds)

        logger.info(f"Scheduled delayed message {message_id} for {time_str}")
        return f"Scheduled to send '{message}' in {time_str}"

    except Exception as e:
        logger.error(f"Error scheduling delayed message: {e}")
        return f"Error scheduling message: {str(e)}"


@homar.tool
async def send_scheduled_message(
    ctx: RunContext[MyDeps], message: str, scheduled_datetime: str
) -> str:
    """Schedule a message to be sent to yourself in this thread at a specific date and time.

    This tool completes immediately by scheduling a background asyncio task. The actual
    delay happens in the background, and when the scheduled time arrives, the message
    triggers a new agent run in the same thread.

    Use this tool when the user asks you to perform an action at a specific time or date.
    For example: "turn off the light at 10pm" or "remind me on December 25th at 9am".

    Args:
        message: The message/command to send to yourself at the scheduled time
        scheduled_datetime: ISO 8601 datetime string (e.g., "2024-12-25T09:00:00" or "2024-12-25 09:00:00")
                           Can also be just date "2024-12-25" (will use 00:00:00 time)

    Returns:
        Confirmation that the message has been scheduled
    """
    deps = ctx.deps

    # Validate that we have the required context
    if not deps or not deps.thread_id or not deps.send_message_callback:
        return "Error: Cannot schedule message - missing thread context"

    # Parse the datetime string
    try:
        # Try multiple datetime formats
        scheduled_time = None
        for fmt in [
            "%Y-%m-%dT%H:%M:%S",
            "%Y-%m-%d %H:%M:%S",
            "%Y-%m-%d %H:%M",
            "%Y-%m-%dT%H:%M",
            "%Y-%m-%d",
        ]:
            try:
                scheduled_time = datetime.strptime(scheduled_datetime, fmt)
                break
            except ValueError:
                continue

        if scheduled_time is None:
            return (
                "Error: Invalid datetime format. Please use ISO 8601 format like "
                "'2024-12-25T09:00:00' or '2024-12-25 09:00:00' or just '2024-12-25'"
            )

    except Exception as e:
        return f"Error parsing datetime: {str(e)}"

    # Validate that the time is in the future
    now = datetime.now()
    if scheduled_time <= now:
        return "Error: Scheduled time must be in the future"

    # Calculate delay and check maximum
    delay_seconds = (scheduled_time - now).total_seconds()
    if delay_seconds > MAX_DELAY_SECONDS:
        return f"Error: Maximum delay is 7 days ({MAX_DELAY_SECONDS} seconds)"

    # Schedule the message
    scheduler = get_scheduler()

    # Create a special marker to identify this as a delayed message from the bot
    marked_message = f"[DELAYED_COMMAND] {message}"

    try:
        message_id = await scheduler.schedule_message_at(
            message=marked_message,
            thread_id=deps.thread_id,
            scheduled_time=scheduled_time,
            send_callback=deps.send_message_callback,
        )

        scheduled_str = scheduled_time.strftime("%Y-%m-%d at %H:%M:%S")

        logger.info(f"Scheduled message {message_id} for {scheduled_str}")
        return f"Scheduled to send '{message}' on {scheduled_str}"

    except Exception as e:
        logger.error(f"Error scheduling message: {e}")
        return f"Error scheduling message: {str(e)}"


async def run_homar_with_messages(
    messages: list[ModelMessage], deps: MyDeps = None
) -> str:
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
) -> tuple[str, list[ModelMessage], list[str]]:
    if deps is None:
        deps = MyDeps()
    agent_response = await homar.run(new_message, message_history=history, deps=deps)
    return agent_response.output, agent_response.new_messages(), deps.generated_images


def print_schema(messages: list[ModelMessage], info: AgentInfo) -> ModelResponse:
    tool = info.function_tools[2]
    print(tool.description)
    print(tool.parameters_json_schema)
    return ModelResponse(parts=[TextPart("calculate_sum")])


if __name__ == "__main__":
    homar.run_sync("hello", model=FunctionModel(print_schema))
