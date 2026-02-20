# Memory Layer Documentation

## Overview

The Homar agent includes a dual memory layer powered by [mem0](https://mem0.ai), enabling it to remember and recall both user-specific preferences and system-wide information across conversations.

## Key Features

- **Dual Memory System**:
  - **User-Specific Memory**: Personal preferences and facts about individual users (isolated per user)
  - **Global Memory**: System-wide information, procedures, and behavioral guidelines (shared across all users)
- **In-Memory Storage**: All data stored in RAM for MVP - no external database required, no persistence between restarts
- **Intelligent Memory Management**: Uses mem0's LLM-based memory extraction and deduplication
- **User-Aware**: Integrates with Discord user authentication and role-based access control

## Architecture

### How mem0 Works

**LLM vs Embeddings:**
- **LLM (gpt-5-mini)**: The "brain" - analyzes conversations to extract structured facts, resolve conflicts, and understand what to remember
- **Embeddings (text-embedding-3-small)**: The "index" - creates vector representations for fast semantic similarity search
- **Vector Store (Qdrant)**: Stores embeddings in-memory for quick retrieval

**Process Flow:**
1. **Add Memory**: LLM extracts key facts from messages → Embeddings stored in vector database
2. **Search**: Query embedding finds similar vectors → Results ranked by relevance
3. **History**: SQLite tracks conversation metadata in-memory

### Components

1. **MemoryManager** (`src/memory.py`)
   - Singleton pattern with dual memory stores
   - User-specific memory (isolated by Discord username)
   - Global memory (accessible to all, modifiable by admins only)
   - Configured for in-memory storage using Qdrant

2. **Memory Tools** (integrated in `src/homar.py`)
   - `remember_user_memory`: Store personal user preferences
   - `remember_global_memory`: Store system-wide information (admin-only)
   - `recall_user_memory`: Retrieve user's personal memories
   - `recall_global_memory`: Retrieve system-wide memories

### Configuration

```python
# Shared configuration for both memory stores
base_config = {
    "embedder": {
        "provider": "openai",
        "config": {"model": "text-embedding-3-small"}
    },
    "llm": {
        "provider": "openai",
        "config": {"model": "gpt-5-mini", "temperature": 0.1}
    },
    "history_db_path": ":memory:"
}

# User-specific memory uses collection "user_memories"
# Global memory uses collection "global_memories"
```

## Usage

### For Users

The agent will automatically use memory tools when appropriate:

**Storing User-Specific Memories:**
```
User: "I prefer to wake up at 6 AM"
Homar: *stores in user memory* "Remembered (personal): I prefer to wake up at 6 AM"
```

**Recalling User Memories:**
```
User: "What time do I usually wake up?"
Homar: *recalls from user memory* "Personal memories:\n1. I prefer to wake up at 6 AM"
```

**Storing Global Memories (Admin Only):**
```
Admin: "Remember that we should always verify user consent before purchases"
Homar: *stores in global memory* "Remembered (global): Always verify user consent before purchases"
```

**Recalling Global Memories:**
```
User: "What are the purchase procedures?"
Homar: *recalls from global memory* "Global memories:\n1. Always verify user consent before purchases"
```

### Tool Guidelines

#### remember_user_memory

**When to use:**
- User shares PERSONAL preferences or information
- Information specific to one user only
- Personal facts, tastes, health info, schedules

**Examples:**
- ✅ "I'm allergic to peanuts" (personal health)
- ✅ "I prefer communication in English" (personal preference)
- ✅ "My favorite color is blue" (personal taste)
- ✅ "I live in Tokyo" (personal information)
- ❌ "Turn on the light" (command, not memory)
- ❌ "What's the weather?" (question, not memory)
- ❌ "The backup server is..." (system-wide, use global)

#### remember_global_memory

**When to use (Admin Only):**
- System-wide procedures and guidelines
- Behavioral rules that apply to all users
- General configuration information
- Common knowledge shared across users

**Examples:**
- ✅ "Always check user consent before making purchases"
- ✅ "To reset the alarm, press * three times"
- ✅ "Backup server address is backup.example.com"
- ❌ "I prefer coffee" (user-specific, use user memory)

#### recall_user_memory / recall_global_memory

**When to use:**
- Making personalized recommendations (user)
- Checking if information is already stored
- Following system procedures (global)
- Customizing responses based on history

**Parameters:**
- `query` (required): Search query for semantic search

## User Integration

### User Identification

User-specific memories are keyed by Discord `username` (from `message.author.display_name`), ensuring each user has isolated personal memory.

### Role-Based Access Control

- **Guest users**: Can use `recall_user_memory` and `recall_global_memory`, but NOT `remember_user_memory` or `remember_global_memory`
- **Default users**: Can use all recall tools and `remember_user_memory`
- **Admin users**: Full access to all memory tools including `remember_global_memory`

## Technical Details

### Memory Storage

**User-Specific Memories:**
- Stored per user (Discord username)
- Isolated - users cannot see each other's memories
- Metadata includes `memory_type: "user_specific"`

**Global Memories:**
- Stored with special user_id: `__GLOBAL__`
- Accessible to all users for reading
- Only admins can add new global memories
- Metadata includes `memory_type: "global"`

### Retrieval

Memory retrieval uses semantic search:
- Vector similarity search via Qdrant
- Returns top 5 most relevant memories by default
- LLM can rerank results for improved relevance

## Testing

The memory layer includes comprehensive tests:

1. **Unit Tests** (`src/memory_test.py`):
   - MemoryManager singleton pattern
   - Dual memory system (user + global)
   - Add/search operations for both memory types
   - Error handling

2. **Integration Tests** (`src/memory_integration_test.py`):
   - Tool registration verification
   - Documentation checks
   - End-to-end functionality for all 4 tools

Run tests:
```bash
python -m pytest src/memory_test.py -v
python -m pytest src/memory_integration_test.py -v
```

## Limitations (MVP)

- **No Persistence**: Data is lost on restart (in-memory storage)
- **No External Database**: All data stored in RAM
- **Single Process**: Not designed for distributed systems
- **Memory Limit**: Limited by available RAM

## Future Enhancements

Potential improvements for production:
- Persistent storage (PostgreSQL, MongoDB)
- Distributed memory across instances
- Memory expiration and cleanup policies
- User privacy controls and data export
- Memory versioning and rollback
- Cross-user memory sharing (with permissions)

## Dependencies

New dependencies added:
- `mem0ai`: Core memory functionality (v1.0.3)
- `qdrant-client`: Vector storage (in-memory)
- `sqlalchemy`: History tracking (in-memory)

See `pyproject.toml` for full dependency list.
