"""Unit tests for cyclic_action_scheduler.py module."""

import asyncio
import pytest
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, patch
from zoneinfo import ZoneInfo
from src.cyclic_action_scheduler import CyclicActionScheduler, DEFAULT_TIMEZONE


class TestCyclicActionScheduler:
    """Test the CyclicActionScheduler class."""

    @pytest.fixture
    def scheduler(self):
        """Create a fresh scheduler instance for each test."""
        return CyclicActionScheduler()

    @pytest.fixture
    def mock_callback(self):
        """Create a mock async callback that tracks calls."""
        calls = []

        async def callback(message, thread_id):
            calls.append({"message": message, "thread_id": thread_id})

        callback.calls = calls
        return callback

    # ── schedule_interval ────────────────────────────────────────────────────

    @pytest.mark.asyncio
    async def test_schedule_interval_basic(self, scheduler, mock_callback):
        """Test that interval action fires repeatedly."""
        action_id = await scheduler.schedule_interval(
            message="ping",
            thread_id=111,
            interval_seconds=0.1,
            send_callback=mock_callback,
        )

        assert action_id.startswith("cyclic_")
        assert len(scheduler.get_actions()) == 1

        await asyncio.sleep(0.45)
        scheduler.cancel_action(action_id)
        await asyncio.sleep(0.05)

        # Should have fired ~4 times in 0.45s with 0.1s interval
        assert len(mock_callback.calls) >= 3

    @pytest.mark.asyncio
    async def test_schedule_interval_with_max_runs(self, scheduler, mock_callback):
        """Test that interval action stops after max_runs."""
        action_id = await scheduler.schedule_interval(
            message="ping",
            thread_id=111,
            interval_seconds=0.1,
            send_callback=mock_callback,
            max_runs=3,
        )

        # Wait long enough for all runs to complete
        await asyncio.sleep(0.5)

        assert len(mock_callback.calls) == 3
        # Action should have removed itself
        assert action_id not in dict(scheduler.get_actions())

    @pytest.mark.asyncio
    async def test_schedule_interval_cancelled_before_first_run(
        self, scheduler, mock_callback
    ):
        """Test that cancelling before first run prevents any calls."""
        action_id = await scheduler.schedule_interval(
            message="ping",
            thread_id=111,
            interval_seconds=2,
            send_callback=mock_callback,
        )

        scheduler.cancel_action(action_id)
        await asyncio.sleep(0.1)

        assert len(mock_callback.calls) == 0

    @pytest.mark.asyncio
    async def test_schedule_interval_invalid_interval(self, scheduler, mock_callback):
        """Test that non-positive interval raises ValueError."""
        with pytest.raises(ValueError, match="interval_seconds must be positive"):
            await scheduler.schedule_interval(
                message="ping",
                thread_id=111,
                interval_seconds=0,
                send_callback=mock_callback,
            )

    @pytest.mark.asyncio
    async def test_schedule_interval_invalid_max_runs(self, scheduler, mock_callback):
        """Test that non-positive max_runs raises ValueError."""
        with pytest.raises(ValueError, match="max_runs must be positive"):
            await scheduler.schedule_interval(
                message="ping",
                thread_id=111,
                interval_seconds=1,
                send_callback=mock_callback,
                max_runs=0,
            )

    # ── schedule_at_time ─────────────────────────────────────────────────────

    @pytest.mark.asyncio
    async def test_schedule_at_time_invalid_time_str(self, scheduler, mock_callback):
        """Test that invalid time strings raise ValueError."""
        with pytest.raises(ValueError, match="Invalid time_str"):
            await scheduler.schedule_at_time(
                message="ping",
                thread_id=111,
                time_str="25:00",
                send_callback=mock_callback,
            )

        with pytest.raises(ValueError, match="Invalid time_str"):
            await scheduler.schedule_at_time(
                message="ping",
                thread_id=111,
                time_str="not-a-time",
                send_callback=mock_callback,
            )

    @pytest.mark.asyncio
    async def test_schedule_at_time_invalid_days_interval(
        self, scheduler, mock_callback
    ):
        """Test that non-positive days_interval raises ValueError."""
        with pytest.raises(ValueError, match="days_interval must be positive"):
            await scheduler.schedule_at_time(
                message="ping",
                thread_id=111,
                time_str="07:00",
                send_callback=mock_callback,
                days_interval=0,
            )

    @pytest.mark.asyncio
    async def test_schedule_at_time_registers_action(self, scheduler, mock_callback):
        """Test that schedule_at_time registers the action correctly."""
        # Use a far-future time so we don't need to wait
        tz = ZoneInfo(DEFAULT_TIMEZONE)
        future = datetime.now(tz=tz) + timedelta(hours=23)
        time_str = future.strftime("%H:%M")

        action_id = await scheduler.schedule_at_time(
            message="ping",
            thread_id=111,
            time_str=time_str,
            send_callback=mock_callback,
            days_interval=1,
            max_runs=5,
        )

        assert action_id.startswith("cyclic_")
        actions = dict(scheduler.get_actions())
        assert action_id in actions
        assert actions[action_id].max_runs == 5
        assert "At" in actions[action_id].schedule_description

        scheduler.cancel_action(action_id)

    @pytest.mark.asyncio
    async def test_schedule_at_time_description_daily(self, scheduler, mock_callback):
        """Test that schedule description shows 'daily' for days_interval=1."""
        tz = ZoneInfo(DEFAULT_TIMEZONE)
        future = datetime.now(tz=tz) + timedelta(hours=23)
        time_str = future.strftime("%H:%M")

        action_id = await scheduler.schedule_at_time(
            message="ping",
            thread_id=111,
            time_str=time_str,
            send_callback=mock_callback,
        )

        actions = dict(scheduler.get_actions())
        assert "daily" in actions[action_id].schedule_description

        scheduler.cancel_action(action_id)

    @pytest.mark.asyncio
    async def test_schedule_at_time_description_weekly(self, scheduler, mock_callback):
        """Test that schedule description shows 'every 7 days' for days_interval=7."""
        tz = ZoneInfo(DEFAULT_TIMEZONE)
        future = datetime.now(tz=tz) + timedelta(hours=23)
        time_str = future.strftime("%H:%M")

        action_id = await scheduler.schedule_at_time(
            message="ping",
            thread_id=111,
            time_str=time_str,
            send_callback=mock_callback,
            days_interval=7,
        )

        actions = dict(scheduler.get_actions())
        assert "every 7 days" in actions[action_id].schedule_description

        scheduler.cancel_action(action_id)

    # ── schedule_random_window ────────────────────────────────────────────────

    @pytest.mark.asyncio
    async def test_schedule_random_window_invalid_hours(self, scheduler, mock_callback):
        """Test that invalid hour ranges raise ValueError."""
        with pytest.raises(ValueError, match="Invalid window"):
            await scheduler.schedule_random_window(
                message="ping",
                thread_id=111,
                start_hour=10,
                end_hour=9,
                send_callback=mock_callback,
            )

        with pytest.raises(ValueError, match="Invalid window"):
            await scheduler.schedule_random_window(
                message="ping",
                thread_id=111,
                start_hour=5,
                end_hour=5,
                send_callback=mock_callback,
            )

    @pytest.mark.asyncio
    async def test_schedule_random_window_registers_action(
        self, scheduler, mock_callback
    ):
        """Test that schedule_random_window registers the action."""
        # Use future window (start_hour = 23) to avoid immediate firing in tests
        action_id = await scheduler.schedule_random_window(
            message="ping",
            thread_id=111,
            start_hour=23,
            end_hour=24,
            send_callback=mock_callback,
            max_runs=3,
        )

        assert action_id.startswith("cyclic_")
        actions = dict(scheduler.get_actions())
        assert action_id in actions
        assert actions[action_id].max_runs == 3
        assert "Random time" in actions[action_id].schedule_description

        scheduler.cancel_action(action_id)

    @pytest.mark.asyncio
    async def test_schedule_random_window_fires_within_window(
        self, scheduler, mock_callback
    ):
        """Test that random window fires once when max_runs=1, using a mocked window time."""
        from datetime import datetime, timedelta
        from unittest.mock import patch
        from zoneinfo import ZoneInfo

        tz = ZoneInfo(DEFAULT_TIMEZONE)

        # Patch _next_random_window_time to always return "now + 0.1 seconds"
        def mock_next_time(now, start_hour, end_hour):
            return now + timedelta(seconds=0.1)

        with patch.object(scheduler, "_next_random_window_time", side_effect=mock_next_time):
            action_id = await scheduler.schedule_random_window(
                message="ping",
                thread_id=111,
                start_hour=0,
                end_hour=24,
                send_callback=mock_callback,
                max_runs=1,
            )

            await asyncio.sleep(0.5)

        assert len(mock_callback.calls) == 1
        assert action_id not in dict(scheduler.get_actions())

    # ── _next_random_window_time ──────────────────────────────────────────────

    def test_next_random_window_time_within_window(self, scheduler):
        """Test that _next_random_window_time returns a time within the window."""
        tz = ZoneInfo(DEFAULT_TIMEZONE)
        # Use a time at 10:00 so we're inside the 9-18 window
        now = datetime.now(tz=tz).replace(hour=10, minute=0, second=0, microsecond=0)

        result = scheduler._next_random_window_time(now, start_hour=9, end_hour=18)

        window_start = now.replace(hour=9, minute=0, second=0, microsecond=0)
        window_end = now.replace(hour=18, minute=0, second=0, microsecond=0)

        assert result >= now + timedelta(seconds=1)
        assert result <= window_end

    def test_next_random_window_time_past_window_uses_tomorrow(self, scheduler):
        """Test that _next_random_window_time uses tomorrow when today's window is past."""
        tz = ZoneInfo(DEFAULT_TIMEZONE)
        # Set time to 20:00 (after the 9-18 window)
        now = datetime.now(tz=tz).replace(hour=20, minute=0, second=0, microsecond=0)

        result = scheduler._next_random_window_time(now, start_hour=9, end_hour=18)

        tomorrow_start = (now + timedelta(days=1)).replace(
            hour=9, minute=0, second=0, microsecond=0
        )
        tomorrow_end = (now + timedelta(days=1)).replace(
            hour=18, minute=0, second=0, microsecond=0
        )

        assert result >= tomorrow_start
        assert result <= tomorrow_end

    def test_next_random_window_time_end_hour_24(self, scheduler):
        """Test that end_hour=24 (midnight) is handled correctly."""
        tz = ZoneInfo(DEFAULT_TIMEZONE)
        now = datetime.now(tz=tz).replace(hour=22, minute=0, second=0, microsecond=0)

        result = scheduler._next_random_window_time(now, start_hour=21, end_hour=24)

        # Should be within today's 21:00-24:00 window
        assert result > now

    # ── cancel_action ─────────────────────────────────────────────────────────

    @pytest.mark.asyncio
    async def test_cancel_action_success(self, scheduler, mock_callback):
        """Test cancelling an active cyclic action."""
        action_id = await scheduler.schedule_interval(
            message="ping",
            thread_id=111,
            interval_seconds=10,
            send_callback=mock_callback,
        )

        assert len(scheduler.get_actions()) == 1
        result = scheduler.cancel_action(action_id)
        assert result is True
        assert len(scheduler.get_actions()) == 0

    def test_cancel_nonexistent_action(self, scheduler):
        """Test cancelling an action that doesn't exist."""
        result = scheduler.cancel_action("nonexistent_id")
        assert result is False

    # ── get_actions ───────────────────────────────────────────────────────────

    @pytest.mark.asyncio
    async def test_get_actions_multiple(self, scheduler, mock_callback):
        """Test get_actions with multiple registered actions."""
        id1 = await scheduler.schedule_interval(
            message="ping1",
            thread_id=111,
            interval_seconds=10,
            send_callback=mock_callback,
        )
        id2 = await scheduler.schedule_interval(
            message="ping2",
            thread_id=222,
            interval_seconds=20,
            send_callback=mock_callback,
        )

        actions = scheduler.get_actions()
        assert len(actions) == 2
        ids = {aid for aid, _ in actions}
        assert id1 in ids
        assert id2 in ids

        scheduler.cancel_action(id1)
        scheduler.cancel_action(id2)

    @pytest.mark.asyncio
    async def test_get_actions_empty(self, scheduler):
        """Test get_actions when no actions are scheduled."""
        assert scheduler.get_actions() == []

    # ── get_default_timezone ──────────────────────────────────────────────────

    def test_get_default_timezone(self, scheduler):
        """Test that the default timezone is returned correctly."""
        assert scheduler.get_default_timezone() == DEFAULT_TIMEZONE

    # ── run_count tracking ────────────────────────────────────────────────────

    @pytest.mark.asyncio
    async def test_run_count_increments(self, scheduler, mock_callback):
        """Test that run_count increments on each execution."""
        action_id = await scheduler.schedule_interval(
            message="ping",
            thread_id=111,
            interval_seconds=0.1,
            send_callback=mock_callback,
            max_runs=3,
        )

        await asyncio.sleep(0.5)

        # Action should have completed and removed itself
        assert action_id not in dict(scheduler.get_actions())
        assert len(mock_callback.calls) == 3

    # ── schedule description ──────────────────────────────────────────────────

    @pytest.mark.asyncio
    async def test_interval_action_description(self, scheduler, mock_callback):
        """Test that interval action has correct description."""
        action_id = await scheduler.schedule_interval(
            message="ping",
            thread_id=111,
            interval_seconds=30,
            send_callback=mock_callback,
            max_runs=5,
        )

        actions = dict(scheduler.get_actions())
        desc = actions[action_id].schedule_description
        assert "30" in desc
        assert "5" in desc

        scheduler.cancel_action(action_id)

    @pytest.mark.asyncio
    async def test_random_window_action_description(self, scheduler, mock_callback):
        """Test that random window action has correct description."""
        action_id = await scheduler.schedule_random_window(
            message="ping",
            thread_id=111,
            start_hour=7,
            end_hour=21,
            send_callback=mock_callback,
            days_interval=7,
        )

        actions = dict(scheduler.get_actions())
        desc = actions[action_id].schedule_description
        assert "07:00" in desc
        assert "21:00" in desc
        assert "7" in desc

        scheduler.cancel_action(action_id)
