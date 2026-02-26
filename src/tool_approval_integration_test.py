"""Integration test demonstrating the tool approval flow."""

import pytest
from unittest.mock import patch, MagicMock
from pydantic_ai import DeferredToolRequests, DeferredToolResults, ToolCallPart
from src.homar import approval_test_tool, update_marvin
from src.models.schemas import MyDeps


class TestToolApprovalFlow:
    """Tests for the tool approval functionality."""

    def test_approval_test_tool_exists(self):
        """Verify the approval_test_tool function exists."""
        # Import the tool function directly
        from src.homar import approval_test_tool

        # Verify it's callable
        assert callable(approval_test_tool), "approval_test_tool should be callable"

        # Test direct call
        result = approval_test_tool("test_param")
        assert "successfully" in result.lower()
        assert "test_param" in result


class TestApprovalToolBehavior:
    """Test the behavior of tools with approval requirements."""

    def test_approval_tool_direct_call(self):
        """Test direct call to approval_test_tool (outside agent context)."""
        # This should work when called directly (bypasses approval since it's already approved)
        result = approval_test_tool("direct_call_test")

        assert "successfully" in result.lower()
        assert "direct_call_test" in result

    @pytest.mark.asyncio
    async def test_multiple_tools_requiring_approval(self):
        """Test scenario where multiple tools require approval."""
        deps = MyDeps()

        # This is a theoretical test - in practice we only have one approval tool
        # But the infrastructure should support multiple

        # Create a mock deferred request with multiple tools
        mock_deferred = DeferredToolRequests(
            calls=[],
            approvals=[
                ToolCallPart(
                    tool_name="approval_test_tool",
                    args={"test_parameter": "test1"},
                    tool_call_id="call_1",
                ),
                ToolCallPart(
                    tool_name="approval_test_tool",
                    args={"test_parameter": "test2"},
                    tool_call_id="call_2",
                ),
            ],
        )

        # Verify structure
        assert len(mock_deferred.approvals) == 2
        assert all(
            call.tool_name == "approval_test_tool" for call in mock_deferred.approvals
        )

        # Create approval results
        results = DeferredToolResults()
        results.approvals["call_1"] = True
        results.approvals["call_2"] = True

        assert len(results.approvals) == 2


class TestUpdateMarvinTool:
    """Tests for the update_marvin tool."""

    def test_update_marvin_exists(self):
        """Verify the update_marvin function exists and is callable."""
        assert callable(update_marvin)

    def test_update_marvin_success(self):
        """Test update_marvin when both commands succeed."""
        mock_git = MagicMock()
        mock_git.returncode = 0
        mock_git.stdout = "Already up to date.\n"

        mock_make = MagicMock()
        mock_make.returncode = 0
        mock_make.stdout = "Restarting service...\n"

        with patch("src.homar.subprocess.run", side_effect=[mock_git, mock_make]):
            result = update_marvin()

        assert "git pull" in result
        assert "Already up to date" in result
        assert "make restart" in result
        assert "Restarting service" in result

    def test_update_marvin_git_pull_failure(self):
        """Test update_marvin when git pull fails."""
        mock_git = MagicMock()
        mock_git.returncode = 1
        mock_git.stdout = ""
        mock_git.stderr = "fatal: not a git repository\n"

        with patch("src.homar.subprocess.run", return_value=mock_git):
            result = update_marvin()

        assert "git pull failed" in result
        assert "fatal: not a git repository" in result

    def test_update_marvin_make_restart_failure(self):
        """Test update_marvin when make restart fails."""
        mock_git = MagicMock()
        mock_git.returncode = 0
        mock_git.stdout = "Already up to date.\n"

        mock_make = MagicMock()
        mock_make.returncode = 1
        mock_make.stdout = ""
        mock_make.stderr = "make: *** [restart] Error 1\n"

        with patch("src.homar.subprocess.run", side_effect=[mock_git, mock_make]):
            result = update_marvin()

        assert "make restart failed" in result
        assert "make: *** [restart] Error 1" in result

    def test_update_marvin_git_pull_exception(self):
        """Test update_marvin when git pull raises an exception."""
        with patch("src.homar.subprocess.run", side_effect=FileNotFoundError("git not found")):
            result = update_marvin()

        assert "git pull error" in result
        assert "git not found" in result

    def test_update_marvin_make_restart_exception(self):
        """Test update_marvin when make restart raises an exception."""
        mock_git = MagicMock()
        mock_git.returncode = 0
        mock_git.stdout = "Already up to date.\n"

        with patch(
            "src.homar.subprocess.run",
            side_effect=[mock_git, FileNotFoundError("make not found")],
        ):
            result = update_marvin()

        assert "make restart error" in result
        assert "make not found" in result

    def test_update_marvin_uses_correct_directory(self):
        """Test that update_marvin runs commands in /Marvin directory."""
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = ""

        with patch("src.homar.subprocess.run", return_value=mock_result) as mock_run:
            update_marvin()

        calls = mock_run.call_args_list
        assert len(calls) == 2
        assert calls[0].kwargs["cwd"] == "/Marvin"
        assert calls[1].kwargs["cwd"] == "/Marvin"
        assert calls[0].args[0] == ["git", "pull"]
        assert calls[1].args[0] == ["make", "restart"]
