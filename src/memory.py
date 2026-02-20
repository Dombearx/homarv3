"""Memory module for storing and retrieving user preferences using mem0."""

from __future__ import annotations

from mem0 import Memory
from loguru import logger


class MemoryManager:
    """Manages user memory storage and retrieval using mem0 with in-memory storage.
    
    Supports two types of memory:
    - User-specific: Personal preferences, facts about individual users
    - Global: System-wide information, general procedures, behavior guidelines
    """

    _instance: "MemoryManager" | None = None
    _user_memory: Memory | None = None
    _global_memory: Memory | None = None
    
    # Special user_id for global memories
    GLOBAL_USER_ID = "__GLOBAL__"

    def __new__(cls):
        """Singleton pattern to ensure only one memory instance."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        """Initialize the memory manager with in-memory configuration."""
        if self._user_memory is None or self._global_memory is None:
            # Configure mem0 to use in-memory storage (no external database)
            base_config = {
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
                # Initialize user-specific memory
                user_config = {
                    **base_config,
                    "vector_store": {
                        "provider": "qdrant",
                        "config": {
                            "collection_name": "user_memories",
                            "path": ":memory:",
                        },
                    },
                }
                self._user_memory = Memory.from_config(user_config)
                
                # Initialize global memory
                global_config = {
                    **base_config,
                    "vector_store": {
                        "provider": "qdrant",
                        "config": {
                            "collection_name": "global_memories",
                            "path": ":memory:",
                        },
                    },
                }
                self._global_memory = Memory.from_config(global_config)
                
                logger.info("Memory manager initialized with user-specific and global memory stores")
            except Exception as e:
                logger.error(f"Failed to initialize memory manager: {e}")
                raise

    def add_user_memory(self, content: str, user_id: str, metadata: dict | None = None) -> dict:
        """
        Add a memory for a specific user.

        Args:
            content: The memory content to store (user's personal preferences/info)
            user_id: Unique identifier for the user (Discord user ID)
            metadata: Optional metadata for categorization

        Returns:
            Result dictionary with memory information
        """
        try:
            if metadata is None:
                metadata = {}
            
            metadata["memory_type"] = "user_specific"

            # Add memory using mem0
            result = self._user_memory.add(
                messages=[{"role": "user", "content": content}],
                user_id=user_id,
                metadata=metadata,
            )

            logger.info(f"Added user-specific memory for user {user_id}")
            return result

        except Exception as e:
            logger.error(f"Error adding user memory: {e}")
            return {"error": str(e)}

    def add_global_memory(self, content: str, metadata: dict | None = None) -> dict:
        """
        Add a global memory accessible across all users.

        Args:
            content: The memory content to store (system-wide information)
            metadata: Optional metadata for categorization

        Returns:
            Result dictionary with memory information
        """
        try:
            if metadata is None:
                metadata = {}
            
            metadata["memory_type"] = "global"

            # Add memory using the global memory store with special user_id
            result = self._global_memory.add(
                messages=[{"role": "user", "content": content}],
                user_id=self.GLOBAL_USER_ID,
                metadata=metadata,
            )

            logger.info(f"Added global memory")
            return result

        except Exception as e:
            logger.error(f"Error adding global memory: {e}")
            return {"error": str(e)}

    def search_user_memories(
        self, query: str, user_id: str, limit: int = 5
    ) -> list[dict]:
        """
        Search and retrieve memories for a specific user.

        Args:
            query: Search query to find relevant memories
            user_id: Unique identifier for the user
            limit: Maximum number of results to return

        Returns:
            List of relevant user-specific memories
        """
        try:
            # Search memories using mem0
            results = self._user_memory.search(
                query=query,
                user_id=user_id,
                limit=limit,
            )

            logger.info(f"Retrieved {len(results)} user memories for user {user_id}")
            return results

        except Exception as e:
            logger.error(f"Error searching user memories: {e}")
            return []

    def search_global_memories(
        self, query: str, limit: int = 5
    ) -> list[dict]:
        """
        Search and retrieve global memories.

        Args:
            query: Search query to find relevant memories
            limit: Maximum number of results to return

        Returns:
            List of relevant global memories
        """
        try:
            # Search global memories using the special user_id
            results = self._global_memory.search(
                query=query,
                user_id=self.GLOBAL_USER_ID,
                limit=limit,
            )

            logger.info(f"Retrieved {len(results)} global memories")
            return results

        except Exception as e:
            logger.error(f"Error searching global memories: {e}")
            return []


# Global singleton instance
_memory_manager = None


def get_memory_manager() -> MemoryManager:
    """Get or create the global memory manager instance."""
    global _memory_manager
    if _memory_manager is None:
        _memory_manager = MemoryManager()
    return _memory_manager
