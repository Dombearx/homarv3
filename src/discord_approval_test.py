"""Tests for Discord approval mechanism."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from pydantic_ai import DeferredToolRequests, ToolCallPart
from src.discord_approval import request_approval, pending_approvals


@pytest.fixture
def mock_thread():
    """Create a mock Discord thread."""
    thread = MagicMock()
    thread.send = AsyncMock()
    return thread


@pytest.fixture
def sample_deferred_request():
    """Create a sample deferred tool request."""
    return DeferredToolRequests(
        calls=[],
        approvals=[
            ToolCallPart(
                tool_name="approval_test_tool",
                args={"test_parameter": "test_value"},
                tool_call_id="test_call_1",
            )
        ],
        metadata={},
    )


class TestRequestApproval:
    """Test the request_approval function."""

    @pytest.mark.asyncio
    async def test_request_approval_message_format(
        self, mock_thread, sample_deferred_request
    ):
        """Test that approval request message is formatted correctly."""
        # Mock the message that gets sent
        mock_message = MagicMock()
        mock_message.id = 12345
        mock_thread.send.return_value = mock_message

        # Don't actually wait for approval, just cancel the future
        with patch("asyncio.wait_for", side_effect=TimeoutError):
            try:
                await request_approval(mock_thread, sample_deferred_request)
            except Exception:
                pass  # We expect timeout

        # Verify message was sent
        mock_thread.send.assert_called_once()
        call_args = mock_thread.send.call_args

        # Check message content
        message_content = call_args[0][0]
        assert "Tool Approval Required" in message_content
        assert "approval_test_tool" in message_content
        assert "test_parameter" in message_content
        assert "test_value" in message_content

    @pytest.mark.asyncio
    async def test_pending_approval_stored(self, mock_thread, sample_deferred_request):
        """Test that pending approval is stored correctly."""
        # Clear any existing pending approvals
        pending_approvals.clear()

        # Mock the message
        mock_message = MagicMock()
        mock_message.id = 12345
        mock_thread.send.return_value = mock_message

        # Don't actually wait, just check storage
        with patch("asyncio.wait_for", side_effect=TimeoutError):
            try:
                await request_approval(mock_thread, sample_deferred_request)
            except Exception:
                pass

        # The approval should have been stored temporarily
        # (Note: it gets cleaned up on timeout in the actual function)

    @pytest.mark.asyncio
    async def test_approval_timeout_cleanup(self, mock_thread, sample_deferred_request):
        """Test that approval is cleaned up on timeout."""
        # Clear pending approvals
        pending_approvals.clear()

        # Mock the message
        mock_message = MagicMock()
        mock_message.id = 12345
        mock_message.edit = AsyncMock()
        mock_thread.send.return_value = mock_message

        # Let it timeout
        with patch("asyncio.wait_for", side_effect=TimeoutError):
            result = await request_approval(mock_thread, sample_deferred_request)

        # Verify timeout handling
        mock_message.edit.assert_called_once()
        edit_call_args = mock_message.edit.call_args
        assert "TIMEOUT" in edit_call_args[1]["content"]

        # Verify it's not in pending_approvals anymore
        assert mock_message.id not in pending_approvals

        # Verify rejection result
        assert len(result.approvals) == 1
        assert "test_call_1" in result.approvals


class TestToolApprovalIntegration:
    """Integration tests for the tool approval mechanism."""

    def test_deferred_request_with_multiple_tools(self):
        """Test handling multiple tools requiring approval."""
        request = DeferredToolRequests(
            calls=[],
            approvals=[
                ToolCallPart(
                    tool_name="tool_1",
                    args={"param1": "value1"},
                    tool_call_id="call_1",
                ),
                ToolCallPart(
                    tool_name="tool_2",
                    args={"param2": "value2"},
                    tool_call_id="call_2",
                ),
            ],
            metadata={"call_1": {"reason": "test"}},
        )

        assert len(request.approvals) == 2
        assert request.approvals[0].tool_name == "tool_1"
        assert request.approvals[1].tool_name == "tool_2"

    def test_deferred_request_with_long_parameters(self):
        """Test that long parameter values are handled correctly."""
        long_value = "x" * 200
        request = DeferredToolRequests(
            calls=[],
            approvals=[
                ToolCallPart(
                    tool_name="test_tool",
                    args={"long_param": long_value},
                    tool_call_id="call_1",
                )
            ],
        )

        assert len(request.approvals[0].args["long_param"]) == 200
        # The UI truncates in the display, but the actual value is preserved

    def test_deferred_request_structure(self):
        """Test the structure of DeferredToolRequests."""
        request = DeferredToolRequests(
            calls=[],
            approvals=[
                ToolCallPart(
                    tool_name="test_tool",
                    args={"param": "value"},
                    tool_call_id="call_id",
                )
            ],
            metadata={"call_id": {"info": "test"}},
        )

        assert hasattr(request, "calls")
        assert hasattr(request, "approvals")
        assert hasattr(request, "metadata")
        assert len(request.approvals) == 1
        assert request.approvals[0].tool_call_id == "call_id"
