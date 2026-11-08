"""Home Assistant capability backed by the Home Assistant MCP server (Assist API)."""

import asyncio
import os

from dotenv import load_dotenv
from loguru import logger
from pydantic_ai import RunContext
from pydantic_ai.capabilities import Capability
from pydantic_ai.mcp import MCPToolset

from src.capabilities.optional_toolset import optional
from src.models.schemas import MyDeps

load_dotenv()

# HassCancelAllTimers only affects voice-satellite timers and GetDateTime duplicates the date
# Homar already has in its instructions.
HIDDEN_HOME_ASSISTANT_TOOLS = {"HassCancelAllTimers", "GetDateTime"}

home_assistant_mcp = MCPToolset(
    os.getenv("HOME_ASSISTANT_MCP_URL", "http://192.168.50.30:8123/mcp_server/sse"),
    id="home_assistant_mcp",
    headers={"Authorization": f"Bearer {os.getenv('HOME_ASSISTANT_TOKEN')}"},
)
home_assistant_toolset = optional(
    home_assistant_mcp.filtered(
        lambda ctx, tool_def: tool_def.name not in HIDDEN_HOME_ASSISTANT_TOOLS
    ),
    "Home Assistant MCP",
)

HOME_ASSISTANT_INSTRUCTIONS = """
Zasady sterowania domem (Home Assistant):
- Sterujesz wyłącznie urządzeniami wymienionymi w aktualnym stanie domu poniżej. Jeśli użytkownik prosi o urządzenie, którego tam nie ma, powiedz krótko, że nie masz do niego dostępu - nie zgaduj i nie proponuj obejść.
- Parametry narzędzi Hass*: `name` to dokładna nazwa lub alias urządzenia z listy poniżej (po polsku, jak w liście); `area` to nazwa pomieszczenia (Salon, Sypialnia, Przedpokój, Biuro, Kuchnia...); `domain` zawęża typ, np. ["light"].
- Jedno urządzenie: podaj `name`. Wszystkie światła w pomieszczeniu: `area` + `domain: ["light"]` (bez `name`). Wszystkie światła w domu: samo `domain: ["light"]`.
- Kolor i jasność: `HassLightSet` (`color` po angielsku, np. "red"; `brightness` 0-100; `temperature` w kelwinach).
- Do budzika świetlnego i klimatyzacji na czas używaj dedykowanych skryptów-narzędzi zamiast ręcznego ustawiania encji.
- Jeśli nazwa jest niejednoznaczna, a pomieszczenia nie da się wywnioskować z kontekstu - dopytaj.
- Urządzenia ze stanem `unavailable` są offline - nie próbuj nimi sterować, poinformuj o tym.
- Do pytań o stan urządzeń wystarczy kontekst poniżej; `GetLiveContext` wywołuj tylko, gdy potrzebujesz świeżego stanu po wykonaniu akcji.
- Po wykonaniu akcji potwierdź jednym zdaniem, co zrobiłeś.
"""

home_assistant = Capability(
    id="home_assistant",
    description=(
        "Home Assistant: sterowanie domem - światła (kolory, jasność), lampki, "
        "telewizor (głośność, pauza), klimatyzacja (też na czas), budzik świetlny, "
        "włączanie komputera; stan urządzeń."
    ),
    instructions=HOME_ASSISTANT_INSTRUCTIONS,
    toolsets=[home_assistant_toolset],
    defer_loading=True,
)


@home_assistant.instructions
async def current_home_state(ctx: RunContext[MyDeps]) -> str:
    """Inject the current state of exposed devices so the model needs no extra tool call."""
    try:
        async with asyncio.timeout(10):
            result = await home_assistant_mcp.direct_call_tool("GetLiveContext", {})
    except (Exception, TimeoutError) as e:
        logger.warning(f"Could not fetch Home Assistant live context: {e}")
        return "Aktualny stan domu jest niedostępny - użyj narzędzia GetLiveContext."
    if isinstance(result, dict):
        result = result.get("result", result)
    return f"Aktualny stan domu:\n{result}"
