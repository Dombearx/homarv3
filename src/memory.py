"""Memory module for storing and retrieving user preferences using mem0."""

from __future__ import annotations

from mem0 import Memory
from loguru import logger


class MemoryManager:
    """Manages user memory storage and retrieval using mem0 with in-memory storage."""

    _instance: "MemoryManager" | None = None
    _memory: Memory | None = None

    def __new__(cls):
        """Singleton pattern to ensure only one memory instance."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        """Initialize the memory manager with in-memory configuration."""
        if self._memory is None:
            # Configure mem0 to use in-memory storage (no external database)
            config = {
                "vector_store": {
                    "provider": "qdrant",
                    "config": {
                        "collection_name": "user_memories",
                        "path": ":memory:",  # In-memory storage
                    },
                },
                "embedder": {
                    "provider": "openai",
                    "config": {
                        "model": "text-embedding-3-small",
                    },
                },
                "llm": {
                    "provider": "openai",
                    "config": {
                        "model": "gpt-5-mini",
                        "temperature": 0.1,
                    },
                },
                # Use SQLite in-memory for history tracking
                "history_db_path": ":memory:",
            }

            try:
                self._memory = Memory.from_config(config)
                logger.info("Memory manager initialized with in-memory storage")
            except Exception as e:
                logger.error(f"Failed to initialize memory manager: {e}")
                raise

    def add_memory(self, content: str, user_id: str, metadata: dict = None) -> dict:
        """
        Add a memory for a user.

        Args:
            content: The memory content to store (important user preference)
            user_id: Unique identifier for the user
            metadata: Optional metadata for categorization

        Returns:
            Result dictionary with memory information
        """
        try:
            if metadata is None:
                metadata = {}

            # Add memory using mem0
            result = self._memory.add(
                messages=[{"role": "user", "content": content}],
                user_id=user_id,
                metadata=metadata,
            )

            logger.info(f"Added memory for user {user_id}")
            return result

        except Exception as e:
            logger.error(f"Error adding memory: {e}")
            return {"error": str(e)}

    def search_memories(
        self, query: str, user_id: str, limit: int = 5
    ) -> list[dict]:
        """
        Search and retrieve memories for a user.

        Args:
            query: Search query to find relevant memories
            user_id: Unique identifier for the user
            limit: Maximum number of results to return

        Returns:
            List of relevant memories
        """
        try:
            # Search memories using mem0
            results = self._memory.search(
                query=query,
                user_id=user_id,
                limit=limit,
            )

            logger.info(f"Retrieved {len(results)} memories for user {user_id}")
            return results

        except Exception as e:
            logger.error(f"Error searching memories: {e}")
            return []


# Global singleton instance
_memory_manager = None


def get_memory_manager() -> MemoryManager:
    """Get or create the global memory manager instance."""
    global _memory_manager
    if _memory_manager is None:
        _memory_manager = MemoryManager()
    return _memory_manager
