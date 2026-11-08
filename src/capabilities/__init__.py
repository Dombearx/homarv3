"""Domain capabilities Homar loads on demand, filtered by the user's permissions."""

from pydantic_ai.capabilities import AbstractCapability

from src.capabilities.google_calendar import google_calendar
from src.capabilities.grocy import grocy
from src.capabilities.home_assistant import home_assistant
from src.capabilities.humblebundle import humblebundle
from src.capabilities.image_generation import image_generation
from src.capabilities.todoist import todoist
from src.models.schemas import GUEST_ALLOWED_CAPABILITIES, UserType

DOMAIN_CAPABILITIES: list[AbstractCapability] = [
    home_assistant,
    todoist,
    google_calendar,
    grocy,
    image_generation,
    humblebundle,
]


def get_domain_capabilities(user_type: UserType) -> list[AbstractCapability]:
    if user_type == UserType.GUEST:
        return [c for c in DOMAIN_CAPABILITIES if c.id in GUEST_ALLOWED_CAPABILITIES]
    return list(DOMAIN_CAPABILITIES)
