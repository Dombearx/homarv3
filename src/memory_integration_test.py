"""Integration test for memory tools with Homar agent."""

import pytest
from unittest.mock import Mock, patch
import src.memory
from src.models.schemas import MyDeps


@pytest.mark.asyncio
async def test_memory_tools_exist():
    """Test that remember/recall memory tools are defined."""
    
    # Import tools
    from src.homar import (
        remember_user_memory,
        remember_global_memory,
        recall_user_memory,
        recall_global_memory
    )
    
    # Test that tools exist and are callable
    assert remember_user_memory is not None
    assert callable(remember_user_memory)
    print(f"✓ remember_user_memory tool exists and is callable")
    
    assert remember_global_memory is not None
    assert callable(remember_global_memory)
    print(f"✓ remember_global_memory tool exists and is callable")
    
    assert recall_user_memory is not None
    assert callable(recall_user_memory)
    print(f"✓ recall_user_memory tool exists and is callable")
    
    assert recall_global_memory is not None
    assert callable(recall_global_memory)
    print(f"✓ recall_global_memory tool exists and is callable")
    
    # Check docstrings contain important information
    assert remember_user_memory.__doc__ is not None
    assert "user-specific" in remember_user_memory.__doc__.lower()
    print(f"✓ remember_user_memory has appropriate documentation")
    
    assert remember_global_memory.__doc__ is not None
    assert "global" in remember_global_memory.__doc__.lower() or "system-wide" in remember_global_memory.__doc__.lower()
    print(f"✓ remember_global_memory has appropriate documentation")
    
    print(f"\n✓ All memory tools integrated successfully!")


@pytest.mark.asyncio
async def test_memory_manager():
    """Test memory manager basic functionality."""
    
    # Mock the mem0 Memory class
    with patch("src.memory.Memory") as mock_memory_class:
        # Create separate mock instances for user and global memory
        mock_user_instance = Mock()
        mock_global_instance = Mock()
        
        # Mock add to return a dict
        mock_user_instance.add.return_value = {"id": "mem_123", "status": "success"}
        mock_global_instance.add.return_value = {"id": "global_123", "status": "success"}
        
        # Mock search to return a list of results
        mock_user_instance.search.return_value = [
            {"memory": "User prefers coffee over tea"}
        ]
        mock_global_instance.search.return_value = [
            {"memory": "Always verify user consent"}
        ]
        
        # Return different instances for each call
        mock_memory_class.from_config.side_effect = [mock_user_instance, mock_global_instance]
        
        # Reset memory manager singleton
        from src.memory import MemoryManager, get_memory_manager
        MemoryManager._instance = None
        MemoryManager._user_memory = None
        MemoryManager._global_memory = None
        src.memory._memory_manager = None
        
        # Get memory manager
        manager = get_memory_manager()
        assert manager is not None
        print(f"✓ Memory manager initialized")
        
        # Test add_user_memory
        result = manager.add_user_memory("I prefer coffee", "user_123")
        assert result is not None
        print(f"✓ add_user_memory works")
        
        # Test add_global_memory
        result = manager.add_global_memory("Always verify consent")
        assert result is not None
        print(f"✓ add_global_memory works")
        
        # Test search_user_memories
        results = manager.search_user_memories("coffee", "user_123")
        assert len(results) > 0
        print(f"✓ search_user_memories works")
        
        # Test search_global_memories
        results = manager.search_global_memories("procedures")
        assert len(results) > 0
        print(f"✓ search_global_memories works")
        
        print(f"\n✓ Memory manager functionality verified!")
