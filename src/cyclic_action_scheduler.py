"""Scheduler for cyclic (repeating) actions."""

import asyncio
import random
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from loguru import logger

# Default timezone for scheduling (Europe/Warsaw - CET/CEST)
DEFAULT_TIMEZONE = "Europe/Warsaw"


@dataclass
class CyclicAction:
    """Represents a repeating cyclic action."""

    message: str
    thread_id: int
    max_runs: int | None  # None = unlimited
    schedule_description: str
    run_count: int = 0
    task: asyncio.Task | None = None
    created_at: datetime = field(default_factory=datetime.now)


class CyclicActionScheduler:
    """Manages scheduling and delivery of repeating cyclic actions."""

    def __init__(self):
        self._actions: dict[str, CyclicAction] = {}
        self._counter = 0

    def _next_id(self) -> str:
        self._counter += 1
        return f"cyclic_{self._counter}"

    async def schedule_interval(
        self,
        message: str,
        thread_id: int,
        interval_seconds: float,
        send_callback,
        max_runs: int | None = None,
    ) -> str:
        """
        Schedule a message to be sent repeatedly every interval_seconds.

        Args:
            message: The message content to send
            thread_id: The Discord thread ID to send the message to
            interval_seconds: How many seconds between each send
            send_callback: Async function to call to send the message
            max_runs: Maximum number of times to send (None = unlimited)

        Returns:
            A unique identifier for this cyclic action
        """
        if interval_seconds <= 0:
            raise ValueError("interval_seconds must be positive")
        if max_runs is not None and max_runs <= 0:
            raise ValueError("max_runs must be positive if specified")

        action_id = self._next_id()
        description = f"Every {interval_seconds}s"
        if max_runs:
            description += f", max {max_runs} times"

        action = CyclicAction(
            message=message,
            thread_id=thread_id,
            max_runs=max_runs,
            schedule_description=description,
        )
        self._actions[action_id] = action

        task = asyncio.create_task(
            self._run_interval_loop(action_id, action, interval_seconds, send_callback)
        )
        action.task = task

        logger.info(
            f"Scheduled cyclic interval action {action_id} for thread {thread_id} "
            f"every {interval_seconds}s"
            + (f", max {max_runs} runs" if max_runs else "")
        )
        return action_id

    async def schedule_at_time(
        self,
        message: str,
        thread_id: int,
        time_str: str,
        send_callback,
        days_interval: int = 1,
        max_runs: int | None = None,
    ) -> str:
        """
        Schedule a message to be sent at a specific time each day (or every N days).

        Args:
            message: The message content to send
            thread_id: The Discord thread ID to send the message to
            time_str: Time of day in "HH:MM" format (24-hour)
            send_callback: Async function to call to send the message
            days_interval: How many days between each send (default 1 = daily)
            max_runs: Maximum number of times to send (None = unlimited)

        Returns:
            A unique identifier for this cyclic action
        """
        try:
            parts = time_str.split(":")
            if len(parts) != 2:
                raise ValueError("Expected HH:MM")
            hour, minute = int(parts[0]), int(parts[1])
            if not (0 <= hour <= 23 and 0 <= minute <= 59):
                raise ValueError("Hour must be 0-23 and minute 0-59")
        except (ValueError, AttributeError) as exc:
            raise ValueError(
                f"Invalid time_str '{time_str}'. Must be 'HH:MM' (e.g. '07:00')"
            ) from exc

        if days_interval <= 0:
            raise ValueError("days_interval must be positive")
        if max_runs is not None and max_runs <= 0:
            raise ValueError("max_runs must be positive if specified")

        action_id = self._next_id()
        freq = "daily" if days_interval == 1 else f"every {days_interval} days"
        description = f"At {time_str} {freq}"
        if max_runs:
            description += f", max {max_runs} times"

        action = CyclicAction(
            message=message,
            thread_id=thread_id,
            max_runs=max_runs,
            schedule_description=description,
        )
        self._actions[action_id] = action

        task = asyncio.create_task(
            self._run_at_time_loop(
                action_id, action, hour, minute, days_interval, send_callback
            )
        )
        action.task = task

        logger.info(
            f"Scheduled cyclic at-time action {action_id} for thread {thread_id} "
            f"at {time_str} every {days_interval} day(s)"
            + (f", max {max_runs} runs" if max_runs else "")
        )
        return action_id

    async def schedule_random_window(
        self,
        message: str,
        thread_id: int,
        start_hour: int,
        end_hour: int,
        send_callback,
        days_interval: int = 1,
        max_runs: int | None = None,
    ) -> str:
        """
        Schedule a message to be sent at a random time within a daily window.

        Args:
            message: The message content to send
            thread_id: The Discord thread ID to send the message to
            start_hour: Start of the daily window (0-23, inclusive)
            end_hour: End of the daily window (1-24, exclusive)
            send_callback: Async function to call to send the message
            days_interval: How many days between each send (default 1 = daily)
            max_runs: Maximum number of times to send (None = unlimited)

        Returns:
            A unique identifier for this cyclic action
        """
        if not (0 <= start_hour < end_hour <= 24):
            raise ValueError(
                f"Invalid window: start_hour={start_hour}, end_hour={end_hour}. "
                "end_hour must be > start_hour and both in range 0-24."
            )
        if days_interval <= 0:
            raise ValueError("days_interval must be positive")
        if max_runs is not None and max_runs <= 0:
            raise ValueError("max_runs must be positive if specified")

        action_id = self._next_id()
        freq = "daily" if days_interval == 1 else f"every {days_interval} days"
        description = (
            f"Random time between {start_hour:02d}:00 and {end_hour:02d}:00 {freq}"
        )
        if max_runs:
            description += f", max {max_runs} times"

        action = CyclicAction(
            message=message,
            thread_id=thread_id,
            max_runs=max_runs,
            schedule_description=description,
        )
        self._actions[action_id] = action

        task = asyncio.create_task(
            self._run_random_window_loop(
                action_id, action, start_hour, end_hour, days_interval, send_callback
            )
        )
        action.task = task

        logger.info(
            f"Scheduled cyclic random-window action {action_id} for thread {thread_id} "
            f"between {start_hour:02d}:00 and {end_hour:02d}:00 every {days_interval} day(s)"
            + (f", max {max_runs} runs" if max_runs else "")
        )
        return action_id

    def cancel_action(self, action_id: str) -> bool:
        """
        Cancel a cyclic action.

        Args:
            action_id: The ID of the action to cancel

        Returns:
            True if the action was cancelled, False if not found
        """
        action = self._actions.get(action_id)
        if action and action.task:
            action.task.cancel()
            del self._actions[action_id]
            logger.info(f"Cancelled cyclic action {action_id}")
            return True
        return False

    def get_actions(self) -> list[tuple[str, CyclicAction]]:
        """Get all currently active cyclic actions."""
        return list(self._actions.items())

    def get_default_timezone(self) -> str:
        """Get the default timezone for scheduling."""
        return DEFAULT_TIMEZONE

    # ── Internal loop helpers ──────────────────────────────────────────────

    async def _run_interval_loop(
        self,
        action_id: str,
        action: CyclicAction,
        interval_seconds: float,
        send_callback,
    ):
        """Internal loop for interval-based cyclic actions."""
        try:
            while action_id in self._actions:
                await asyncio.sleep(interval_seconds)
                if action_id not in self._actions:
                    break
                action.run_count += 1
                logger.info(
                    f"Running cyclic action {action_id} (run {action.run_count}"
                    + (f"/{action.max_runs}" if action.max_runs else "")
                    + ")"
                )
                await send_callback(action.message, action.thread_id)
                if action.max_runs is not None and action.run_count >= action.max_runs:
                    if action_id in self._actions:
                        del self._actions[action_id]
                    break
        except asyncio.CancelledError:
            logger.info(f"Cyclic interval action {action_id} was cancelled")
            raise
        except Exception as e:
            logger.error(f"Error in cyclic interval action {action_id}: {e}")
            if action_id in self._actions:
                del self._actions[action_id]

    async def _run_at_time_loop(
        self,
        action_id: str,
        action: CyclicAction,
        hour: int,
        minute: int,
        days_interval: int,
        send_callback,
    ):
        """Internal loop for time-of-day based cyclic actions."""
        try:
            while action_id in self._actions:
                tz = ZoneInfo(DEFAULT_TIMEZONE)
                now = datetime.now(tz=tz)

                # Find the next occurrence of hour:minute
                next_run = now.replace(
                    hour=hour, minute=minute, second=0, microsecond=0
                )
                if next_run <= now:
                    next_run += timedelta(days=1)

                delay = (next_run - now).total_seconds()
                await asyncio.sleep(delay)

                if action_id not in self._actions:
                    break

                action.run_count += 1
                logger.info(
                    f"Running cyclic at-time action {action_id} (run {action.run_count}"
                    + (f"/{action.max_runs}" if action.max_runs else "")
                    + ")"
                )
                await send_callback(action.message, action.thread_id)

                if action.max_runs is not None and action.run_count >= action.max_runs:
                    if action_id in self._actions:
                        del self._actions[action_id]
                    break

                # If days_interval > 1, skip ahead so the loop doesn't fire
                # again at the same time tomorrow
                if days_interval > 1:
                    await asyncio.sleep((days_interval - 1) * 86400)

        except asyncio.CancelledError:
            logger.info(f"Cyclic at-time action {action_id} was cancelled")
            raise
        except Exception as e:
            logger.error(f"Error in cyclic at-time action {action_id}: {e}")
            if action_id in self._actions:
                del self._actions[action_id]

    def _next_random_window_time(
        self, now: datetime, start_hour: int, end_hour: int
    ) -> datetime:
        """Calculate the next random run time within the [start_hour, end_hour) window."""
        tz = now.tzinfo or ZoneInfo(DEFAULT_TIMEZONE)

        today_start = now.replace(
            hour=start_hour, minute=0, second=0, microsecond=0, tzinfo=tz
        )
        today_end = now.replace(
            hour=end_hour % 24,
            minute=0,
            second=0,
            microsecond=0,
            tzinfo=tz,
        )
        # Handle end_hour == 24 (midnight next day)
        if end_hour == 24:
            today_end = (now + timedelta(days=1)).replace(
                hour=0, minute=0, second=0, microsecond=0, tzinfo=tz
            )

        # Try today's window (must be at least 1 second in the future)
        effective_start = max(now + timedelta(seconds=1), today_start)
        if effective_start < today_end:
            window_secs = (today_end - effective_start).total_seconds()
            offset = random.uniform(0, window_secs)
            return effective_start + timedelta(seconds=offset)

        # Fall back to tomorrow's window
        tomorrow_start = today_start + timedelta(days=1)
        tomorrow_end = today_end + timedelta(days=1)
        window_secs = (tomorrow_end - tomorrow_start).total_seconds()
        offset = random.uniform(0, window_secs)
        return tomorrow_start + timedelta(seconds=offset)

    async def _run_random_window_loop(
        self,
        action_id: str,
        action: CyclicAction,
        start_hour: int,
        end_hour: int,
        days_interval: int,
        send_callback,
    ):
        """Internal loop for random-window cyclic actions."""
        try:
            while action_id in self._actions:
                tz = ZoneInfo(DEFAULT_TIMEZONE)
                now = datetime.now(tz=tz)

                run_at = self._next_random_window_time(now, start_hour, end_hour)
                delay = (run_at - now).total_seconds()
                if delay > 0:
                    await asyncio.sleep(delay)

                if action_id not in self._actions:
                    break

                action.run_count += 1
                logger.info(
                    f"Running cyclic random-window action {action_id} "
                    f"(run {action.run_count}"
                    + (f"/{action.max_runs}" if action.max_runs else "")
                    + ")"
                )
                await send_callback(action.message, action.thread_id)

                if action.max_runs is not None and action.run_count >= action.max_runs:
                    if action_id in self._actions:
                        del self._actions[action_id]
                    break

                # If days_interval > 1, skip ahead extra days
                if days_interval > 1:
                    await asyncio.sleep((days_interval - 1) * 86400)

        except asyncio.CancelledError:
            logger.info(f"Cyclic random-window action {action_id} was cancelled")
            raise
        except Exception as e:
            logger.error(f"Error in cyclic random-window action {action_id}: {e}")
            if action_id in self._actions:
                del self._actions[action_id]


# Global instance
_cyclic_scheduler = CyclicActionScheduler()


def get_cyclic_scheduler() -> CyclicActionScheduler:
    """Get the global cyclic action scheduler instance."""
    return _cyclic_scheduler
