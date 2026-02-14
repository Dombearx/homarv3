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
            mock_instance = Mock()
            mock_memory.from_config.return_value = mock_instance
            yield mock_instance

    @pytest.fixture
    def memory_manager(self, mock_mem0):
        """Create a MemoryManager instance with mocked mem0."""
        # Reset singleton
        MemoryManager._instance = None
        MemoryManager._memory = None
        return MemoryManager()

    def test_singleton_pattern(self, mock_mem0):
        """Test that MemoryManager follows singleton pattern."""
        # Reset singleton
        MemoryManager._instance = None
        MemoryManager._memory = None
        
        manager1 = MemoryManager()
        manager2 = MemoryManager()
        
        assert manager1 is manager2

    def test_add_memory_success(self, memory_manager, mock_mem0):
        """Test successful memory addition."""
        mock_mem0.add.return_value = {"id": "mem_123", "status": "success"}
        
        result = memory_manager.add_memory(
            content="I prefer coffee over tea",
            user_id="user_123",
            metadata={"category": "preferences"}
        )
        
        assert "id" in result
        assert result["status"] == "success"
        mock_mem0.add.assert_called_once()

    def test_add_memory_with_defaults(self, memory_manager, mock_mem0):
        """Test memory addition with default metadata."""
        mock_mem0.add.return_value = {"id": "mem_456"}
        
        result = memory_manager.add_memory(
            content="I like hiking",
            user_id="user_456"
        )
        
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

    def test_get_all_memories_success(self, memory_manager, mock_mem0):
        """Test successful retrieval of all memories."""
        mock_mem0.get_all.return_value = [
            {"memory": "Memory 1"},
            {"memory": "Memory 2"},
            {"memory": "Memory 3"}
        ]
        
        results = memory_manager.get_all_memories(user_id="user_123")
        
        assert len(results) == 3
        mock_mem0.get_all.assert_called_once_with(user_id="user_123")

    def test_get_all_memories_empty(self, memory_manager, mock_mem0):
        """Test get_all_memories with no results."""
        mock_mem0.get_all.return_value = None
        
        results = memory_manager.get_all_memories(user_id="user_123")
        
        assert results == []

    def test_get_all_memories_error(self, memory_manager, mock_mem0):
        """Test error handling in get_all_memories."""
        mock_mem0.get_all.side_effect = Exception("Database error")
        
        results = memory_manager.get_all_memories(user_id="user_123")
        
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
