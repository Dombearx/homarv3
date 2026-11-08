"""Tests for Homar's on-demand capabilities and the Todoist toolset."""

import importlib
from unittest.mock import AsyncMock, patch

import pytest
from pydantic_ai import ModelMessage, ModelResponse, TextPart, ToolCallPart
from pydantic_ai.models.function import AgentInfo, FunctionModel

from src.capabilities import DOMAIN_CAPABILITIES
from src.homar import _capabilities_for, homar
from src.models.schemas import MyDeps, UserType

# `src.capabilities.todoist` is shadowed by the re-exported capability object
todoist_module = importlib.import_module("src.capabilities.todoist")


class TestDomainCapabilities:
    def test_all_domain_capabilities_are_deferred_with_description(self):
        for capability in DOMAIN_CAPABILITIES:
            assert capability.defer_loading, capability.id
            assert capability.description, capability.id

    def test_capability_ids_are_unique(self):
        ids = [c.id for c in DOMAIN_CAPABILITIES]
        assert len(ids) == len(set(ids))


class TestProgressiveDisclosure:
    """Domain tools stay hidden until the model loads their capability."""

    @pytest.mark.asyncio
    async def test_todoist_tools_appear_only_after_load(self):
        seen_tool_names: list[set[str]] = []

        def model(messages: list[ModelMessage], info: AgentInfo) -> ModelResponse:
            seen_tool_names.append({t.name for t in info.function_tools})
            if len(seen_tool_names) == 1:
                return ModelResponse(
                    parts=[
                        ToolCallPart(
                            tool_name="load_capability", args={"id": "todoist"}
                        )
                    ]
                )
            return ModelResponse(parts=[TextPart("ok")])

        deps = MyDeps(user_type=UserType.DEFAULT)
        # Only Todoist: the other capabilities would connect to real services.
        capabilities = [
            c for c in _capabilities_for(deps) if c.id in ("todoist", "maintenance")
        ]
        result = await homar.run(
            "dodaj mleko do listy zakupów",
            deps=deps,
            model=FunctionModel(model),
            capabilities=capabilities,
        )

        assert result.output == "ok"
        first, second = seen_tool_names
        assert "load_capability" in first
        assert "create_shopping_list" not in first
        assert "send_delayed_message" in first
        assert "create_shopping_list" in second


class TestTodoistShoppingList:
    @pytest.mark.asyncio
    async def test_creates_parent_task_with_subtasks(self):
        parent = {"id": "p1", "project_id": "inbox", "content": "Lista zakupów"}
        request = AsyncMock(side_effect=[parent, {}, {}])

        with patch.object(todoist_module, "_request", request):
            result = await todoist_module.create_shopping_list(
                None, ["mleko", "chleb"]
            )

        parent_call, *item_calls = request.await_args_list
        assert parent_call.args == ("POST", "/tasks")
        assert parent_call.kwargs["json"]["content"] == "Lista zakupów"
        assert parent_call.kwargs["json"]["due_string"] == "dzisiaj"
        assert [c.kwargs["json"] for c in item_calls] == [
            {"content": "mleko", "parent_id": "p1", "project_id": "inbox"},
            {"content": "chleb", "parent_id": "p1", "project_id": "inbox"},
        ]
        # Subtasks never get a due date
        assert all("due_string" not in c.kwargs["json"] for c in item_calls)
        assert "2 pozycjami" in result

    @pytest.mark.asyncio
    async def test_add_task_maps_priority_and_project(self):
        request = AsyncMock(
            side_effect=[
                {"results": [{"id": "proj1", "name": "Dom"}], "next_cursor": None},
                {"id": "t1", "content": "Umyć okna", "priority": 4},
            ]
        )

        with patch.object(todoist_module, "_request", request):
            await todoist_module.add_task(
                None, "Umyć okna", due_string="jutro", priority=1, project_name="dom"
            )

        payload = request.await_args_list[-1].kwargs["json"]
        assert payload == {
            "content": "Umyć okna",
            "due_string": "jutro",
            "due_lang": "pl",
            "priority": 4,
            "project_id": "proj1",
        }
