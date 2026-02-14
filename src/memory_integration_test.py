"""Integration test for memory tools with Homar agent."""

import pytest
from unittest.mock import Mock, patch
from src.models.schemas import MyDeps


@pytest.mark.asyncio
async def test_memory_tools_exist():
    """Test that remember_memory and recall_memory tools are defined."""
    
    # Import tools
    from src.homar import remember_memory, recall_memory
    
    # Test that tools exist and are callable
    assert remember_memory is not None
    assert callable(remember_memory)
    print(f"✓ remember_memory tool exists and is callable")
    
    assert recall_memory is not None
    assert callable(recall_memory)
    print(f"✓ recall_memory tool exists and is callable")
    
    # Check docstrings contain important information
    assert remember_memory.__doc__ is not None
    assert "important" in remember_memory.__doc__.lower()
    assert "preferences" in remember_memory.__doc__.lower()
    print(f"✓ remember_memory has appropriate documentation")
    
    assert recall_memory.__doc__ is not None
    assert "retrieve" in recall_memory.__doc__.lower() or "recall" in recall_memory.__doc__.lower()
    print(f"✓ recall_memory has appropriate documentation")
    
    print(f"\n✓ All memory tools integrated successfully!")


@pytest.mark.asyncio
async def test_memory_manager():
    """Test memory manager basic functionality."""
    
    # Mock the mem0 Memory class
    with patch("src.memory.Memory") as mock_memory_class:
        # Create mock memory instance with proper return values
        mock_memory_instance = Mock()
        
        # Mock add to return a dict
        mock_memory_instance.add.return_value = {"id": "mem_123", "status": "success"}
        
        # Mock search to return a list of results
        mock_memory_instance.search.return_value = [
            {"memory": "User prefers coffee over tea"}
        ]
        
        mock_memory_class.from_config.return_value = mock_memory_instance
        
        # Reset memory manager singleton
        from src.memory import MemoryManager, get_memory_manager
        import src.memory
        MemoryManager._instance = None
        MemoryManager._memory = None
        src.memory._memory_manager = None
        
        # Get memory manager
        manager = get_memory_manager()
        assert manager is not None
        print(f"✓ Memory manager initialized")
        
        # Test add_memory
        result = manager.add_memory("I prefer coffee", "user_123")
        # The result from the mock should be the dict we defined
        assert result is not None
        print(f"✓ add_memory works")
        
        # Test search_memories
        results = manager.search_memories("coffee", "user_123")
        assert len(results) > 0
        print(f"✓ search_memories works")
        
        print(f"\n✓ Memory manager functionality verified!")


