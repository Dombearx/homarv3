"""Tests for the tool approval flow and approval-gated tools."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from pydantic_ai import DeferredToolRequests, DeferredToolResults, ToolCallPart

from src.homar import _handle_approvals, update_marvin
from src.models.schemas import MyDeps


def _requests() -> DeferredToolRequests:
    return DeferredToolRequests(
        calls=[],
        approvals=[
            ToolCallPart(tool_name="update_marvin", args={}, tool_call_id="call_1"),
        ],
    )


class TestHandleApprovals:
    """The in-run approval handler delegates to the Discord callback from deps."""

    @pytest.mark.asyncio
    async def test_delegates_to_callback(self):
        results = DeferredToolResults(approvals={"call_1": True})
        callback = AsyncMock(return_value=results)
        ctx = MagicMock()
        ctx.deps = MyDeps(approval_callback=callback)
        requests = _requests()

        assert await _handle_approvals(ctx, requests) is results
        callback.assert_awaited_once_with(requests)

    @pytest.mark.asyncio
    async def test_without_callback_lets_requests_bubble_up(self):
        ctx = MagicMock()
        ctx.deps = MyDeps()
        assert await _handle_approvals(ctx, _requests()) is None

    @pytest.mark.asyncio
    async def test_without_deps_lets_requests_bubble_up(self):
        ctx = MagicMock()
        ctx.deps = None
        assert await _handle_approvals(ctx, _requests()) is None


class TestUpdateMarvinTool:
    """Tests for the update_marvin tool (runs the update script on the host via SSH)."""

    def test_update_marvin_success(self):
        result_mock = MagicMock(returncode=0, stdout="Updated.\n")
        with patch("src.homar.subprocess.run", return_value=result_mock) as mock_run:
            result = update_marvin()

        assert "Remote update successful" in result
        assert "Updated." in result
        command = mock_run.call_args.args[0]
        assert command[0] == "ssh"
        assert command[-1] == "/home/domin/update_marvin.sh"

    def test_update_marvin_failure(self):
        result_mock = MagicMock(returncode=1, stdout="", stderr="Permission denied\n")
        with patch("src.homar.subprocess.run", return_value=result_mock):
            result = update_marvin()

        assert "failed" in result
        assert "Permission denied" in result

    def test_update_marvin_exception(self):
        with patch(
            "src.homar.subprocess.run", side_effect=FileNotFoundError("ssh not found")
        ):
            result = update_marvin()

        assert "error" in result
        assert "ssh not found" in result
