"""Unit tests for memory module."""

import pytest
from unittest.mock import Mock, patch, MagicMock
from src.memory import MemoryManager, get_memory_manager


class TestMemoryManager:
    """Test the MemoryManager class."""

    @pytest.fixture
    def mock_mem0(self):
        """Mock the mem0 Memory class."""
        with patch("src.memory.Memory") as mock_memory:
            mock_user_instance = Mock()
            mock_global_instance = Mock()
            # Return different instances for user and global
            mock_memory.from_config.side_effect = [mock_user_instance, mock_global_instance]
            yield (mock_user_instance, mock_global_instance)

    @pytest.fixture
    def memory_manager(self, mock_mem0):
        """Create a MemoryManager instance with mocked mem0."""
        # Reset singleton
        MemoryManager._instance = None
        MemoryManager._user_memory = None
        MemoryManager._global_memory = None
        return MemoryManager()

    def test_singleton_pattern(self, mock_mem0):
        """Test that MemoryManager follows singleton pattern."""
        # Reset singleton
        MemoryManager._instance = None
        MemoryManager._user_memory = None
        MemoryManager._global_memory = None
        
        manager1 = MemoryManager()
        manager2 = MemoryManager()
        
        assert manager1 is manager2

    def test_add_user_memory_success(self, memory_manager, mock_mem0):
        """Test successful user memory addition."""
        mock_user_mem, _ = mock_mem0
        mock_user_mem.add.return_value = {"id": "mem_123", "status": "success"}
        
        result = memory_manager.add_user_memory(
            content="I prefer coffee over tea",
            user_id="user_123",
            metadata={"category": "preferences"}
        )
        
        assert "id" in result
        assert result["status"] == "success"
        mock_user_mem.add.assert_called_once()

    def test_add_user_memory_with_defaults(self, memory_manager, mock_mem0):
        """Test user memory addition with default metadata."""
        mock_user_mem, _ = mock_mem0
        mock_user_mem.add.return_value = {"id": "mem_456"}
        
        result = memory_manager.add_user_memory(
            content="I like hiking",
            user_id="user_456"
        )
        
        # Verify that metadata includes memory_type
        call_args = mock_user_mem.add.call_args
        assert call_args[1]["metadata"]["memory_type"] == "user_specific"

    def test_add_user_memory_error(self, memory_manager, mock_mem0):
        """Test error handling in add_user_memory."""
        mock_user_mem, _ = mock_mem0
        mock_user_mem.add.side_effect = Exception("API Error")
        
        result = memory_manager.add_user_memory(
            content="Test content",
            user_id="user_789"
        )
        
        assert "error" in result
        assert "API Error" in result["error"]

    def test_add_global_memory_success(self, memory_manager, mock_mem0):
        """Test successful global memory addition."""
        _, mock_global_mem = mock_mem0
        mock_global_mem.add.return_value = {"id": "global_123", "status": "success"}
        
        result = memory_manager.add_global_memory(
            content="Always verify user consent",
            metadata={"category": "guidelines"}
        )
        
        assert "id" in result
        assert result["status"] == "success"
        # Verify it used the global user ID
        call_args = mock_global_mem.add.call_args
        assert call_args[1]["user_id"] == MemoryManager.GLOBAL_USER_ID

    def test_search_user_memories_success(self, memory_manager, mock_mem0):
        """Test successful user memory search."""
        mock_user_mem, _ = mock_mem0
        mock_user_mem.search.return_value = [
            {"memory": "I prefer coffee over tea"},
            {"memory": "I like Italian food"}
        ]
        
        results = memory_manager.search_user_memories(
            query="food preferences",
            user_id="user_123",
            limit=5
        )
        
        assert len(results) == 2
        assert results[0]["memory"] == "I prefer coffee over tea"
        mock_user_mem.search.assert_called_once()

    def test_search_user_memories_empty(self, memory_manager, mock_mem0):
        """Test user memory search with no results."""
        mock_user_mem, _ = mock_mem0
        mock_user_mem.search.return_value = []
        
        results = memory_manager.search_user_memories(
            query="nonexistent",
            user_id="user_123"
        )
        
        assert results == []

    def test_search_user_memories_error(self, memory_manager, mock_mem0):
        """Test error handling in search_user_memories."""
        mock_user_mem, _ = mock_mem0
        mock_user_mem.search.side_effect = Exception("Search error")
        
        results = memory_manager.search_user_memories(
            query="test",
            user_id="user_123"
        )
        
        assert results == []

    def test_search_global_memories_success(self, memory_manager, mock_mem0):
        """Test successful global memory search."""
        _, mock_global_mem = mock_mem0
        mock_global_mem.search.return_value = [
            {"memory": "Always verify consent"},
            {"memory": "Backup server: backup.example.com"}
        ]
        
        results = memory_manager.search_global_memories(
            query="procedures",
            limit=5
        )
        
        assert len(results) == 2
        # Verify it used the global user ID
        call_args = mock_global_mem.search.call_args
        assert call_args[1]["user_id"] == MemoryManager.GLOBAL_USER_ID


class TestGetMemoryManager:
    """Test the get_memory_manager function."""

    @patch("src.memory.Memory")
    def test_get_memory_manager_creates_instance(self, mock_memory_class):
        """Test that get_memory_manager creates and returns instance."""
        # Reset global state
        import src.memory
        src.memory._memory_manager = None
        MemoryManager._instance = None
        MemoryManager._user_memory = None
        MemoryManager._global_memory = None
        
        mock_user_instance = Mock()
        mock_global_instance = Mock()
        mock_memory_class.from_config.side_effect = [mock_user_instance, mock_global_instance]
        
        manager = get_memory_manager()
        
        assert manager is not None
        assert isinstance(manager, MemoryManager)

    @patch("src.memory.Memory")
    def test_get_memory_manager_singleton(self, mock_memory_class):
        """Test that get_memory_manager returns same instance."""
        # Reset global state
        import src.memory
        src.memory._memory_manager = None
        MemoryManager._instance = None
        MemoryManager._user_memory = None
        MemoryManager._global_memory = None
        
        mock_user_instance = Mock()
        mock_global_instance = Mock()
        mock_memory_class.from_config.side_effect = [mock_user_instance, mock_global_instance]
        
        manager1 = get_memory_manager()
        manager2 = get_memory_manager()
        
        assert manager1 is manager2

        
        # Verify that metadata defaults to empty dict
        call_args = mock_mem0.add.call_args
        assert call_args[1]["metadata"] == {}

    def test_add_memory_error(self, memory_manager, mock_mem0):
        """Test error handling in add_memory."""
        mock_mem0.add.side_effect = Exception("API Error")
        
        result = memory_manager.add_memory(
            content="Test content",
            user_id="user_789"
        )
        
        assert "error" in result
        assert "API Error" in result["error"]

    def test_search_memories_success(self, memory_manager, mock_mem0):
        """Test successful memory search."""
        mock_mem0.search.return_value = [
            {"memory": "I prefer coffee over tea"},
            {"memory": "I like Italian food"}
        ]
        
        results = memory_manager.search_memories(
            query="food preferences",
            user_id="user_123",
            limit=5
        )
        
        assert len(results) == 2
        assert results[0]["memory"] == "I prefer coffee over tea"
        mock_mem0.search.assert_called_once()

    def test_search_memories_empty(self, memory_manager, mock_mem0):
        """Test memory search with no results."""
        mock_mem0.search.return_value = []
        
        results = memory_manager.search_memories(
            query="nonexistent",
            user_id="user_123"
        )
        
        assert results == []

    def test_search_memories_error(self, memory_manager, mock_mem0):
        """Test error handling in search_memories."""
        mock_mem0.search.side_effect = Exception("Search error")
        
        results = memory_manager.search_memories(
            query="test",
            user_id="user_123"
        )
        
        assert results == []


class TestGetMemoryManager:
    """Test the get_memory_manager function."""

    @patch("src.memory.Memory")
    def test_get_memory_manager_creates_instance(self, mock_memory_class):
        """Test that get_memory_manager creates and returns instance."""
        # Reset global state
        import src.memory
        src.memory._memory_manager = None
        MemoryManager._instance = None
        MemoryManager._memory = None
        
        mock_instance = Mock()
        mock_memory_class.from_config.return_value = mock_instance
        
        manager = get_memory_manager()
        
        assert manager is not None
        assert isinstance(manager, MemoryManager)

    @patch("src.memory.Memory")
    def test_get_memory_manager_singleton(self, mock_memory_class):
        """Test that get_memory_manager returns same instance."""
        # Reset global state
        import src.memory
        src.memory._memory_manager = None
        MemoryManager._instance = None
        MemoryManager._memory = None
        
        mock_instance = Mock()
        mock_memory_class.from_config.return_value = mock_instance
        
        manager1 = get_memory_manager()
        manager2 = get_memory_manager()
        
        assert manager1 is manager2
