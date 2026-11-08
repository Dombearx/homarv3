"""Grocy capability: home groceries stock management."""

import asyncio

from loguru import logger
from pydantic_ai import RunContext
from pydantic_ai.capabilities import Capability

from src.grocy_mcp.grocy_mcp import (
    add_stock,
    consume_stock,
    create_product,
    list_locations,
    list_products,
    list_quantity_units,
    list_stock_entries,
    list_stocks,
    open_stock,
)
from src.models.schemas import MyDeps

GROCY_INSTRUCTIONS = """
Zasady pracy z Grocy (stan zapasów w domu):
- Używaj Grocy, gdy użytkownik mówi, że coś kupił, włożył do lodówki, otworzył, zjadł lub zużył, albo pyta, co jest w domu i co się kończy.
- Domyślna lokalizacja to lodówka, chyba że wynika inaczej.
- Produkt to tylko typ (np. "Mleko"); stan to konkretne partie z ilością, datą ważności i informacją o otwarciu.
- Nazwy produktów zawsze po polsku. Najpierw dopasuj do istniejącego produktu z listy poniżej; nowy produkt twórz tylko, gdy żaden nie pasuje.
- Datę ważności podawaj, jeśli użytkownik ją zna; "never expiring" tylko gdy wyraźnie tak powie.
"""

grocy = Capability(
    id="grocy",
    description=(
        "Grocy: stan zapasów jedzenia w domu - co kupiono, włożono do lodówki, "
        "otwarto, zjedzono, co się kończy lub psuje."
    ),
    instructions=GROCY_INSTRUCTIONS,
    tools=[
        create_product,
        list_stocks,
        add_stock,
        consume_stock,
        open_stock,
        list_stock_entries,
    ],
    defer_loading=True,
)


def _grocy_reference_data() -> str:
    return f"{list_locations()}\n\n{list_quantity_units()}\n\n{list_products()}"


@grocy.instructions
async def grocy_reference_data(ctx: RunContext[MyDeps]) -> str:
    try:
        return await asyncio.to_thread(_grocy_reference_data)
    except Exception as e:
        logger.warning(f"Could not fetch Grocy reference data: {e}")
        return "Lista lokalizacji, jednostek i produktów jest chwilowo niedostępna."
