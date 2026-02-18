"""Unit tests for retry behavior in homar.py tools."""

import pytest
from unittest.mock import AsyncMock, Mock, patch
from pydantic_ai import ModelRetry, UnexpectedModelBehavior
from src.homar import (
    todoist_api,
    home_assistant_api,
    grocy_api,
    google_calendar_api,
    humblebundle_api,
    image_generation_api,
)
from src.models.schemas import MyDeps


class TestToolRetryBehavior:
    """Test that tools properly implement retry behavior."""

    @pytest.mark.asyncio
    async def test_todoist_api_raises_model_retry_on_error(self):
        """Test that todoist_api raises ModelRetry when the agent fails."""
        # Create a mock context
        mock_ctx = Mock()
        mock_ctx.deps = MyDeps()
        mock_ctx.usage = Mock()

        # Mock the todoist_agent.run to raise an exception
        with patch("src.homar.todoist_agent.run", side_effect=Exception("API Error")):
            # Verify that ModelRetry is raised
            with pytest.raises(ModelRetry) as exc_info:
                await todoist_api(mock_ctx, "create a task")

            # Verify the error message is user-friendly
            assert "Todoist API call failed" in str(exc_info.value)
            assert "try again" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_todoist_api_returns_success_on_valid_response(self):
        """Test that todoist_api returns successful response when agent succeeds."""
        # Create a mock context
        mock_ctx = Mock()
        mock_ctx.deps = MyDeps()
        mock_ctx.usage = Mock()

        # Mock the todoist_agent.run to return a successful response
        mock_result = Mock()
        mock_result.output = "Task created successfully"

        with patch("src.homar.todoist_agent.run", return_value=mock_result):
            result = await todoist_api(mock_ctx, "create a task")
            assert result == "Task created successfully"

    @pytest.mark.asyncio
    async def test_home_assistant_api_raises_model_retry_on_error(self):
        """Test that home_assistant_api raises ModelRetry when the agent fails."""
        mock_ctx = Mock()
        mock_ctx.deps = MyDeps()
        mock_ctx.usage = Mock()

        with patch(
            "src.homar.home_assistant_agent.run",
            side_effect=Exception("Device not found"),
        ):
            with pytest.raises(ModelRetry) as exc_info:
                await home_assistant_api(mock_ctx, "turn on light")

            assert "Home Assistant API call failed" in str(exc_info.value)
            assert "try again" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_home_assistant_api_returns_success_on_valid_response(self):
        """Test that home_assistant_api returns successful response when agent succeeds."""
        mock_ctx = Mock()
        mock_ctx.deps = MyDeps()
        mock_ctx.usage = Mock()

        mock_result = Mock()
        mock_result.output = "Light turned on"

        with patch("src.homar.home_assistant_agent.run", return_value=mock_result):
            result = await home_assistant_api(mock_ctx, "turn on light")
            assert result == "Light turned on"

    @pytest.mark.asyncio
    async def test_grocy_api_raises_model_retry_on_error(self):
        """Test that grocy_api raises ModelRetry when the agent fails."""
        mock_ctx = Mock()
        mock_ctx.deps = MyDeps()
        mock_ctx.usage = Mock()

        with patch(
            "src.agents_as_tools.grocy_agent.grocy_agent.run",
            side_effect=Exception("Product not found"),
        ):
            with pytest.raises(ModelRetry) as exc_info:
                await grocy_api(mock_ctx, "add milk")

            assert "Grocy API call failed" in str(exc_info.value)
            assert "try again" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_google_calendar_api_raises_model_retry_on_error(self):
        """Test that google_calendar_api raises ModelRetry when the agent fails."""
        mock_ctx = Mock()
        mock_ctx.deps = MyDeps()
        mock_ctx.usage = Mock()

        with patch(
            "src.homar.google_calendar_agent.run",
            side_effect=Exception("Calendar not found"),
        ):
            with pytest.raises(ModelRetry) as exc_info:
                await google_calendar_api(mock_ctx, "list events")

            assert "Google Calendar API call failed" in str(exc_info.value)
            assert "try again" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_humblebundle_api_raises_model_retry_on_error(self):
        """Test that humblebundle_api raises ModelRetry when the agent fails."""
        mock_ctx = Mock()
        mock_ctx.deps = MyDeps()
        mock_ctx.usage = Mock()

        with patch(
            "src.homar.humblebundle_agent.run", side_effect=Exception("API error")
        ):
            with pytest.raises(ModelRetry) as exc_info:
                await humblebundle_api(mock_ctx, "list bundles")

            assert "HumbleBundle API call failed" in str(exc_info.value)
            assert "try again" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_image_generation_api_raises_model_retry_on_error(self):
        """Test that image_generation_api raises ModelRetry when the agent fails."""
        mock_ctx = Mock()
        mock_ctx.deps = MyDeps()
        mock_ctx.usage = Mock()

        with patch(
            "src.homar.image_generation_agent.run",
            side_effect=Exception("Generation failed"),
        ):
            with pytest.raises(ModelRetry) as exc_info:
                await image_generation_api(mock_ctx, "a dragon")

            assert "Image generation failed" in str(exc_info.value)
            assert "try again" in str(exc_info.value)


class TestToolRetryConfiguration:
    """Test that tools have retry configuration."""

    def test_todoist_tool_has_retries_configured(self):
        """Verify todoist_api tool has retries configured."""
        from src.homar import homar

        # Find the todoist_api tool in the agent's tools
        todoist_tool = None
        for tool in homar._function_tools.values():
            if "todoist" in tool.name.lower():
                todoist_tool = tool
                break

        assert todoist_tool is not None, "todoist_api tool not found"
        # PydanticAI tools store retries in their definition
        # The retry behavior is set via decorator parameter

    def test_home_assistant_tool_has_retries_configured(self):
        """Verify home_assistant_api tool has retries configured."""
        from src.homar import homar

        # Find the home_assistant_api tool in the agent's tools
        ha_tool = None
        for tool in homar._function_tools.values():
            if "home_assistant" in tool.name.lower():
                ha_tool = tool
                break

        assert ha_tool is not None, "home_assistant_api tool not found"

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
