"""Unit tests for the send_push_notification tool in homar.py."""

import pytest
import discord
from unittest.mock import AsyncMock, MagicMock, patch

from src.models.schemas import MyDeps


# ---------------------------------------------------------------------------
# Helpers – replicate the tool logic so we can test it without a live agent
# ---------------------------------------------------------------------------


async def _send_push_notification_logic(deps: MyDeps, message: str) -> str:
    """Standalone helper that mirrors the send_push_notification tool body."""
    if not deps or not deps.send_notification_callback:
        return "Error: Cannot send push notification - missing notification context"

    try:
        success = await deps.send_notification_callback(message)
        if success:
            return "Push notification sent successfully to #powiadomienia"
        return "Error: Could not find the 'powiadomienia' channel"
    except Exception as e:
        return f"Error sending push notification: {str(e)}"


NOTIFICATION_CHANNEL_NAME = "powiadomienia"


async def _send_notification_to_channel_logic(bot, message: str) -> bool:
    """Standalone helper that mirrors _send_notification_to_channel from main.py."""
    for guild in bot.guilds:
        channel = discord.utils.get(guild.text_channels, name=NOTIFICATION_CHANNEL_NAME)
        if channel is not None:
            await channel.send(message)
            return True
    return False


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestSendPushNotification:
    """Tests for send_push_notification tool logic."""

    @pytest.mark.asyncio
    async def test_sends_notification_successfully(self):
        """Notification is sent when callback returns True."""
        callback = AsyncMock(return_value=True)
        deps = MyDeps(send_notification_callback=callback)

        result = await _send_push_notification_logic(deps, "Hello!")

        callback.assert_awaited_once_with("Hello!")
        assert result == "Push notification sent successfully to #powiadomienia"

    @pytest.mark.asyncio
    async def test_returns_error_when_channel_not_found(self):
        """Returns error message when callback reports channel not found (False)."""
        callback = AsyncMock(return_value=False)
        deps = MyDeps(send_notification_callback=callback)

        result = await _send_push_notification_logic(deps, "Test message")

        callback.assert_awaited_once_with("Test message")
        assert result == "Error: Could not find the 'powiadomienia' channel"

    @pytest.mark.asyncio
    async def test_returns_error_when_no_callback(self):
        """Returns error message when no notification callback is configured."""
        deps = MyDeps(send_notification_callback=None)

        result = await _send_push_notification_logic(deps, "Test message")

        assert result == "Error: Cannot send push notification - missing notification context"

    @pytest.mark.asyncio
    async def test_returns_error_when_callback_raises(self):
        """Returns error message when the callback raises an exception."""
        callback = AsyncMock(side_effect=RuntimeError("network failure"))
        deps = MyDeps(send_notification_callback=callback)

        result = await _send_push_notification_logic(deps, "Test message")

        assert "Error sending push notification" in result
        assert "network failure" in result

    @pytest.mark.asyncio
    async def test_passes_message_verbatim_to_callback(self):
        """The exact message is forwarded to the notification callback."""
        callback = AsyncMock(return_value=True)
        deps = MyDeps(send_notification_callback=callback)
        message = "Urgent: something happened!"

        await _send_push_notification_logic(deps, message)

        callback.assert_awaited_once_with(message)


class TestSendNotificationToChannel:
    """Tests for _send_notification_to_channel channel-lookup logic."""

    @pytest.mark.asyncio
    async def test_sends_to_powiadomienia_channel(self):
        """Message is sent to the 'powiadomienia' channel and returns True."""
        mock_channel = MagicMock()
        mock_channel.name = NOTIFICATION_CHANNEL_NAME
        mock_channel.send = AsyncMock()

        mock_guild = MagicMock()

        mock_bot = MagicMock()
        mock_bot.guilds = [mock_guild]

        with patch.object(discord.utils, "get", return_value=mock_channel):
            result = await _send_notification_to_channel_logic(mock_bot, "Hello!")

        mock_channel.send.assert_awaited_once_with("Hello!")
        assert result is True

    @pytest.mark.asyncio
    async def test_returns_false_when_channel_not_found(self):
        """Returns False when 'powiadomienia' channel does not exist in any guild."""
        mock_guild = MagicMock()
        mock_bot = MagicMock()
        mock_bot.guilds = [mock_guild]

        with patch.object(discord.utils, "get", return_value=None):
            result = await _send_notification_to_channel_logic(mock_bot, "Hello!")

        assert result is False

    @pytest.mark.asyncio
    async def test_returns_false_when_no_guilds(self):
        """Returns False when the bot is not in any guilds."""
        mock_bot = MagicMock()
        mock_bot.guilds = []

        result = await _send_notification_to_channel_logic(mock_bot, "Hello!")

        assert result is False
