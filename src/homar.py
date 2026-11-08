import os
import subprocess
from datetime import datetime
from zoneinfo import ZoneInfo

from dotenv import load_dotenv
from loguru import logger
from pydantic_ai import (
    Agent,
    DeferredToolRequests,
    DeferredToolResults,
    ModelMessage,
    RunContext,
)
from pydantic_ai.capabilities import Capability, HandleDeferredToolCalls
from pydantic_ai.models.openai import (
    OpenAIResponsesModel,
    OpenAIResponsesModelSettings,
)
from pydantic_ai.providers.openai import OpenAIProvider

load_dotenv()
from src.capabilities import get_domain_capabilities
from src.delayed_message_scheduler import get_scheduler
from src.models.schemas import MyDeps, UserType

# Constants
MAX_DELAY_SECONDS = 86400 * 7  # 7 days
HOMAR_MODEL = os.getenv("HOMAR_MODEL", "openai:gpt-5.4-mini")
TIMEZONE = "Europe/Warsaw"


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


HOMAR_INSTRUCTIONS = """
Nazywasz się Homar. Jesteś domowym asystentem na Discordzie. Masz poczucie humoru, ale przede wszystkim jesteś skuteczny.

Jak działasz:
- Wykonuj polecenia od razu, korzystając z narzędzi. Jesteś domyślny - jeśli polecenie da się sensownie zinterpretować, działaj zamiast dopytywać.
- Twoje specjalistyczne możliwości (dom, Todoist, kalendarz, zapasy, obrazy...) są w katalogu poniżej. Gdy polecenie dotyczy którejś z nich, załaduj ją narzędziem `load_capability` i dopiero wtedy działaj. Możesz załadować kilka, jeśli zadanie tego wymaga.
- Zanim odpowiesz, że czegoś nie potrafisz, sprawdź katalog. Jeśli nic nie pasuje, powiedz to wprost w jednym zdaniu.
- Możesz analizować obrazy wysłane przez użytkownika.
- Polecenia "za godzinę"/"o 22:00" realizuj przez zaplanowanie wiadomości do siebie (`send_delayed_message` / `send_scheduled_message`), a gdy wiadomość przyjdzie - po prostu ją wykonaj.

Jak odpowiadasz:
- Krótko i konkretnie, po polsku. Po wykonaniu akcji potwierdź jednym zdaniem, co zrobiłeś.
- Nie kończ odpowiedzi pytaniami w stylu "Czy mogę jeszcze w czymś pomóc?" ani listą propozycji.
- Nigdy nie proponuj ani nie obiecuj czynności, do których nie masz narzędzia (np. sterowania urządzeniem, którego nie widzisz w Home Assistant).
- Propozycję dalszego kroku składaj tylko wyjątkowo: gdy jest bezpośrednio związana z poleceniem, wyraźnie przydatna i na pewno potrafisz ją wykonać.
- Jeśli narzędzie zwróci błąd, powiedz krótko, co się nie udało - nie udawaj sukcesu.
"""

settings = OpenAIResponsesModelSettings(
    openai_reasoning_effort="low",
    openai_reasoning_summary="concise",
)


async def _handle_approvals(
    ctx: RunContext[MyDeps], requests: DeferredToolRequests
) -> DeferredToolResults | None:
    """Ask the user (e.g. via Discord buttons) to approve tool calls without ending the run."""
    if ctx.deps is None or ctx.deps.approval_callback is None:
        return None
    return await ctx.deps.approval_callback(requests)


def _build_model(model_name: str) -> OpenAIResponsesModel | str:
    """Build the OpenAI model with tools revealed as plain tool-list additions.

    With OpenAI's native `additional_tools` reveal, gpt-5.4-mini often doesn't notice the
    tools of a capability it has just loaded and starts calling unrelated tools. Listing the
    revealed tools in `tools` costs a prompt-cache miss but works reliably.
    """
    provider_name, _, name = model_name.partition(":")
    if provider_name not in ("openai", "openai-responses"):
        return model_name
    profile = OpenAIProvider().model_profile(name) or {}
    profile = {**profile, "tool_addition_mode": None, "tool_deferral_mode": None}
    return OpenAIResponsesModel(name, profile=profile)


homar = Agent(
    _build_model(HOMAR_MODEL),
    deps_type=MyDeps,
    output_type=str | DeferredToolRequests,
    instructions=HOMAR_INSTRUCTIONS,
    model_settings=settings,
    retries={"tools": 3},
    capabilities=[HandleDeferredToolCalls(_handle_approvals)],
)


@homar.instructions
def current_context(ctx: RunContext[MyDeps]) -> str:
    now = datetime.now(tz=ZoneInfo(TIMEZONE))
    lines = [f"Teraz jest {now.strftime('%A, %Y-%m-%d %H:%M')} (Europe/Warsaw)."]
    if ctx.deps and ctx.deps.username:
        lines.append(f"Piszesz z użytkownikiem: {ctx.deps.username}.")
    return "\n".join(lines)


# Admin/default users only - guests don't get it.
maintenance = Capability(id="maintenance")


def _run_ssh_command(label: str, command: list[str]) -> tuple[str | None, str | None]:
    try:
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=120,
        )
        if result.returncode != 0:
            return None, f"{label} failed:\n{result.stderr}"
        return result.stdout, None
    except Exception as e:
        return None, f"{label} error: {str(e)}"


@maintenance.tool_plain(requires_approval=True)
def update_marvin() -> str:
    """
    Update Marvin by calling update script on host via SSH.
    """
    ssh_command = [
        "ssh",
        "-i",
        "/app/deploy_key",
        "-o",
        "StrictHostKeyChecking=no",
        "domin@172.17.0.1",
        "/home/domin/update_marvin.sh",
    ]

    stdout, error = _run_ssh_command("remote update_marvin.sh", ssh_command)
    if error:
        return error

    return f"Remote update successful:\n{stdout}"


@homar.tool(retries=2)
async def send_push_notification(ctx: RunContext[MyDeps], message: str) -> str:
    """Send a push notification to the 'powiadomienia' Discord channel.

    Use this tool when the user asks to send a push notification or an alert to the
    notification channel. The message will always be delivered to the channel named
    'powiadomienia'.

    Args:
        ctx: The run context, including usage metadata.
        message: The notification message to send.

    Returns:
        Confirmation that the notification was sent, or an error message.
    """
    deps = ctx.deps

    if not deps or not deps.send_notification_callback:
        return "Error: Cannot send push notification - missing notification context"

    try:
        success = await deps.send_notification_callback(message)
        if success:
            logger.info(f"Push notification sent: {message}")
            return "Push notification sent successfully to #powiadomienia"
        return "Error: Could not find the 'powiadomienia' channel"
    except Exception as e:
        logger.error(f"Error sending push notification: {e}")
        return f"Error sending push notification: {str(e)}"


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


def _capabilities_for(deps: MyDeps) -> list:
    capabilities = get_domain_capabilities(deps.user_type)
    if deps.user_type != UserType.GUEST:
        capabilities.append(maintenance)
    return capabilities


async def run_homar_with_history(
    new_message: str | list, history: list[ModelMessage], deps: MyDeps | None = None
) -> tuple[str | DeferredToolRequests, list[ModelMessage], list[str]]:
    if deps is None:
        deps = MyDeps()
    agent_response = await homar.run(
        new_message,
        message_history=history,
        deps=deps,
        capabilities=_capabilities_for(deps),
    )
    return agent_response.output, agent_response.new_messages(), deps.generated_images


async def run_homar(
    message: str, deps: MyDeps | None = None
) -> str | DeferredToolRequests:
    output, _, _ = await run_homar_with_history(message, [], deps)
    return output


if __name__ == "__main__":
    import asyncio
    import sys

    print(asyncio.run(run_homar(" ".join(sys.argv[1:]) or "Co potrafisz?")))
