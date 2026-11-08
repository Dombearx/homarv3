"""Toolset wrapper that keeps Homar working when an external MCP server is down."""

import asyncio
from dataclasses import dataclass, field
from typing import Any, Self

from loguru import logger
from pydantic_ai import RunContext
from pydantic_ai.toolsets import AbstractToolset, ToolsetTool, WrapperToolset


@dataclass
class OptionalToolset(WrapperToolset):
    """Treat a toolset that fails to connect or list tools as having no tools.

    The agent connects to every toolset when a run starts, deferred capabilities included, so
    without this one unreachable MCP server (e.g. an expired Google token) fails every request.
    """

    name: str = "toolset"
    connect_timeout: float = 10.0
    _entered: int = field(default=0, repr=False)

    async def __aenter__(self) -> Self:
        try:
            async with asyncio.timeout(self.connect_timeout):
                await self.wrapped.__aenter__()
            self._entered += 1
        except (Exception, TimeoutError) as e:
            logger.warning(f"{self.name} unavailable, continuing without it: {e!r}")
        return self

    async def __aexit__(self, *args: Any) -> bool | None:
        if self._entered:
            self._entered -= 1
            return await self.wrapped.__aexit__(*args)
        return None

    async def get_tools(self, ctx: RunContext) -> dict[str, ToolsetTool]:
        if not self._entered:
            return {}
        try:
            async with asyncio.timeout(self.connect_timeout):
                return await self.wrapped.get_tools(ctx)
        except (Exception, TimeoutError) as e:
            logger.warning(f"{self.name} tools unavailable: {e!r}")
            return {}


def optional(toolset: AbstractToolset, name: str) -> OptionalToolset:
    return OptionalToolset(toolset, name=name)
