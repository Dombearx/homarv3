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

    def get_chat(self, chat_id: str) -> Chat:
        """Return a chat by its ID."""
        return next((chat for chat in self._chats if chat.chat_id == chat_id), None)
    
    def create_chat(self, chat_id: str) -> Chat:
        """Create a new chat."""
        new_chat = Chat(
            chat_id=chat_id,
            messages=[],
        )
        self._chats.append(new_chat)
        return new_chat

    def add_message(self, chat_id: str, message: Message) -> None:
        """Add a message to a chat."""
        chat = self.get_chat(chat_id)
        if chat:
            chat.messages.append(message) 
        else:
            # If chat does not exist, create it and add the message
            new_chat = self.create_chat(chat_id)
            new_chat.messages.append(message)


# create a module-level instance for easy import/use
db = Database()
