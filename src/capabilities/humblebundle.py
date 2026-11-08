"""HumbleBundle capability: current game, book and software bundles."""

from pydantic_ai.capabilities import Capability

from src.integrations.humblebundle import get_bundle_details, list_bundles

HUMBLEBUNDLE_INSTRUCTIONS = """
Zasady pracy z HumbleBundle:
- Przy liście bundli podawaj nazwę, typ i link; przy szczegółach także progi cenowe i zawartość, jeśli są dostępne.
- Zawsze dołącz bezpośredni link do bundla.
"""

humblebundle = Capability(
    id="humblebundle",
    description="HumbleBundle: aktualne zestawy (bundle) gier, książek i oprogramowania, ich ceny i zawartość.",
    instructions=HUMBLEBUNDLE_INSTRUCTIONS,
    tools=[list_bundles, get_bundle_details],
    defer_loading=True,
)
