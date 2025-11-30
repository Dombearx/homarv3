"""JSON-backed database for chats.

Stores chats in a single JSON file. Messages are serialized using
`pydantic_core.to_jsonable_python` and deserialized with
`pydantic_ai.ModelMessagesTypeAdapter.validate_python` so `ModelMessage`
instances are preserved.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from threading import Lock

from pydantic_core import to_jsonable_python
from pydantic_ai import ModelMessagesTypeAdapter

from src.models.schemas import Chat, ChatResponse, Message


DEFAULT_DB_DIR = Path(__file__).parent.parent / "data" / "chats"


class DatabaseJson:
    """Per-chat JSON files database.

    Each chat is stored in `data/chats/<safe_chat_id>.json` with structure:
      {"chat_id": str, "messages": <jsonable messages>}

    Serialization uses `to_jsonable_python` and deserialization uses
    `ModelMessagesTypeAdapter.validate_python` to recover `ModelMessage` objects.
    """

    def __init__(self, dir_path: Path | str = DEFAULT_DB_DIR) -> None:
        self.dir = Path(dir_path)
        self.dir.mkdir(parents=True, exist_ok=True)
        self._lock = Lock()

    def _safe_filename(self, chat_id: str) -> str:
        # Keep filename simple: allow alnum and limited set, else hex fallback
        safe = "".join(c for c in chat_id if (c.isalnum() or c in "-_"))
        if not safe:
            # fallback to hex of chat_id
            safe = chat_id.encode("utf-8").hex()
        return f"{safe}.json"

    def _chat_path(self, chat_id: str) -> Path:
        return self.dir / self._safe_filename(chat_id)

    def _load_chat_file(self, chat_id: str) -> Chat | None:
        p = self._chat_path(chat_id)
        if not p.exists():
            return None
        try:
            with p.open("r", encoding="utf-8") as fh:
                obj = json.load(fh)
        except Exception:
            return None

        messages_python = obj.get("messages", [])
        try:
            messages = ModelMessagesTypeAdapter.validate_python(messages_python)
        except Exception:
            messages = []

        try:
            return Chat(chat_id=obj.get("chat_id", chat_id), messages=messages)
        except Exception:
            return None

    def _save_chat_file(self, chat: Chat) -> None:
        p = self._chat_path(chat.chat_id)
        data = {"chat_id": chat.chat_id, "messages": to_jsonable_python(chat.messages)}
        tmp = p.with_suffix(".tmp")
        with tmp.open("w", encoding="utf-8") as fh:
            json.dump(data, fh, ensure_ascii=False, indent=2)
        tmp.replace(p)

    def get_chats(self) -> ChatResponse:
        """Return all chats by reading every file in the chats directory."""
        chats: list[Chat] = []
        for p in sorted(self.dir.glob("*.json")):
            try:
                with p.open("r", encoding="utf-8") as fh:
                    obj = json.load(fh)
            except Exception:
                continue

            messages_python = obj.get("messages", [])
            try:
                messages = ModelMessagesTypeAdapter.validate_python(messages_python)
            except Exception:
                messages = []

            try:
                chats.append(Chat(chat_id=obj.get("chat_id"), messages=messages))
            except Exception:
                continue

        return ChatResponse(chats=chats)

    def get_chat(self, chat_id: str) -> Chat | None:
        return self._load_chat_file(chat_id)

    def create_chat(self, chat_id: str) -> Chat:
        with self._lock:
            existing = self.get_chat(chat_id)
            if existing:
                return existing
            new_chat = Chat(chat_id=chat_id, messages=[])
            try:
                self._save_chat_file(new_chat)
            except Exception:
                pass
            return new_chat

    def add_message(self, chat_id: str, message) -> None:
        with self._lock:
            chat = self.get_chat(chat_id)
            if not chat:
                chat = Chat(chat_id=chat_id, messages=[])
            chat.messages.append(message)
            try:
                self._save_chat_file(chat)
            except Exception:
                pass


# module-level instance for convenience
db_json = DatabaseJson()
