import os
from pydantic_ai import Agent, RunContext, DeferredToolRequests, ModelRetry
from pydantic_ai.mcp import MCPServerStreamableHTTP, MCPServerSSE
import httpx
import asyncio
import time
from datetime import datetime
from zoneinfo import ZoneInfo
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
from src.agents_as_tools.humblebundle_agent import humblebundle_agent
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
    "openai:gpt-4o",
    deps_type=MyDeps,
    output_type=str | DeferredToolRequests,
    instructions="Nazywasz się Homar. Jesteś domowym asystentem. Wykonuj polecenia użytkownika korzystając z swojej wiedzy i dostępnych narzędzi. Odpowiadaj krótko i zwięźle, nie oferuj dodatkowej pomocy i proponuj kolejnych działań. Jesteś dokładny i masz poczucie humoru. Jesteś domyślny, potrafisz zrozumieć polecenie nawet jeżeli nie było do końca sprecyzowane. Korzystaj z swojej wiedzy. Najczęściej będziesz musiał wykorzystać narzędzia do wykonania polecenia. Możesz również analizować obrazy, które użytkownik wysyła.",
    model_settings=settings,
)


@homar.tool(retries=3)
async def todoist_api(ctx: RunContext[MyDeps], command: str) -> str:
    """Use this tool to interact with the Todoist API - todos, shopping list, tasks, things to remember, etc.

    Args:
        ctx: The run context, including usage metadata.
        command: The natural language command to execute.

    Returns:
        The response from the Todoist API as a string.
    """
    try:
        r = await todoist_agent.run(
            command,
            deps=ctx.deps,
            usage=ctx.usage,
        )
        return r.output
    except Exception as e:
        logger.warning(f"Todoist API tool error: {e}")
        raise ModelRetry(
            f"The Todoist API call failed with error: {str(e)}. Please try again with a different approach or rephrase the command."
        )


@homar.tool(retries=3)
async def home_assistant_api(ctx: RunContext[MyDeps], command: str) -> str:
    """Use this tool to interact with the Home Assistant API - check status and control devices such as: lights, pc.

    Args:
        ctx: The run context, including usage metadata.
        command: The natural language command to execute.

    Returns:
        The response from the Home Assistant API as a string.
    """
    try:
        r = await home_assistant_agent.run(
            command,
            deps=ctx.deps,
            usage=ctx.usage,
        )
        return r.output
    except Exception as e:
        logger.warning(f"Home Assistant API tool error: {e}")
        raise ModelRetry(
            f"The Home Assistant API call failed with error: {str(e)}. Please try again with a different approach or be more specific about the device or action."
        )


@homar.tool(retries=3)
async def image_generation_api(ctx: RunContext[MyDeps], description: str) -> str:
    """Use this tool to generate images.

    Args:
        ctx: The run context, including usage metadata.
        description: The simple natural language description of image that should contains all imporant details.

    Returns:
        The filepath of the generated image.
    """
    try:
        from src.agents_as_tools.image_generation_agent import generate_image

        r = await image_generation_agent.run(
            description,
            deps=ctx.deps,
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
    except Exception as e:
        logger.warning(f"Image generation API tool error: {e}")
        raise ModelRetry(
            f"Image generation failed with error: {str(e)}. Please try again with a clearer or more specific description."
        )


@homar.tool(retries=3)
async def grocy_api(ctx: RunContext[MyDeps], command: str) -> str:
    """Use this tool to interact with the Grocy API - home groceries management. Allows to add products, check stock, consume stock, open stock, etc.
    Use whenever user informs about groceries - added to fridge, opened, consumed, etc.

    Args:
        ctx: The run context, including usage metadata.
        command: The natural language command to execute.

    Returns:
        The response from the Grocy API as a string.
    """
    try:
        from src.agents_as_tools.grocy_agent import grocy_agent

        r = await grocy_agent.run(
            command,
            deps=ctx.deps,
            usage=ctx.usage,
        )
        return r.output
    except Exception as e:
        logger.warning(f"Grocy API tool error: {e}")
        raise ModelRetry(
            f"The Grocy API call failed with error: {str(e)}. Please try again with a different approach or be more specific about the product or action."
        )


@homar.tool(retries=3)
async def google_calendar_api(ctx: RunContext[MyDeps], command: str) -> str:
    """Use this tool to interact with Google Calendar - manage events, appointments, meetings, reminders with dates.
    Use whenever user asks about calendar, schedule, events, appointments, or wants to create/check/modify calendar entries.

    Args:
        command: The natural language command to execute.

    Returns:
        The response from the Google Calendar API as a string.
    """
    try:
        r = await google_calendar_agent.run(
            command,
            deps=ctx.deps,
            usage=ctx.usage,
        )
        return r.output
    except Exception as e:
        logger.warning(f"Google Calendar API tool error: {e}")
        raise ModelRetry(
            f"The Google Calendar API call failed with error: {str(e)}. Please try again with a different approach or provide more specific date/time information."
        )


@homar.tool(retries=3)
async def humblebundle_api(ctx: RunContext[MyDeps], command: str) -> str:
    """Use this tool to check HumbleBundle deals and bundles.
    Use when user asks about HumbleBundle, game bundles, book bundles, software bundles, or current deals on HumbleBundle.
    Can list available bundles or get details about specific bundles.

    Args:
        command: The natural language command to execute (e.g., "list all bundles", "show me game bundles", "details about book bundle").

    Returns:
        Information about HumbleBundle bundles as a string.
    """
    try:
        r = await humblebundle_agent.run(
            command,
            deps=ctx.deps,
            usage=ctx.usage,
        )
        return r.output
    except Exception as e:
        logger.warning(f"HumbleBundle API tool error: {e}")
        raise ModelRetry(
            f"The HumbleBundle API call failed with error: {str(e)}. Please try again with a different approach or rephrase your request."
        )


@homar.tool_plain(requires_approval=True)
def approval_test_tool(test_parameter: str) -> str:
    """Test tool for Discord approval mechanism - this tool always requires user confirmation.

    This is a simple test tool to demonstrate the approval workflow. When called,
    it will require the user to approve or reject the action via Discord UI.

    Args:
        test_parameter: A test parameter to demonstrate how parameters are displayed for approval

    Returns:
        A success message if approved
    """
    return f"Test tool executed successfully with parameter: {test_parameter}"


@homar.tool_plain
def calculate_sum(a: int, b: int) -> int:
    """Use this tool to calculate the sum of two integers."""
    return a + b


@homar.tool(retries=2)
async def send_delayed_message(
    ctx: RunContext[MyDeps],
    message: str,
    hours: int = 0,
    minutes: int = 0,
    seconds: int = 0,
) -> str:
    """Schedule a message to be sent to yourself in this thread after a specified delay.

    This is NOT a PydanticAI deferred tool - it completes immediately by scheduling a
    background asyncio task. The actual delay happens in the background, and when the
    time expires, the scheduled message triggers a new agent run in the same thread.

    Use this tool when the user asks you to perform an action after a certain amount of time.
    For example: "turn off the light in 1 hour" or "remind me in 30 minutes".

    Args:
        message: The message/command to send to yourself after the delay
        hours: Number of hours to wait (0 to 168, default 0)
        minutes: Number of minutes to wait (0 to 59, default 0)
        seconds: Number of seconds to wait (0 to 59, default 0)

    Returns:
        Confirmation that the message has been scheduled
    """
    deps = ctx.deps

    # Validate that we have the required context
    if not deps or not deps.thread_id or not deps.send_message_callback:
        return "Error: Cannot schedule delayed message - missing thread context"

    # Validate individual parameters
    if hours < 0 or hours > 168:
        return "Error: Hours must be between 0 and 168"
    if minutes < 0 or minutes > 59:
        return "Error: Minutes must be between 0 and 59"
    if seconds < 0 or seconds > 59:
        return "Error: Seconds must be between 0 and 59"

    # Calculate total delay in seconds
    delay_seconds = hours * 3600 + minutes * 60 + seconds

    # Validate delay
    if delay_seconds < 1:
        return "Error: Delay must be at least 1 second (all time parameters cannot be zero)"

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


@homar.tool(retries=2)
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
                           Times are interpreted in Europe/Warsaw timezone (CET/CEST)

    Returns:
        Confirmation that the message has been scheduled
    """
    deps = ctx.deps

    # Validate that we have the required context
    if not deps or not deps.thread_id or not deps.send_message_callback:
        return "Error: Cannot schedule message - missing thread context"

    # Get the default timezone
    scheduler = get_scheduler()
    tz = ZoneInfo(scheduler.get_default_timezone())

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
                # Parse as naive datetime then make it timezone-aware
                scheduled_time = datetime.strptime(scheduled_datetime, fmt)
                # Make it timezone-aware (interpret as local timezone)
                scheduled_time = scheduled_time.replace(tzinfo=tz)
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
    # Use timezone-aware current time for comparison
    now = datetime.now(tz=tz)
    if scheduled_time <= now:
        return "Error: Scheduled time must be in the future"

    # Calculate delay and check maximum
    delay_seconds = (scheduled_time - now).total_seconds()
    if delay_seconds > MAX_DELAY_SECONDS:
        return f"Error: Maximum delay is 7 days ({MAX_DELAY_SECONDS} seconds)"

    # Create a special marker to identify this as a delayed message from the bot
    marked_message = f"[DELAYED_COMMAND] {message}"

    try:
        message_id = await scheduler.schedule_message_at(
            message=marked_message,
            thread_id=deps.thread_id,
            scheduled_time=scheduled_time,
            send_callback=deps.send_message_callback,
        )

        scheduled_str = scheduled_time.strftime("%Y-%m-%d at %H:%M:%S %Z")

        logger.info(f"Scheduled message {message_id} for {scheduled_str}")
        return f"Scheduled to send '{message}' on {scheduled_str}"

    except Exception as e:
        logger.error(f"Error scheduling message: {e}")
        return f"Error scheduling message: {str(e)}"


@homar.tool(retries=2)
async def list_scheduled_messages(ctx: RunContext[MyDeps]) -> str:
    """List all scheduled messages that are pending delivery.

    Use this tool when the user wants to see what messages/actions are scheduled.
    For example: "what messages are scheduled?" or "show me pending actions".

    Returns:
        A formatted list of all scheduled messages with their IDs, scheduled times, and content
    """
    scheduler = get_scheduler()
    scheduled = scheduler.get_scheduled_messages()

    if not scheduled:
        return "No scheduled messages pending."

    # Get timezone for display
    tz = ZoneInfo(scheduler.get_default_timezone())

    result = []
    result.append(f"Found {len(scheduled)} scheduled message(s):\n")

    for message_id, delayed_msg in scheduled:
        # Format the scheduled time
        scheduled_str = delayed_msg.scheduled_time.strftime("%Y-%m-%d %H:%M:%S %Z")

        # Extract the actual message (removing the DELAYED_COMMAND marker)
        actual_message = delayed_msg.message
        if actual_message.startswith("[DELAYED_COMMAND] "):
            actual_message = actual_message[len("[DELAYED_COMMAND] ") :]

        result.append(f"- ID: {message_id}")
        result.append(f"  Time: {scheduled_str}")
        result.append(f"  Message: {actual_message}")
        result.append("")

    return "\n".join(result)


@homar.tool(retries=2)
async def cancel_scheduled_message(ctx: RunContext[MyDeps], message_id: str) -> str:
    """Cancel a scheduled message that hasn't been sent yet.

    Use this tool when the user wants to cancel a previously scheduled action.
    For example: "cancel scheduled message delayed_1" or "cancel that reminder".

    Args:
        message_id: The ID of the scheduled message to cancel (e.g., "delayed_1" or "scheduled_1")

    Returns:
        Confirmation that the message was cancelled or an error if not found
    """
    scheduler = get_scheduler()

    success = scheduler.cancel_message(message_id)

    if success:
        logger.info(f"Cancelled scheduled message {message_id}")
        return f"Successfully cancelled scheduled message: {message_id}"

    return f"Could not find scheduled message with ID: {message_id}. Use list_scheduled_messages to see available IDs."


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
) -> tuple[str | DeferredToolRequests, list[ModelMessage], list[str]]:
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
