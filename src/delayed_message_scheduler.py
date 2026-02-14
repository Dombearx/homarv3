"""Scheduler for delayed Discord messages."""

import asyncio
from dataclasses import dataclass
from datetime import datetime, timedelta
from loguru import logger


@dataclass
class DelayedMessage:
    """Represents a message scheduled for delayed delivery."""

    message: str
    thread_id: int
    scheduled_time: datetime
    task: asyncio.Task | None = None


class DelayedMessageScheduler:
    """Manages scheduling and delivery of delayed Discord messages."""

    def __init__(self):
        self._scheduled_messages: dict[str, DelayedMessage] = {}
        self._message_counter = 0

    async def schedule_message(
        self, message: str, thread_id: int, delay_seconds: int, send_callback
    ) -> str:
        """
        Schedule a message to be sent after a delay.

        Args:
            message: The message content to send
            thread_id: The Discord thread ID to send the message to
            delay_seconds: How many seconds to wait before sending
            send_callback: Async function to call to send the message

        Returns:
            A unique identifier for this scheduled message
        """
        self._message_counter += 1
        message_id = f"delayed_{self._message_counter}"

        scheduled_time = datetime.now() + timedelta(seconds=delay_seconds)

        # Create the delayed message object
        delayed_msg = DelayedMessage(
            message=message, thread_id=thread_id, scheduled_time=scheduled_time
        )

        # Schedule the task
        task = asyncio.create_task(
            self._send_delayed_message(message_id, delay_seconds, send_callback)
        )
        delayed_msg.task = task

        self._scheduled_messages[message_id] = delayed_msg

        logger.info(
            f"Scheduled message {message_id} for thread {thread_id} "
            f"to be sent in {delay_seconds} seconds"
        )

        return message_id

    async def _send_delayed_message(
        self, message_id: str, delay_seconds: int, send_callback
    ):
        """Internal method to wait and then send the message."""
        try:
            # Wait for the specified delay
            await asyncio.sleep(delay_seconds)

            # Get the message details
            delayed_msg = self._scheduled_messages.get(message_id)
            if not delayed_msg:
                logger.warning(f"Message {message_id} not found in scheduler")
                return

            # Send the message using the callback
            logger.info(
                f"Sending delayed message {message_id} to thread {delayed_msg.thread_id}"
            )
            await send_callback(delayed_msg.message, delayed_msg.thread_id)

            # Clean up
            del self._scheduled_messages[message_id]

        except asyncio.CancelledError:
            logger.info(f"Delayed message {message_id} was cancelled")
            if message_id in self._scheduled_messages:
                del self._scheduled_messages[message_id]
        except Exception as e:
            logger.error(f"Error sending delayed message {message_id}: {e}")
            if message_id in self._scheduled_messages:
                del self._scheduled_messages[message_id]

    def cancel_message(self, message_id: str) -> bool:
        """
        Cancel a scheduled message.

        Args:
            message_id: The ID of the message to cancel

        Returns:
            True if the message was cancelled, False if not found
        """
        delayed_msg = self._scheduled_messages.get(message_id)
        if delayed_msg and delayed_msg.task:
            delayed_msg.task.cancel()
            logger.info(f"Cancelled delayed message {message_id}")
            return True
        return False

    def get_scheduled_messages(self) -> list[tuple[str, DelayedMessage]]:
        """Get all currently scheduled messages."""
        return list(self._scheduled_messages.items())


# Global instance
_scheduler = DelayedMessageScheduler()


def get_scheduler() -> DelayedMessageScheduler:
    """Get the global delayed message scheduler instance."""
    return _scheduler
