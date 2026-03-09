"""Unit tests for image_generation_agent.py module."""

import pytest
from unittest.mock import MagicMock
from src.agents_as_tools.image_generation_agent import (
    IMAGE_GENERATION_DIRECT_PROMPT,
    get_system_prompt,
)
from src.models.schemas import MyDeps


def _make_ctx(mode: str) -> MagicMock:
    ctx = MagicMock()
    ctx.deps = MyDeps(mode=mode)
    return ctx


class TestGetSystemPrompt:
    """Test the get_system_prompt function for image_generation_agent."""

    @pytest.mark.asyncio
    async def test_standard_mode_uses_rpg_prompt(self):
        """Standard mode (RPG channel) should use the RPG-specific agent prompt."""
        ctx = _make_ctx("standard")
        result = await get_system_prompt(ctx)
        assert "sesji rpg" in result
        assert "{{guidelines}}" not in result

    @pytest.mark.asyncio
    async def test_horror_mode_uses_rpg_prompt(self):
        """Horror mode (RPG2 channel) should use the RPG-specific agent prompt."""
        ctx = _make_ctx("horror")
        result = await get_system_prompt(ctx)
        assert "sesji rpg" in result
        assert "{{guidelines}}" not in result

    @pytest.mark.asyncio
    async def test_direct_mode_uses_generic_prompt(self):
        """Direct mode (called from Homar tool) should use the generic prompt without RPG context."""
        ctx = _make_ctx("direct")
        result = await get_system_prompt(ctx)
        assert result == IMAGE_GENERATION_DIRECT_PROMPT
        assert "sesji rpg" not in result

    @pytest.mark.asyncio
    async def test_unknown_mode_uses_generic_prompt(self):
        """Any unrecognised mode should fall back to the generic prompt."""
        ctx = _make_ctx("unknown_mode")
        result = await get_system_prompt(ctx)
        assert result == IMAGE_GENERATION_DIRECT_PROMPT
        assert "sesji rpg" not in result
