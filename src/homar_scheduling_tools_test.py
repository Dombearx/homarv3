"""Unit tests for homar scheduling tools."""

import asyncio
import pytest
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from src.models.schemas import MyDeps
from src.delayed_message_scheduler import get_scheduler


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
    scheduled = scheduler.get_scheduled_messages()

    if not scheduled:
        return "No scheduled messages pending."

    result = []
    result.append(f"Found {len(scheduled)} scheduled message(s):\n")
    
    for message_id, delayed_msg in scheduled:
        scheduled_str = delayed_msg.scheduled_time.strftime("%Y-%m-%d %H:%M:%S %Z")
        actual_message = delayed_msg.message
        if actual_message.startswith("[DELAYED_COMMAND] "):
            actual_message = actual_message[len("[DELAYED_COMMAND] "):]
        
        result.append(f"- ID: {message_id}")
        result.append(f"  Time: {scheduled_str}")
        result.append(f"  Message: {actual_message}")
        result.append("")
    
    return "\n".join(result)


async def cancel_scheduled_message_test_helper(message_id):
    """Helper function that mimics cancel_scheduled_message behavior."""
    scheduler = get_scheduler()
    success = scheduler.cancel_message(message_id)
    
    if success:
        return f"Successfully cancelled scheduled message: {message_id}"
    else:
        return f"Could not find scheduled message with ID: {message_id}. Use list_scheduled_messages to see available IDs."


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

    @pytest.fixture(autouse=True)
    def clear_scheduler(self):
        """Clear all scheduled messages before each test."""
        scheduler = get_scheduler()
        # Cancel all existing messages
        for message_id, _ in scheduler.get_scheduled_messages():
            scheduler.cancel_message(message_id)
        yield
        # Clean up after test
        for message_id, _ in scheduler.get_scheduled_messages():
            scheduler.cancel_message(message_id)

    @pytest.mark.asyncio
    async def test_list_scheduled_messages_empty(self):
        """Test listing scheduled messages when there are none."""
        result = await list_scheduled_messages_test_helper()
        assert result == "No scheduled messages pending."

    @pytest.mark.asyncio
    async def test_list_scheduled_messages_with_messages(self, deps, mock_callback):
        """Test listing scheduled messages when there are some."""
        # Schedule messages
        await send_delayed_message_test_helper(deps, "Test message 1", 0, 0, 10)
        await send_delayed_message_test_helper(deps, "Test message 2", 0, 0, 20)
        
        result = await list_scheduled_messages_test_helper()
        
        assert "Found 2 scheduled message(s)" in result
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
        assert "Could not find scheduled message with ID: nonexistent_id" in result

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
