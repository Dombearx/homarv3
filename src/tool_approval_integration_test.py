"""Integration test demonstrating the tool approval flow."""

import pytest
from pydantic_ai import DeferredToolRequests, DeferredToolResults, ToolCallPart
from src.homar import approval_test_tool
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
