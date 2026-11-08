"""Todoist capability: a small, purpose-built toolset on top of the Todoist API v1.

The official Todoist MCP server exposes ~50 tools (projects, workspaces, templates, stats...),
which made the model pick wrong tools - e.g. creating a project for a shopping list. These
tools cover only what Homar actually needs, and the shopping list shape (one parent task with
subtasks) is enforced in code instead of in the prompt.
"""

import os
from typing import Any, Literal

import httpx
from pydantic_ai import ModelRetry, RunContext
from pydantic_ai.capabilities import Capability

from src.models.schemas import MyDeps

TODOIST_API_URL = "https://api.todoist.com/api/v1"
DUE_LANG = "pl"
DEFAULT_SHOPPING_LIST_NAME = "Lista zakupów"

TODOIST_INSTRUCTIONS = """
Zasady pracy z Todoist:
- Lista zakupów (lub każda inna lista rzeczy do kupienia/zabrania) to ZAWSZE jedno zadanie nadrzędne z podzadaniami - nigdy projekt ani sekcja. Używaj `create_shopping_list`.
- Zanim stworzysz nową listę zakupów, sprawdź `find_tasks` (np. filtr "search: zakupy"), czy nie ma już otwartej listy. Jeśli jest, dopisz pozycje przez `add_items_to_list`, chyba że użytkownik wyraźnie chce nową listę.
- Pojedyncze zadania i przypomnienia twórz w Inbox (nie podawaj projektu), chyba że użytkownik wskaże projekt.
- Terminy podawaj w języku naturalnym po polsku w `due_string` (np. "jutro o 10", "w piątek", "co poniedziałek") - Todoist sam je zinterpretuje.
- Priorytety: 1 = najwyższy (p1), 4 = brak priorytetu. Nie ustawiaj priorytetu, jeśli użytkownik go nie podał.
- Do zmiany zadania potrzebujesz jego ID - najpierw znajdź je przez `find_tasks`.
- Nie twórz projektów, sekcji ani etykiet.
"""

todoist = Capability(
    id="todoist",
    description=(
        "Todoist: zadania, listy zakupów, rzeczy do zrobienia i zapamiętania, "
        "przypomnienia z terminem, odhaczanie i przeglądanie zadań."
    ),
    instructions=TODOIST_INSTRUCTIONS,
    defer_loading=True,
)


async def _request(method: str, path: str, **kwargs: Any) -> Any:
    headers = {"Authorization": f"Bearer {os.getenv('TODOIST_TOKEN')}"}
    async with httpx.AsyncClient(base_url=TODOIST_API_URL, timeout=30.0) as client:
        response = await client.request(method, path, headers=headers, **kwargs)
    if response.status_code >= 400:
        raise ModelRetry(
            f"Todoist API error {response.status_code} for {method} {path}: {response.text[:500]}"
        )
    if response.status_code == 204 or not response.content:
        return None
    return response.json()


async def _get_all(path: str, params: dict[str, Any] | None = None) -> list[dict]:
    """Fetch every page of a paginated Todoist v1 endpoint."""
    params = dict(params or {}, limit=200)
    results: list[dict] = []
    while True:
        page = await _request("GET", path, params=params)
        results.extend(page.get("results", []))
        cursor = page.get("next_cursor")
        if not cursor:
            return results
        params["cursor"] = cursor


async def _projects_by_id() -> dict[str, str]:
    return {p["id"]: p["name"] for p in await _get_all("/projects")}


async def _resolve_project_id(project_name: str) -> str:
    projects = await _projects_by_id()
    for project_id, name in projects.items():
        if name.lower() == project_name.lower():
            return project_id
    raise ModelRetry(
        f"Project '{project_name}' not found. Available projects: {', '.join(projects.values())}"
    )


def _format_task(task: dict, projects: dict[str, str] | None = None) -> str:
    parts = [f"[{task['id']}] {task['content']}"]
    if due := task.get("due"):
        parts.append(f"termin: {due.get('string') or due.get('date')}")
    if task.get("priority", 1) > 1:
        parts.append(f"p{5 - task['priority']}")
    if projects and task.get("project_id") in projects:
        parts.append(f"projekt: {projects[task['project_id']]}")
    if task.get("parent_id"):
        parts.append(f"podzadanie {task['parent_id']}")
    if task.get("description"):
        parts.append(f"opis: {task['description'][:200]}")
    return " | ".join(parts)


async def _add_subtasks(parent: dict, items: list[str]) -> list[dict]:
    created = []
    for item in items:
        created.append(
            await _request(
                "POST",
                "/tasks",
                json={
                    "content": item,
                    "parent_id": parent["id"],
                    "project_id": parent["project_id"],
                },
            )
        )
    return created


@todoist.tool(retries=2)
async def create_shopping_list(
    ctx: RunContext[MyDeps],
    items: list[str],
    name: str = DEFAULT_SHOPPING_LIST_NAME,
    due_string: str = "dzisiaj",
) -> str:
    """Create a shopping list: one parent task with every item as a subtask (in Inbox).

    Args:
        items: Items to buy, one per subtask, e.g. ["mleko 2l", "chleb", "jajka x10"].
        name: Name of the list, e.g. "Lista zakupów" or "Zakupy Castorama".
        due_string: Due date of the whole list in natural Polish language. Defaults to today.
    """
    if not items:
        raise ModelRetry("A shopping list needs at least one item.")
    parent = await _request(
        "POST",
        "/tasks",
        json={"content": name, "due_string": due_string, "due_lang": DUE_LANG},
    )
    await _add_subtasks(parent, items)
    return f"Utworzono listę '{name}' [{parent['id']}] z {len(items)} pozycjami: {', '.join(items)}"


@todoist.tool(retries=2)
async def add_items_to_list(
    ctx: RunContext[MyDeps], list_task_id: str, items: list[str]
) -> str:
    """Add items as subtasks to an existing list (e.g. an open shopping list).

    Args:
        list_task_id: ID of the parent task of the list (find it with `find_tasks`).
        items: Items to add, one per subtask.
    """
    parent = await _request("GET", f"/tasks/{list_task_id}")
    await _add_subtasks(parent, items)
    return f"Dodano do '{parent['content']}': {', '.join(items)}"


@todoist.tool(retries=2)
async def find_tasks(ctx: RunContext[MyDeps], query: str) -> str:
    """Find active tasks with a Todoist filter query.

    Args:
        query: Todoist filter syntax (English keywords), e.g. "today | overdue",
            "search: zakupy", "tomorrow", "next 7 days", "#Inbox", "p1", "no date".
    """
    tasks = await _get_all("/tasks/filter", {"query": query, "lang": "en"})
    if not tasks:
        return f"Brak zadań dla filtra '{query}'."
    projects = await _projects_by_id()
    return "\n".join(_format_task(task, projects) for task in tasks)


@todoist.tool(retries=2)
async def get_task(ctx: RunContext[MyDeps], task_id: str) -> str:
    """Get a task with its subtasks (e.g. to read the contents of a shopping list).

    Args:
        task_id: ID of the task.
    """
    task = await _request("GET", f"/tasks/{task_id}")
    subtasks = await _get_all("/tasks", {"parent_id": task_id})
    lines = [_format_task(task)]
    lines.extend(f"  - {_format_task(subtask)}" for subtask in subtasks)
    return "\n".join(lines)


@todoist.tool(retries=2)
async def add_task(
    ctx: RunContext[MyDeps],
    content: str,
    due_string: str | None = None,
    description: str | None = None,
    priority: Literal[1, 2, 3, 4] | None = None,
    project_name: str | None = None,
    parent_task_id: str | None = None,
) -> str:
    """Add a single task (to Inbox unless a project is given).

    Args:
        content: Task title.
        due_string: Due date in natural Polish language, e.g. "jutro o 18", "co piątek".
        description: Optional longer description.
        priority: 1 is the highest (p1), 4 means no priority.
        project_name: Existing project name; omit to use Inbox.
        parent_task_id: Make it a subtask of this task.
    """
    payload: dict[str, Any] = {"content": content}
    if due_string:
        payload |= {"due_string": due_string, "due_lang": DUE_LANG}
    if description:
        payload["description"] = description
    if priority:
        payload["priority"] = 5 - priority
    if project_name:
        payload["project_id"] = await _resolve_project_id(project_name)
    if parent_task_id:
        payload["parent_id"] = parent_task_id
    task = await _request("POST", "/tasks", json=payload)
    return f"Dodano: {_format_task(task)}"


@todoist.tool(retries=2)
async def update_task(
    ctx: RunContext[MyDeps],
    task_id: str,
    content: str | None = None,
    due_string: str | None = None,
    description: str | None = None,
    priority: Literal[1, 2, 3, 4] | None = None,
) -> str:
    """Change an existing task. Pass only the fields that change.

    Args:
        task_id: ID of the task.
        content: New title.
        due_string: New due date in natural Polish language, or "no date" to remove it.
        description: New description.
        priority: 1 is the highest (p1), 4 means no priority.
    """
    payload: dict[str, Any] = {}
    if content:
        payload["content"] = content
    if due_string:
        payload |= {"due_string": due_string, "due_lang": DUE_LANG}
    if description is not None:
        payload["description"] = description
    if priority:
        payload["priority"] = 5 - priority
    if not payload:
        raise ModelRetry("Nothing to update - pass at least one field.")
    task = await _request("POST", f"/tasks/{task_id}", json=payload)
    return f"Zaktualizowano: {_format_task(task)}"


@todoist.tool(retries=2)
async def complete_tasks(ctx: RunContext[MyDeps], task_ids: list[str]) -> str:
    """Mark tasks as done (recurring tasks move to their next date).

    Args:
        task_ids: IDs of the tasks to complete.
    """
    for task_id in task_ids:
        await _request("POST", f"/tasks/{task_id}/close")
    return f"Ukończono {len(task_ids)} zadań."


@todoist.tool(retries=2, requires_approval=True)
async def delete_task(ctx: RunContext[MyDeps], task_id: str) -> str:
    """Permanently delete a task with its subtasks. Prefer `complete_tasks` for finished tasks.

    Args:
        task_id: ID of the task.
    """
    await _request("DELETE", f"/tasks/{task_id}")
    return f"Usunięto zadanie {task_id}."


@todoist.tool(retries=2)
async def list_projects(ctx: RunContext[MyDeps]) -> str:
    """List the names of existing Todoist projects."""
    return ", ".join((await _projects_by_id()).values())
