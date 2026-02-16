"""Unit tests for delayed_message_scheduler.py module."""

import asyncio
import pytest
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from src.delayed_message_scheduler import DelayedMessageScheduler


class TestDelayedMessageScheduler:
    """Test the DelayedMessageScheduler class."""

    @pytest.fixture
    def scheduler(self):
        """Create a fresh scheduler instance for each test."""
        return DelayedMessageScheduler()

    @pytest.fixture
    def mock_callback(self):
        """Create a mock callback that tracks calls."""
        calls = []

        async def callback(message, thread_id):
            calls.append({"message": message, "thread_id": thread_id})

        callback.calls = calls
        return callback

    @pytest.mark.asyncio
    async def test_schedule_message(self, scheduler, mock_callback):
        """Test scheduling a message."""
        message_id = await scheduler.schedule_message(
            message="Test message",
            thread_id=123456,
            delay_seconds=1,
            send_callback=mock_callback,
        )

        assert message_id.startswith("delayed_")
        assert len(scheduler.get_scheduled_messages()) == 1

        # Wait for message to be sent
        await asyncio.sleep(1.2)

        # Verify callback was called
        assert len(mock_callback.calls) == 1
        assert mock_callback.calls[0]["message"] == "Test message"
        assert mock_callback.calls[0]["thread_id"] == 123456

        # Verify message was removed from scheduler
        assert len(scheduler.get_scheduled_messages()) == 0

    @pytest.mark.asyncio
    async def test_cancel_message(self, scheduler, mock_callback):
        """Test cancelling a scheduled message."""
        message_id = await scheduler.schedule_message(
            message="Test message",
            thread_id=123456,
            delay_seconds=2,
            send_callback=mock_callback,
        )

        assert len(scheduler.get_scheduled_messages()) == 1

        # Cancel the message
        result = scheduler.cancel_message(message_id)
        assert result is True

        # Wait to ensure message is not sent
        await asyncio.sleep(2.5)

        # Verify callback was not called - this is the most important check
        assert len(mock_callback.calls) == 0

    @pytest.mark.asyncio
    async def test_cancel_nonexistent_message(self, scheduler):
        """Test cancelling a message that doesn't exist."""
        result = scheduler.cancel_message("nonexistent_id")
        assert result is False

    @pytest.mark.asyncio
    async def test_multiple_messages(self, scheduler, mock_callback):
        """Test scheduling multiple messages."""
        message_id_1 = await scheduler.schedule_message(
            message="Message 1",
            thread_id=111,
            delay_seconds=1,
            send_callback=mock_callback,
        )

        message_id_2 = await scheduler.schedule_message(
            message="Message 2",
            thread_id=222,
            delay_seconds=2,
            send_callback=mock_callback,
        )

        assert len(scheduler.get_scheduled_messages()) == 2
        assert message_id_1 != message_id_2

        # Wait for both messages
        await asyncio.sleep(2.5)

        # Verify both callbacks were called
        assert len(mock_callback.calls) == 2

        # Verify messages were removed
        assert len(scheduler.get_scheduled_messages()) == 0

    @pytest.mark.asyncio
    async def test_get_scheduled_messages(self, scheduler, mock_callback):
        """Test getting list of scheduled messages."""
        await scheduler.schedule_message(
            message="Test 1",
            thread_id=111,
            delay_seconds=10,
            send_callback=mock_callback,
        )

        await scheduler.schedule_message(
            message="Test 2",
            thread_id=222,
            delay_seconds=10,
            send_callback=mock_callback,
        )

        messages = scheduler.get_scheduled_messages()
        assert len(messages) == 2

        # Verify structure
        for message_id, delayed_msg in messages:
            assert isinstance(message_id, str)
            assert delayed_msg.message in ["Test 1", "Test 2"]

    @pytest.mark.asyncio
    async def test_schedule_message_at(self, scheduler, mock_callback):
        """Test scheduling a message at a specific datetime."""
        # Schedule a message 1 second in the future using timezone-aware datetime
        tz = ZoneInfo("Europe/Warsaw")
        scheduled_time = datetime.now(tz=tz) + timedelta(seconds=1)

        message_id = await scheduler.schedule_message_at(
            message="Test message",
            thread_id=123456,
            scheduled_time=scheduled_time,
            send_callback=mock_callback,
        )

        assert message_id.startswith("scheduled_")
        assert len(scheduler.get_scheduled_messages()) == 1

        # Wait for message to be sent
        await asyncio.sleep(1.2)

        # Verify callback was called
        assert len(mock_callback.calls) == 1
        assert mock_callback.calls[0]["message"] == "Test message"
        assert mock_callback.calls[0]["thread_id"] == 123456

        # Verify message was removed from scheduler
        assert len(scheduler.get_scheduled_messages()) == 0

    @pytest.mark.asyncio
    async def test_schedule_message_at_past_time(self, scheduler, mock_callback):
        """Test that scheduling a message in the past raises an error."""
        # Try to schedule a message in the past
        past_time = datetime.now() - timedelta(seconds=10)

        with pytest.raises(ValueError, match="Scheduled time must be in the future"):
            await scheduler.schedule_message_at(
                message="Test message",
                thread_id=123456,
                scheduled_time=past_time,
                send_callback=mock_callback,
            )

    @pytest.mark.asyncio
    async def test_schedule_message_at_specific_date(self, scheduler, mock_callback):
        """Test scheduling a message at a specific date and time."""
        # Schedule a message 2 seconds in the future with a specific datetime
        tz = ZoneInfo("Europe/Warsaw")
        scheduled_time = datetime.now(tz=tz) + timedelta(seconds=2)

        message_id = await scheduler.schedule_message_at(
            message="Scheduled message",
            thread_id=999,
            scheduled_time=scheduled_time,
            send_callback=mock_callback,
        )

        assert message_id.startswith("scheduled_")

        # Get the scheduled message and verify its scheduled_time
        messages = scheduler.get_scheduled_messages()
        assert len(messages) == 1
        msg_id, delayed_msg = messages[0]
        assert delayed_msg.scheduled_time == scheduled_time

        # Wait for message to be sent
        await asyncio.sleep(2.2)

        # Verify callback was called
        assert len(mock_callback.calls) == 1
        assert mock_callback.calls[0]["message"] == "Scheduled message"

    @pytest.mark.asyncio
    async def test_schedule_message_at_with_timezone(self, scheduler, mock_callback):
        """Test scheduling a message with timezone-aware datetime."""
        # Create a timezone-aware datetime 1 second in the future
        tz = ZoneInfo("Europe/Warsaw")
        scheduled_time = datetime.now(tz=tz) + timedelta(seconds=1)

        message_id = await scheduler.schedule_message_at(
            message="Timezone test",
            thread_id=777,
            scheduled_time=scheduled_time,
            send_callback=mock_callback,
        )

        assert message_id.startswith("scheduled_")
        assert len(scheduler.get_scheduled_messages()) == 1

        # Wait for message to be sent
        await asyncio.sleep(1.2)

        # Verify callback was called
        assert len(mock_callback.calls) == 1
        assert mock_callback.calls[0]["message"] == "Timezone test"
        assert mock_callback.calls[0]["thread_id"] == 777

    @pytest.mark.asyncio
    async def test_schedule_message_at_naive_datetime(self, scheduler, mock_callback):
        """Test that naive datetime is treated as DEFAULT_TIMEZONE."""
        # Create a naive datetime that's 1 second in the future in Europe/Warsaw time
        # First get current time in Europe/Warsaw
        tz = ZoneInfo("Europe/Warsaw")
        current_time_in_tz = datetime.now(tz=tz)
        
        # Create a naive datetime 1 second in the future
        # by taking the tz-aware time, adding 1 second, then removing tz info
        future_time_in_tz = current_time_in_tz + timedelta(seconds=1)
        scheduled_time = future_time_in_tz.replace(tzinfo=None)
        # This is now a naive datetime representing 1 second in the future in Europe/Warsaw

        message_id = await scheduler.schedule_message_at(
            message="Naive datetime test",
            thread_id=888,
            scheduled_time=scheduled_time,
            send_callback=mock_callback,
        )

        assert message_id.startswith("scheduled_")

        # Wait for message to be sent
        await asyncio.sleep(1.2)

        # Verify callback was called
        assert len(mock_callback.calls) == 1
        assert mock_callback.calls[0]["message"] == "Naive datetime test"

    @pytest.mark.asyncio
    async def test_get_default_timezone(self, scheduler):
        """Test that we can get the default timezone."""
        tz = scheduler.get_default_timezone()
        assert tz == "Europe/Warsaw"
