"""Google Calendar capability backed by the @cocal/google-calendar-mcp server."""

import os
import shutil

from dotenv import load_dotenv
from fastmcp.client.transports import StdioTransport
from pydantic_ai.capabilities import Capability
from pydantic_ai.mcp import MCPToolset

from src.capabilities.optional_toolset import optional

load_dotenv()

# Tools the assistant needs; the rest (colors, multi-account management, invitations) only
# add noise to the tool list.
GOOGLE_CALENDAR_TOOLS = {
    "list-calendars",
    "list-events",
    "search-events",
    "get-event",
    "create-event",
    "update-event",
    "delete-event",
    "get-freebusy",
}

# Installed globally in the Docker image; falls back to npx for local runs.
GOOGLE_CALENDAR_MCP_COMMAND = (
    ["google-calendar-mcp"]
    if shutil.which("google-calendar-mcp")
    else ["npx", "-y", "@cocal/google-calendar-mcp"]
)

google_calendar_mcp = MCPToolset(
    StdioTransport(
        GOOGLE_CALENDAR_MCP_COMMAND[0],
        GOOGLE_CALENDAR_MCP_COMMAND[1:],
        env={
            "GOOGLE_OAUTH_CREDENTIALS": os.getenv("GOOGLE_OAUTH_CREDENTIALS", ""),
            "GOOGLE_CALENDAR_MCP_TOKEN_PATH": os.getenv(
                "GOOGLE_CALENDAR_MCP_TOKEN_PATH", ""
            ),
            "PATH": os.environ.get("PATH", ""),
            "HOME": os.environ.get("HOME", ""),
        },
    ),
    id="google_calendar_mcp",
)
google_calendar_toolset = optional(
    google_calendar_mcp.filtered(
        lambda ctx, tool_def: tool_def.name in GOOGLE_CALENDAR_TOOLS
    ),
    "Google Calendar MCP",
)

GOOGLE_CALENDAR_INSTRUCTIONS = """
Zasady pracy z Google Calendar:
- Strefa czasowa to zawsze Europe/Warsaw. Daty i godziny względne ("jutro", "w piątek o 18") przeliczaj na podstawie aktualnej daty podanej w kontekście.
- Wydarzenia twórz w kalendarzu "primary", chyba że użytkownik wskaże inny.
- Jeśli brakuje godziny, a wydarzenie wyraźnie jej wymaga (spotkanie, wizyta), dopytaj. Wydarzenia bez godziny (urodziny, wyjazd) twórz jako całodniowe.
- Do zmiany lub usunięcia wydarzenia najpierw znajdź je (`search-events` / `list-events`), żeby mieć jego ID.
- Kalendarz to wydarzenia w czasie; zadania do zrobienia należą do Todoist.
"""

google_calendar = Capability(
    id="google_calendar",
    description=(
        "Google Calendar: wydarzenia, spotkania, wizyty, plan dnia/tygodnia, "
        "sprawdzanie wolnych terminów, dodawanie i zmiana wydarzeń."
    ),
    instructions=GOOGLE_CALENDAR_INSTRUCTIONS,
    toolsets=[google_calendar_toolset],
    defer_loading=True,
)
