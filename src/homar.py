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
from src.models.schemas import MyDeps, UserType, GUEST_ALLOWED_TOOLS
from src.memory import get_memory_manager

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


def _check_tool_access(ctx: RunContext[MyDeps], tool_name: str) -> str | None:
    """Return an error string if the user lacks access to *tool_name*, else None."""
    if (
        ctx.deps is not None
        and ctx.deps.user_type == UserType.GUEST
        and tool_name not in GUEST_ALLOWED_TOOLS
    ):
        username = ctx.deps.username or "unknown"
        return f"Access denied: user '{username}' (guest) is not allowed to use the '{tool_name}' tool."
    return None


settings = OpenAIResponsesModelSettings(
    openai_reasoning_effort="low",
    openai_reasoning_summary="concise",
)

homar = Agent(
    "openai:gpt-5-mini",
    deps_type=MyDeps,
    output_type=str | DeferredToolRequests,
    instructions="Nazywasz się Homar. Jesteś domowym asystentem. Wykonuj polecenia użytkownika korzystając z swojej wiedzy i dostępnych narzędzi. Odpowiadaj krótko i zwięźle, nie oferuj dodatkowej pomocy i proponuj kolejnych działań. Jesteś dokładny i masz poczucie humoru. Jesteś domyślny, potrafisz zrozumieć polecenie nawet jeżeli nie było do końca sprecyzowane. Korzystaj z swojej wiedzy. Najczęściej będziesz musiał wykorzystać narzędzia do wykonania polecenia. Możesz również analizować obrazy, które użytkownik wysyła.\n\nMAMY SYSTEM: Możesz zapamiętywać ważne informacje używając narzędzi pamięci. Zapamiętuj TYLKO naprawdę ważne fakty i preferencje użytkowników - NIE zapamiętuj poleceń, pytań ani tymczasowego kontekstu. Używaj remember_user_memory dla osobistych preferencji użytkownika, a remember_global_memory (tylko dla adminów) dla ogólnych procedur systemowych.",
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
        if error := _check_tool_access(ctx, "todoist_api"):
            return error
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
        if error := _check_tool_access(ctx, "image_generation_api"):
            return error
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
        if error := _check_tool_access(ctx, "grocy_api"):
            return error
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
        if error := _check_tool_access(ctx, "google_calendar_api"):
            return error
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
        if error := _check_tool_access(ctx, "humblebundle_api"):
            return error
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


def _format_memory_result(result: dict | str) -> str:
    """
    Extract memory text from a result object.
    
    Args:
        result: Memory result from mem0 (can be dict or string)
    
    Returns:
        Formatted memory text string
    """
    if isinstance(result, dict):
        return result.get("memory", result.get("text", str(result)))
    return str(result)


@homar.tool(retries=2)
async def remember_user_memory(
    ctx: RunContext[MyDeps], user_preference: str
) -> str:
    """Store important USER-SPECIFIC preferences or information in memory.

    Use this tool ONLY when the user explicitly shares PERSONAL preferences, 
    facts about themselves, or information specific to them that should be remembered.
    This memory is user-specific and will NOT be shared with other users.
    
    Examples of user-specific memories:
    - "I'm allergic to peanuts" (user's personal health info)
    - "I prefer to wake up at 6 AM" (user's personal preference)
    - "My favorite color is blue" (user's personal taste)
    - "I live in Tokyo" (user's personal information)
    
    Do NOT remember:
    - Commands or requests (e.g., "turn on the light")
    - Questions (e.g., "what's the weather?")
    - System-wide information (use remember_global_memory for that)
    - Temporary context from current conversation
    - Information that applies to everyone

    Args:
        user_preference: The important user-specific preference or information to remember

    Returns:
        Confirmation that the preference has been stored
    """
    # Check tool access
    access_error = _check_tool_access(ctx, "remember_user_memory")
    if access_error:
        return access_error
    
    try:
        # Use Discord username as user_id
        user_id = ctx.deps.username if ctx.deps.username else "default_user"
        
        memory_manager = get_memory_manager()
        result = memory_manager.add_user_memory(
            content=user_preference,
            user_id=user_id,
            metadata={"source": "homar_agent"}
        )
        
        if "error" in result:
            logger.error(f"Error storing user memory: {result['error']}")
            return f"Failed to remember: {result['error']}"
        
        logger.info(f"Stored user memory for {user_id}: {user_preference}")
        return f"Remembered (personal): {user_preference}"
    
    except Exception as e:
        logger.error(f"Error in remember_user_memory tool: {e}")
        return f"Failed to remember preference: {str(e)}"


@homar.tool(retries=2)
async def remember_global_memory(
    ctx: RunContext[MyDeps], system_information: str
) -> str:
    """Store important SYSTEM-WIDE information in global memory.

    Use this tool for information that applies to ALL users, not specific individuals.
    This includes behavioral guidelines, procedures, general facts, or system-level knowledge.
    
    Examples of global memories:
    - "Always check user consent before making purchases"
    - "To reset the alarm system, press the * key three times"
    - "The backup server address is backup.example.com"
    - "Preferred time zone for appointments is Europe/Warsaw"
    
    Do NOT use for:
    - User-specific preferences (use remember_user_memory instead)
    - Temporary information
    - Commands or requests
    
    Args:
        system_information: The important system-wide information to remember

    Returns:
        Confirmation that the information has been stored
    """
    # Only admins can modify global memory
    if ctx.deps.user_type != UserType.ADMIN:
        username = ctx.deps.username or "unknown"
        return f"Access denied: user '{username}' is not an admin. Only admins can add global memories."
    
    try:
        memory_manager = get_memory_manager()
        result = memory_manager.add_global_memory(
            content=system_information,
            metadata={"source": "homar_agent", "added_by": ctx.deps.username}
        )
        
        if "error" in result:
            logger.error(f"Error storing global memory: {result['error']}")
            return f"Failed to remember: {result['error']}"
        
        logger.info(f"Stored global memory: {system_information}")
        return f"Remembered (global): {system_information}"
    
    except Exception as e:
        logger.error(f"Error in remember_global_memory tool: {e}")
        return f"Failed to remember information: {str(e)}"


@homar.tool(retries=2)
async def recall_user_memory(
    ctx: RunContext[MyDeps], query: str
) -> str:
    """Retrieve previously stored USER-SPECIFIC preferences and information from memory.

    Use this tool to recall personal preferences or information specific to the current user.
    This helps provide personalized responses based on what this particular user has shared.
    
    Use this tool when:
    - Making personalized recommendations
    - Checking if user information is already stored
    - User asks about their personal preferences
    - Customizing responses based on user history
    
    Args:
        query: Search query to find specific memories (required)

    Returns:
        Relevant user-specific preferences and information from memory
    """
    # Check tool access
    access_error = _check_tool_access(ctx, "recall_user_memory")
    if access_error:
        return access_error
    
    try:
        # Use Discord username as user_id
        user_id = ctx.deps.username if ctx.deps.username else "default_user"
        
        memory_manager = get_memory_manager()
        
        # Search for specific memories
        results = memory_manager.search_user_memories(
            query=query,
            user_id=user_id,
            limit=5
        )
        
        if not results:
            return f"No personal memories found for query: {query}"
        
        # Format the results
        memory_list = [
            f"{idx}. {_format_memory_result(result)}"
            for idx, result in enumerate(results, 1)
        ]
        
        memories_str = "\n".join(memory_list)
        logger.info(f"Retrieved {len(results)} user memories for {user_id}")
        return f"Personal memories:\n{memories_str}"
    
    except Exception as e:
        logger.error(f"Error in recall_user_memory tool: {e}")
        return f"Failed to recall memories: {str(e)}"


@homar.tool(retries=2)
async def recall_global_memory(
    ctx: RunContext[MyDeps], query: str
) -> str:
    """Retrieve previously stored SYSTEM-WIDE information from global memory.

    Use this tool to recall general procedures, behavioral guidelines, or 
    system-level information that applies to all users.
    
    Use this tool when:
    - Looking for system procedures or guidelines
    - Checking general facts or configurations
    - Finding information that's not user-specific
    
    Args:
        query: Search query to find specific memories (required)

    Returns:
        Relevant system-wide information from memory
    """
    # Check tool access
    access_error = _check_tool_access(ctx, "recall_global_memory")
    if access_error:
        return access_error
    
    try:
        memory_manager = get_memory_manager()
        
        # Search for global memories
        results = memory_manager.search_global_memories(
            query=query,
            limit=5
        )
        
        if not results:
            return f"No global memories found for query: {query}"
        
        # Format the results
        memory_list = [
            f"{idx}. {_format_memory_result(result)}"
            for idx, result in enumerate(results, 1)
        ]
        
        memories_str = "\n".join(memory_list)
        logger.info(f"Retrieved {len(results)} global memories")
        return f"Global memories:\n{memories_str}"
    
    except Exception as e:
        logger.error(f"Error in recall_global_memory tool: {e}")
        return f"Failed to recall memories: {str(e)}"


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
