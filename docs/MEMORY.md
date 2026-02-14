# Memory Layer Documentation

## Overview

The Homar agent now includes a memory layer powered by [mem0](https://mem0.ai), enabling it to remember and recall important user preferences and information across conversations.

## Features

- **In-Memory Storage**: All data is stored in RAM for MVP - no external database required, no persistence between restarts
- **Intelligent Memory Management**: Uses mem0's intelligent memory extraction and deduplication
- **Two Core Tools**:
  - `remember_memory`: Store important user preferences
  - `recall_memory`: Retrieve previously stored memories

## Architecture

### Components

1. **MemoryManager** (`src/memory.py`)
   - Singleton pattern ensures single memory instance
   - Configured for in-memory storage using Qdrant
   - Uses OpenAI for embeddings and LLM operations

2. **Memory Tools** (integrated in `src/homar.py`)
   - `remember_memory`: Stores user preferences with guidance to avoid over-storing
   - `recall_memory`: Searches and retrieves relevant memories

### Configuration

The memory system uses the following configuration:
- **Vector Store**: Qdrant in-memory (`:memory:`)
- **Embeddings**: OpenAI `text-embedding-3-small`
- **LLM**: OpenAI `gpt-4o-mini` with temperature 0.1
- **History DB**: SQLite in-memory (`:memory:`)

## Usage

### For Users

The agent will automatically use memory tools when appropriate:

**Storing Memories:**
```
User: "I prefer to wake up at 6 AM"
Homar: *stores in memory* "Remembered: User prefers to wake up at 6 AM"
```

**Recalling Memories:**
```
User: "What time do I usually wake up?"
Homar: *recalls from memory* "Based on what I remember, you prefer to wake up at 6 AM"
```

### Tool Guidelines

#### remember_memory

**When to use:**
- User explicitly shares important preferences
- User mentions personal information that should be remembered
- User states facts about themselves

**When NOT to use:**
- General conversation
- Commands or requests
- Questions
- Temporary context
- Information already stored (check with recall_memory first)

**Examples of appropriate usage:**
- ✅ "I'm allergic to peanuts"
- ✅ "I prefer communication in English"
- ✅ "My favorite color is blue"
- ✅ "I like to wake up at 6 AM"
- ❌ "Turn on the light" (command)
- ❌ "What's the weather?" (question)
- ❌ "I'm going to the store now" (temporary)

#### recall_memory

**When to use:**
- Making personalized recommendations
- Before storing new information (to check duplicates)
- User asks about their preferences
- Personalizing responses

**Parameters:**
- `query` (optional): Search query for specific memories. If empty, returns all memories.

## Technical Details

### Memory Storage

Memories are stored per user/thread:
- Uses Discord `thread_id` as the `user_id`
- Each memory is automatically extracted and structured by mem0
- Duplicate detection prevents redundant storage

### Retrieval

Memory retrieval uses semantic search:
- Vector similarity search via Qdrant
- Returns top 5 most relevant memories by default
- Can retrieve all memories if no query specified

## Testing

The memory layer includes comprehensive tests:

1. **Unit Tests** (`src/memory_test.py`):
   - MemoryManager singleton pattern
   - Add/search/get operations
   - Error handling

2. **Integration Tests** (`src/memory_integration_test.py`):
   - Tool registration verification
   - Documentation checks
   - End-to-end functionality

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
- Memory expiration and cleanup
- User privacy controls
- Memory export/import

## Dependencies

New dependencies added:
- `mem0ai`: Core memory functionality
- `qdrant-client`: Vector storage
- `sqlalchemy`: History tracking

See `pyproject.toml` for full dependency list.
