"""Unit tests for homar scheduling tools."""

import asyncio
import pytest
import pytest_asyncio
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from src.models.schemas import MyDeps
from src.delayed_message_scheduler import get_scheduler
from src.cyclic_action_scheduler import get_cyclic_scheduler


# Import the tool functions directly to avoid full homar import chain
# We'll test these functions standalone
async def send_delayed_message_test_helper(deps, message, hours, minutes, seconds):
    """Helper function that mimics send_delayed_message behavior."""
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

    MAX_DELAY_SECONDS = 86400 * 7
    if delay_seconds > MAX_DELAY_SECONDS:
        return f"Error: Maximum delay is 7 days ({MAX_DELAY_SECONDS} seconds)"

    # Schedule the message
    scheduler = get_scheduler()
    marked_message = f"[DELAYED_COMMAND] {message}"

    try:
        message_id = await scheduler.schedule_message(
            message=marked_message,
            thread_id=deps.thread_id,
            delay_seconds=delay_seconds,
            send_callback=deps.send_message_callback,
        )
        return f"Scheduled to send '{message}'"
    except Exception as e:
        return f"Error scheduling message: {str(e)}"


async def list_scheduled_messages_test_helper():
    """Helper function that mimics list_scheduled_messages behavior."""
    scheduler = get_scheduler()
    cyclic_scheduler = get_cyclic_scheduler()
    scheduled = scheduler.get_scheduled_messages()
    cyclic_actions = cyclic_scheduler.get_actions()

    if not scheduled and not cyclic_actions:
        return "No scheduled messages or cyclic actions pending."

    result = []

    if scheduled:
        result.append(f"One-time scheduled messages ({len(scheduled)}):\n")
        for message_id, delayed_msg in scheduled:
            scheduled_str = delayed_msg.scheduled_time.strftime("%Y-%m-%d %H:%M:%S %Z")
            actual_message = delayed_msg.message
            if actual_message.startswith("[DELAYED_COMMAND] "):
                actual_message = actual_message[len("[DELAYED_COMMAND] ") :]
            result.append(f"- ID: {message_id}")
            result.append(f"  Time: {scheduled_str}")
            result.append(f"  Message: {actual_message}")
            result.append("")

    if cyclic_actions:
        result.append(f"Cyclic actions ({len(cyclic_actions)}):\n")
        for action_id, action in cyclic_actions:
            runs_info = (
                f"{action.run_count}/{action.max_runs}"
                if action.max_runs
                else str(action.run_count)
            )
            actual_message = action.message
            if actual_message.startswith("[DELAYED_COMMAND] "):
                actual_message = actual_message[len("[DELAYED_COMMAND] ") :]
            result.append(f"- ID: {action_id}")
            result.append(f"  Schedule: {action.schedule_description}")
            result.append(f"  Runs: {runs_info}")
            result.append(f"  Message: {actual_message}")
            result.append("")

    return "\n".join(result)


async def cancel_scheduled_message_test_helper(message_id):
    """Helper function that mimics cancel_scheduled_message behavior."""
    scheduler = get_scheduler()
    if scheduler.cancel_message(message_id):
        return f"Successfully cancelled scheduled message: {message_id}"

    cyclic_scheduler = get_cyclic_scheduler()
    if cyclic_scheduler.cancel_action(message_id):
        return f"Successfully cancelled cyclic action: {message_id}"

    return (
        f"Could not find scheduled message or cyclic action with ID: {message_id}. "
        "Use list_scheduled_messages to see available IDs."
    )


async def schedule_cyclic_action_test_helper(
    deps, message, interval_hours, interval_minutes, interval_seconds, max_runs=None
):
    """Helper function that mimics schedule_cyclic_action behavior."""
    if not deps or not deps.thread_id or not deps.send_message_callback:
        return "Error: Cannot schedule cyclic action - missing thread context"

    if interval_hours < 0 or interval_minutes < 0 or interval_seconds < 0:
        return "Error: Interval values must be non-negative"
    if interval_minutes > 59 or interval_seconds > 59:
        return "Error: Minutes and seconds must be 0-59"

    total_seconds = interval_hours * 3600 + interval_minutes * 60 + interval_seconds
    if total_seconds < 1:
        return "Error: Interval must be at least 1 second"

    if max_runs is not None and max_runs <= 0:
        return "Error: max_runs must be a positive number"

    cyclic_scheduler = get_cyclic_scheduler()
    marked_message = f"[DELAYED_COMMAND] {message}"

    try:
        action_id = await cyclic_scheduler.schedule_interval(
            message=marked_message,
            thread_id=deps.thread_id,
            interval_seconds=total_seconds,
            send_callback=deps.send_message_callback,
            max_runs=max_runs,
        )
        return f"Scheduled '{message}'. ID: {action_id}"
    except Exception as e:
        return f"Error scheduling cyclic action: {str(e)}"


async def schedule_daily_action_test_helper(
    deps, message, time_str, days_interval=1, max_runs=None
):
    """Helper function that mimics schedule_daily_action behavior."""
    if not deps or not deps.thread_id or not deps.send_message_callback:
        return "Error: Cannot schedule daily action - missing thread context"

    if days_interval <= 0:
        return "Error: days_interval must be at least 1"

    if max_runs is not None and max_runs <= 0:
        return "Error: max_runs must be a positive number"

    cyclic_scheduler = get_cyclic_scheduler()
    marked_message = f"[DELAYED_COMMAND] {message}"

    try:
        action_id = await cyclic_scheduler.schedule_at_time(
            message=marked_message,
            thread_id=deps.thread_id,
            time_str=time_str,
            send_callback=deps.send_message_callback,
            days_interval=days_interval,
            max_runs=max_runs,
        )
        freq = "daily" if days_interval == 1 else f"every {days_interval} days"
        return f"Scheduled '{message}' at {time_str} {freq}. ID: {action_id}"
    except ValueError as e:
        return f"Error: {str(e)}"
    except Exception as e:
        return f"Error scheduling daily action: {str(e)}"


async def schedule_random_action_test_helper(
    deps, message, start_hour, end_hour, days_interval=1, max_runs=None
):
    """Helper function that mimics schedule_random_action behavior."""
    if not deps or not deps.thread_id or not deps.send_message_callback:
        return "Error: Cannot schedule random action - missing thread context"

    if not (0 <= start_hour < end_hour <= 24):
        return f"Error: Invalid window: start_hour={start_hour}, end_hour={end_hour}."

    if days_interval <= 0:
        return "Error: days_interval must be at least 1"

    if max_runs is not None and max_runs <= 0:
        return "Error: max_runs must be a positive number"

    cyclic_scheduler = get_cyclic_scheduler()
    marked_message = f"[DELAYED_COMMAND] {message}"

    try:
        action_id = await cyclic_scheduler.schedule_random_window(
            message=marked_message,
            thread_id=deps.thread_id,
            start_hour=start_hour,
            end_hour=end_hour,
            send_callback=deps.send_message_callback,
            days_interval=days_interval,
            max_runs=max_runs,
        )
        return f"Scheduled '{message}'. ID: {action_id}"
    except ValueError as e:
        return f"Error: {str(e)}"
    except Exception as e:
        return f"Error scheduling random action: {str(e)}"


class TestSchedulingTools:
    """Test the scheduling tools in homar."""

    @pytest.fixture
    def mock_callback(self):
        """Create a mock callback that tracks calls."""
        calls = []

        async def callback(message, thread_id):
            calls.append({"message": message, "thread_id": thread_id})

        callback.calls = calls
        return callback

    @pytest.fixture
    def deps(self, mock_callback):
        """Create MyDeps with thread context."""
        return MyDeps(thread_id=12345, send_message_callback=mock_callback)

    @pytest_asyncio.fixture(autouse=True)
    async def clear_scheduler(self):
        """Clear all scheduled messages and cyclic actions before each test."""
        scheduler = get_scheduler()
        cyclic_scheduler = get_cyclic_scheduler()

        # Cancel all existing messages and collect their tasks (BEFORE test)
        tasks_to_wait = []
        messages_before = list(scheduler.get_scheduled_messages())
        for message_id, delayed_msg in messages_before:
            if delayed_msg.task and not delayed_msg.task.done():
                tasks_to_wait.append(delayed_msg.task)
            scheduler.cancel_message(message_id)

        # Cancel all cyclic actions
        for action_id, action in list(cyclic_scheduler.get_actions()):
            if action.task and not action.task.done():
                tasks_to_wait.append(action.task)
            cyclic_scheduler.cancel_action(action_id)

        # Wait for all cancelled tasks to complete
        for task in tasks_to_wait:
            try:
                await task
            except asyncio.CancelledError:
                pass
            except Exception:
                pass

        # Extra wait to ensure cleanup completes
        await asyncio.sleep(0.2)

        # Verify cleanup succeeded
        remaining = scheduler.get_scheduled_messages()
        if remaining:
            # Force cleanup if still messages present
            for message_id, _ in remaining:
                scheduler.cancel_message(message_id)
            await asyncio.sleep(0.1)

        yield

        # Clean up after test
        tasks_to_wait = []
        messages_after = list(scheduler.get_scheduled_messages())
        for message_id, delayed_msg in messages_after:
            if delayed_msg.task and not delayed_msg.task.done():
                tasks_to_wait.append(delayed_msg.task)
            scheduler.cancel_message(message_id)

        for action_id, action in list(cyclic_scheduler.get_actions()):
            if action.task and not action.task.done():
                tasks_to_wait.append(action.task)
            cyclic_scheduler.cancel_action(action_id)

        # Wait for all cancelled tasks to complete
        for task in tasks_to_wait:
            try:
                await task
            except asyncio.CancelledError:
                pass
            except Exception:
                pass

        # Extra wait to ensure cleanup completes
        await asyncio.sleep(0.2)

    @pytest.mark.asyncio
    async def test_list_scheduled_messages_empty(self):
        """Test listing scheduled messages when there are none."""
        result = await list_scheduled_messages_test_helper()
        assert result == "No scheduled messages or cyclic actions pending."

    @pytest.mark.asyncio
    async def test_list_scheduled_messages_with_messages(self, deps, mock_callback):
        """Test listing scheduled messages when there are some."""
        # Schedule messages
        await send_delayed_message_test_helper(deps, "Test message 1", 0, 0, 10)
        await send_delayed_message_test_helper(deps, "Test message 2", 0, 0, 20)

        result = await list_scheduled_messages_test_helper()

        assert "One-time scheduled messages (2)" in result
        assert "Test message 1" in result
        assert "Test message 2" in result
        assert "delayed_" in result

    @pytest.mark.asyncio
    async def test_cancel_scheduled_message_success(self, deps, mock_callback):
        """Test cancelling a scheduled message."""
        # Schedule a message
        await send_delayed_message_test_helper(deps, "Test message", 0, 0, 10)

        # Get message_id from scheduler
        scheduler = get_scheduler()
        messages = scheduler.get_scheduled_messages()
        assert len(messages) == 1
        message_id = messages[0][0]

        # Cancel the message
        result = await cancel_scheduled_message_test_helper(message_id)

        assert f"Successfully cancelled scheduled message: {message_id}" in result

        # Wait a moment for async cleanup to complete
        await asyncio.sleep(0.5)

        # Verify it was cancelled
        messages = scheduler.get_scheduled_messages()
        assert len(messages) == 0

        # Verify the callback was never called (message was successfully cancelled)
        assert len(mock_callback.calls) == 0

    @pytest.mark.asyncio
    async def test_cancel_scheduled_message_not_found(self):
        """Test cancelling a message that doesn't exist."""
        result = await cancel_scheduled_message_test_helper("nonexistent_id")
        assert (
            "Could not find scheduled message or cyclic action with ID: nonexistent_id"
            in result
        )

    @pytest.mark.asyncio
    async def test_send_delayed_message_validation(self, deps):
        """Test that send_delayed_message validates parameters."""
        # Test with all zeros (should fail)
        result = await send_delayed_message_test_helper(deps, "Test", 0, 0, 0)
        assert "Error" in result
        assert "at least 1 second" in result

        # Test with negative values
        result = await send_delayed_message_test_helper(deps, "Test", -1, 0, 0)
        assert "Error" in result


class TestCyclicActionTools:
    """Test the cyclic action scheduling tools."""

    @pytest.fixture
    def mock_callback(self):
        """Create a mock callback that tracks calls."""
        calls = []

        async def callback(message, thread_id):
            calls.append({"message": message, "thread_id": thread_id})

        callback.calls = calls
        return callback

    @pytest.fixture
    def deps(self, mock_callback):
        """Create MyDeps with thread context."""
        return MyDeps(thread_id=12345, send_message_callback=mock_callback)

    @pytest_asyncio.fixture(autouse=True)
    async def clear_cyclic_scheduler(self):
        """Clear all cyclic actions before each test."""
        cyclic_scheduler = get_cyclic_scheduler()

        tasks_to_wait = []
        for action_id, action in list(cyclic_scheduler.get_actions()):
            if action.task and not action.task.done():
                tasks_to_wait.append(action.task)
            cyclic_scheduler.cancel_action(action_id)

        for task in tasks_to_wait:
            try:
                await task
            except asyncio.CancelledError:
                pass
            except Exception:
                pass

        await asyncio.sleep(0.1)

        yield

        tasks_to_wait = []
        for action_id, action in list(cyclic_scheduler.get_actions()):
            if action.task and not action.task.done():
                tasks_to_wait.append(action.task)
            cyclic_scheduler.cancel_action(action_id)

        for task in tasks_to_wait:
            try:
                await task
            except asyncio.CancelledError:
                pass
            except Exception:
                pass

        await asyncio.sleep(0.1)

    # ── schedule_cyclic_action tests ──────────────────────────────────────────

    @pytest.mark.asyncio
    async def test_schedule_cyclic_action_success(self, deps):
        """Test scheduling a cyclic interval action."""
        result = await schedule_cyclic_action_test_helper(
            deps, "test action", 0, 0, 5, max_runs=2
        )

        assert "Error" not in result
        assert "cyclic_" in result

        # Verify it's registered
        cyclic_scheduler = get_cyclic_scheduler()
        assert len(cyclic_scheduler.get_actions()) == 1

    @pytest.mark.asyncio
    async def test_schedule_cyclic_action_zero_interval(self, deps):
        """Test that zero interval returns an error."""
        result = await schedule_cyclic_action_test_helper(deps, "test action", 0, 0, 0)
        assert "Error" in result
        assert "at least 1 second" in result

    @pytest.mark.asyncio
    async def test_schedule_cyclic_action_negative_values(self, deps):
        """Test that negative interval values return an error."""
        result = await schedule_cyclic_action_test_helper(deps, "test action", -1, 0, 0)
        assert "Error" in result

    @pytest.mark.asyncio
    async def test_schedule_cyclic_action_invalid_max_runs(self, deps):
        """Test that zero or negative max_runs returns an error."""
        result = await schedule_cyclic_action_test_helper(
            deps, "test action", 0, 0, 5, max_runs=0
        )
        assert "Error" in result

    @pytest.mark.asyncio
    async def test_schedule_cyclic_action_fires_repeatedly(self, deps, mock_callback):
        """Test that the cyclic action fires multiple times."""
        result = await schedule_cyclic_action_test_helper(
            deps, "ping", 0, 0, 0, max_runs=None
        )
        # 0-second interval fails validation
        assert "Error" in result

        # Use a valid short interval
        result = await schedule_cyclic_action_test_helper(
            deps, "ping", 0, 0, 1, max_runs=2
        )
        assert "Error" not in result

        # Wait for both runs
        await asyncio.sleep(2.5)
        assert len(mock_callback.calls) == 2

    @pytest.mark.asyncio
    async def test_schedule_cyclic_action_message_marked(self, deps, mock_callback):
        """Test that cyclic action messages are marked with DELAYED_COMMAND prefix."""
        await schedule_cyclic_action_test_helper(
            deps, "my command", 0, 0, 1, max_runs=1
        )

        await asyncio.sleep(1.5)

        assert len(mock_callback.calls) == 1
        assert mock_callback.calls[0]["message"] == "[DELAYED_COMMAND] my command"

    @pytest.mark.asyncio
    async def test_schedule_cyclic_action_without_context(self):
        """Test that cyclic action without thread context returns error."""
        deps_no_context = MyDeps()
        result = await schedule_cyclic_action_test_helper(
            deps_no_context, "test", 0, 0, 5
        )
        assert "Error" in result
        assert "missing thread context" in result

    # ── schedule_daily_action tests ───────────────────────────────────────────

    @pytest.mark.asyncio
    async def test_schedule_daily_action_success(self, deps):
        """Test scheduling a daily action at a future time."""
        tz = ZoneInfo("Europe/Warsaw")
        future = datetime.now(tz=tz) + timedelta(hours=23)
        time_str = future.strftime("%H:%M")

        result = await schedule_daily_action_test_helper(deps, "daily task", time_str)

        assert "Error" not in result
        assert "cyclic_" in result

        cyclic_scheduler = get_cyclic_scheduler()
        assert len(cyclic_scheduler.get_actions()) == 1

    @pytest.mark.asyncio
    async def test_schedule_daily_action_invalid_time(self, deps):
        """Test that invalid time_str returns an error."""
        result = await schedule_daily_action_test_helper(deps, "task", "25:00")
        assert "Error" in result

        result = await schedule_daily_action_test_helper(deps, "task", "not-a-time")
        assert "Error" in result

    @pytest.mark.asyncio
    async def test_schedule_daily_action_invalid_days_interval(self, deps):
        """Test that invalid days_interval returns an error."""
        result = await schedule_daily_action_test_helper(
            deps, "task", "07:00", days_interval=0
        )
        assert "Error" in result

    @pytest.mark.asyncio
    async def test_schedule_daily_action_weekly(self, deps):
        """Test scheduling a weekly action."""
        tz = ZoneInfo("Europe/Warsaw")
        future = datetime.now(tz=tz) + timedelta(hours=23)
        time_str = future.strftime("%H:%M")

        result = await schedule_daily_action_test_helper(
            deps, "weekly task", time_str, days_interval=7, max_runs=4
        )

        assert "Error" not in result
        cyclic_scheduler = get_cyclic_scheduler()
        actions = dict(cyclic_scheduler.get_actions())
        action = next(iter(actions.values()))
        assert action.max_runs == 4
        assert "7 days" in action.schedule_description

    # ── schedule_random_action tests ──────────────────────────────────────────

    @pytest.mark.asyncio
    async def test_schedule_random_action_success(self, deps):
        """Test scheduling a random window action."""
        result = await schedule_random_action_test_helper(
            deps, "random task", start_hour=23, end_hour=24
        )

        assert "Error" not in result
        assert "cyclic_" in result

    @pytest.mark.asyncio
    async def test_schedule_random_action_invalid_window(self, deps):
        """Test that invalid hour window returns an error."""
        result = await schedule_random_action_test_helper(
            deps, "task", start_hour=18, end_hour=9
        )
        assert "Error" in result

        result = await schedule_random_action_test_helper(
            deps, "task", start_hour=9, end_hour=9
        )
        assert "Error" in result

    @pytest.mark.asyncio
    async def test_schedule_random_action_without_context(self):
        """Test that random action without thread context returns error."""
        deps_no_context = MyDeps()
        result = await schedule_random_action_test_helper(
            deps_no_context, "task", start_hour=9, end_hour=18
        )
        assert "Error" in result
        assert "missing thread context" in result

    # ── cancel cyclic action tests ────────────────────────────────────────────

    @pytest.mark.asyncio
    async def test_cancel_cyclic_action_success(self, deps):
        """Test cancelling a cyclic action by ID."""
        result = await schedule_cyclic_action_test_helper(deps, "ping", 0, 1, 0)
        assert "Error" not in result

        cyclic_scheduler = get_cyclic_scheduler()
        actions = cyclic_scheduler.get_actions()
        assert len(actions) == 1
        action_id = actions[0][0]

        cancel_result = await cancel_scheduled_message_test_helper(action_id)
        assert "Successfully cancelled cyclic action" in cancel_result
        assert len(cyclic_scheduler.get_actions()) == 0

    # ── list combined tests ───────────────────────────────────────────────────

    @pytest.mark.asyncio
    async def test_list_shows_cyclic_actions(self, deps):
        """Test that list_scheduled_messages shows cyclic actions."""
        await schedule_cyclic_action_test_helper(
            deps, "cyclic test", 0, 1, 0, max_runs=5
        )

        result = await list_scheduled_messages_test_helper()

        assert "Cyclic actions" in result
        assert "cyclic test" in result
        assert "cyclic_" in result

    @pytest.mark.asyncio
    async def test_list_shows_both_types(self, deps):
        """Test that list shows both one-time and cyclic actions."""
        # Add a one-time delayed message
        await send_delayed_message_test_helper(deps, "one-time msg", 0, 0, 30)

        # Add a cyclic action
        await schedule_cyclic_action_test_helper(deps, "cyclic msg", 0, 1, 0)

        result = await list_scheduled_messages_test_helper()

        assert "One-time scheduled messages" in result
        assert "Cyclic actions" in result
        assert "one-time msg" in result
        assert "cyclic msg" in result
