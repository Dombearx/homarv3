"""A minimal in-memory mock database for chats."""

from typing import Any
from pydantic import BaseModel
from enum import StrEnum, auto
from datetime import datetime
from src.models.schemas import Chat, ChatResponse, Message, Role


class Database:
    """Simple in-memory store for chats. Currently returns empty list."""

    def __init__(self) -> None:
        # store chats in a list during runtime
        self._chats: list[Chat] = []

    def get_chats(self) -> list[Chat]:
        """Return stored chats (empty by default)."""
        return ChatResponse(chats=list(self._chats))


# create a module-level instance for easy import/use
db = Database()

# populate with two mocked chats: one with 3 messages, one with 5 messages
_now = datetime.utcnow()

db._chats = [
    Chat(
        chat_id="chat-1",
        last_message_timestamp=_now,
        messages=[
            Message(timestamp=_now, message_id="c1-m1", chat_id="chat-1", content="Cześć, czy możesz mi pomóc z pogodą?", role=Role.USER),
            Message(timestamp=_now, message_id="c1-m2", chat_id="chat-1", content="Oczywiście — jaka lokalizacja Cię interesuje?", role=Role.ASSISTANT),
            Message(timestamp=_now, message_id="c1-m3", chat_id="chat-1", content="Warszawa, proszę.", role=Role.USER),
        ],
    ),
    Chat(
        chat_id="chat-2",
        last_message_timestamp=_now,
        messages=[
            Message(timestamp=_now, message_id="c2-m1", chat_id="chat-2", content="Hej, masz może przepis na risotto?", role=Role.USER),
            Message(timestamp=_now, message_id="c2-m2", chat_id="chat-2", content="Tak — lubisz grzyby czy wolisz wersję z warzywami?", role=Role.ASSISTANT),
            Message(timestamp=_now, message_id="c2-m3", chat_id="chat-2", content="Wersję z grzybami.", role=Role.USER),
            Message(timestamp=_now, message_id="c2-m4", chat_id="chat-2", content="Świetnie — najpierw podsmaż cebulę i czosnek, potem dodaj ryż...", role=Role.ASSISTANT),
            Message(timestamp=_now, message_id="c2-m5", chat_id="chat-2", content="Dzięki, spróbuję!", role=Role.USER),
        ],
    ),
]
