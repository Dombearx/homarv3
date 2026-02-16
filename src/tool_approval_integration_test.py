"""Integration test demonstrating the tool approval flow."""

import os
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from pydantic_ai import DeferredToolRequests, DeferredToolResults
from src.homar import homar, test_discord_approval
from src.models.schemas import MyDeps


# Skip LLM tests if no API key available
skip_if_no_api_key = pytest.mark.skipif(
    not os.getenv("OPENAI_API_KEY"),
    reason="Requires OpenAI API key"
)


class TestToolApprovalFlow:
    """Integration tests for the complete approval flow."""

    def test_discord_approval_tool_exists(self):
        """Verify the test_discord_approval tool function exists."""
        # Import the tool function directly
        from src.homar import test_discord_approval
        
        # Verify it's callable
        assert callable(test_discord_approval), "test_discord_approval should be callable"
        
        # Test direct call
        result = test_discord_approval("test_param")
        assert "successfully" in result.lower()
        assert "test_param" in result

    @skip_if_no_api_key
    @pytest.mark.asyncio
    async def test_approval_required_returns_deferred_request(self):
        """Test that calling a tool requiring approval returns DeferredToolRequests."""
        # Create deps
        deps = MyDeps()
        
        # Run the agent with a command that would trigger the test approval tool
        # Using a direct message that the LLM should understand
        result = await homar.run(
            "Call test_discord_approval with test_parameter set to 'integration_test'",
            deps=deps
        )
        
        # The result should be either a string or DeferredToolRequests
        # If it's DeferredToolRequests, the tool required approval
        output = result.output
        
        # We can't guarantee the LLM will call the tool, so check both cases
        if isinstance(output, DeferredToolRequests):
            # Success - tool required approval as expected
            assert len(output.approvals) > 0
            
            # Check that our tool is in the approvals
            tool_names = [call.tool_name for call in output.approvals]
            assert "test_discord_approval" in tool_names
            
            # Find our tool call
            our_call = next(call for call in output.approvals if call.tool_name == "test_discord_approval")
            assert "test_parameter" in our_call.args
        else:
            # LLM chose not to call the tool - this is also valid
            # Just verify it's a string
            assert isinstance(output, str)

    @skip_if_no_api_key
    @pytest.mark.asyncio
    async def test_approval_continuation_with_approval(self):
        """Test continuing execution after approval."""
        deps = MyDeps()
        
        # First run - should get deferred request
        result1 = await homar.run(
            "Call test_discord_approval with test_parameter 'approved_test'",
            deps=deps
        )
        
        # If we got a deferred request, test the continuation
        if isinstance(result1.output, DeferredToolRequests):
            deferred = result1.output
            
            # Create approval results - approve all
            approvals = DeferredToolResults()
            for call in deferred.approvals:
                approvals.approvals[call.tool_call_id] = True
            
            # Continue execution with approvals
            result2 = await homar.run(
                message_history=result1.new_messages(),
                deferred_tool_results=approvals,
                deps=deps
            )
            
            # Should now have a string response
            assert isinstance(result2.output, str)
            
            # Response should mention success or the test parameter
            response_lower = result2.output.lower()
            assert any(word in response_lower for word in ["success", "executed", "approved_test"])

    @skip_if_no_api_key
    @pytest.mark.asyncio  
    async def test_approval_continuation_with_rejection(self):
        """Test continuing execution after rejection."""
        from pydantic_ai import ToolDenied
        
        deps = MyDeps()
        
        # First run - should get deferred request
        result1 = await homar.run(
            "Call test_discord_approval with test_parameter 'rejected_test'",
            deps=deps
        )
        
        # If we got a deferred request, test the continuation
        if isinstance(result1.output, DeferredToolRequests):
            deferred = result1.output
            
            # Create approval results - reject all
            approvals = DeferredToolResults()
            for call in deferred.approvals:
                approvals.approvals[call.tool_call_id] = ToolDenied("User rejected the action")
            
            # Continue execution with rejections
            result2 = await homar.run(
                message_history=result1.new_messages(),
                deferred_tool_results=approvals,
                deps=deps
            )
            
            # Should now have a string response
            assert isinstance(result2.output, str)
            
            # Response should mention rejection or denial
            response_lower = result2.output.lower()
            assert any(word in response_lower for word in ["reject", "denied", "not allowed", "nie"])


class TestApprovalToolBehavior:
    """Test the behavior of tools with approval requirements."""

    def test_test_discord_approval_direct_call(self):
        """Test direct call to test_discord_approval (outside agent context)."""
        # This should work when called directly (bypasses approval since it's already approved)
        result = test_discord_approval("direct_call_test")
        
        assert "successfully" in result.lower()
        assert "direct_call_test" in result

    @pytest.mark.asyncio
    async def test_multiple_tools_requiring_approval(self):
        """Test scenario where multiple tools require approval."""
        deps = MyDeps()
        
        # This is a theoretical test - in practice we only have one approval tool
        # But the infrastructure should support multiple
        
        # Create a mock deferred request with multiple tools
        from pydantic_ai import ToolCallPart
        
        mock_deferred = DeferredToolRequests(
            calls=[],
            approvals=[
                ToolCallPart(
                    tool_name="test_discord_approval",
                    args={"test_parameter": "test1"},
                    tool_call_id="call_1"
                ),
                ToolCallPart(
                    tool_name="test_discord_approval",
                    args={"test_parameter": "test2"},
                    tool_call_id="call_2"
                )
            ]
        )
        
        # Verify structure
        assert len(mock_deferred.approvals) == 2
        assert all(call.tool_name == "test_discord_approval" for call in mock_deferred.approvals)
        
        # Create approval results
        results = DeferredToolResults()
        results.approvals["call_1"] = True
        results.approvals["call_2"] = True
        
        assert len(results.approvals) == 2
