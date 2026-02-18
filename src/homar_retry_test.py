"""Unit tests for retry behavior in homar.py tools."""

import pytest
from unittest.mock import Mock, patch
from pydantic_ai import ModelRetry
from src.homar import home_assistant_api
from src.models.schemas import MyDeps


class TestToolRetryBehavior:
    """Test that tools properly implement retry behavior."""

    @pytest.mark.asyncio
    async def test_tool_raises_model_retry_on_error(self):
        """Test that API tools raise ModelRetry when the agent fails."""
        # Create a mock context
        mock_ctx = Mock()
        mock_ctx.deps = MyDeps()
        mock_ctx.usage = Mock()

        # Mock the home_assistant_agent.run to raise an exception
        with patch(
            "src.homar.home_assistant_agent.run",
            side_effect=Exception("Device not found"),
        ):
            # Verify that ModelRetry is raised
            with pytest.raises(ModelRetry) as exc_info:
                await home_assistant_api(mock_ctx, "turn on light")

            # Verify the error message is user-friendly and includes retry guidance
            assert "Home Assistant API call failed" in str(exc_info.value)
            assert "try again" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_tool_returns_success_on_valid_response(self):
        """Test that API tools return successful response when agent succeeds."""
        # Create a mock context
        mock_ctx = Mock()
        mock_ctx.deps = MyDeps()
        mock_ctx.usage = Mock()

        # Mock the home_assistant_agent.run to return a successful response
        mock_result = Mock()
        mock_result.output = "Light turned on"

        with patch("src.homar.home_assistant_agent.run", return_value=mock_result):
            result = await home_assistant_api(mock_ctx, "turn on light")
            assert result == "Light turned on"


class TestToolRetryConfiguration:
    """Test that tools have retry configuration."""

    def test_all_api_tools_exist(self):
        """Verify all API tools are registered with the agent."""
        from src.homar import homar

        tool_names = [tool.name for tool in homar._function_tools.values()]

        # Check that key API tools exist
        expected_tools = [
            "todoist_api",
            "home_assistant_api",
            "grocy_api",
            "google_calendar_api",
            "humblebundle_api",
            "image_generation_api",
        ]

        for expected_tool in expected_tools:
            assert any(expected_tool in name for name in tool_names), (
                f"{expected_tool} not found in registered tools"
            )
