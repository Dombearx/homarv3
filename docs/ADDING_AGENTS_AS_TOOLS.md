# Adding New Agents as Tools

## Overview

This guide explains how to create and integrate new specialized agents as tools in the Homarv3 project. Agents can be used as tools to break down complex functionality into modular, reusable components.

## What are Agents as Tools?

In PydanticAI, agents can be wrapped as tools to be called by other agents. This creates a hierarchical architecture where:
- The **main agent** (Homar) orchestrates high-level interactions
- **Sub-agents** (specialized agents) handle specific domains (e.g., Todoist, Home Assistant, Grocy)

This pattern is particularly useful for:
- Organizing complex functionality into domain-specific modules
- Reusing agents across different contexts
- Maintaining clean separation of concerns
- Leveraging specialized instructions and tools per domain

## Architecture

```
User Request
    ↓
Homar Agent (Main)
    ↓
┌──────────────┬──────────────┬──────────────┐
│ Todoist      │ Home         │ Grocy        │
│ Agent Tool   │ Assistant    │ Agent Tool   │
│              │ Agent Tool   │              │
└──────────────┴──────────────┴──────────────┘
```

## Step-by-Step Guide

### 1. Create the Agent File

Create a new agent file in `src/agents_as_tools/`:

```bash
src/agents_as_tools/
├── your_agent.py      # Your new agent
├── todoist_agent.py   # Existing examples
├── home_assistant_agent.py
├── grocy_agent.py
└── ...
```

### 2. Define the Agent

Here's a template for creating a new agent:

```python
from pydantic_ai import Agent, RunContext
from pydantic_ai.models.openai import OpenAIResponsesModelSettings

# Agent prompt - clear instructions for the agent's behavior
YOUR_AGENT_PROMPT = """
You are an interface to the [Service Name] API.
Execute user commands precisely and always use provided tools to interact with [Service Name].

[Add specific guidelines, constraints, or behaviors here]
"""

# Model settings - configure the model behavior
settings = OpenAIResponsesModelSettings(
    openai_reasoning_effort="minimal",  # "minimal" or "low" for faster responses
    openai_reasoning_summary="concise",
)

# Create the agent
your_agent = Agent(
    "openai:gpt-5-mini",              # Model to use
    toolsets=[],                       # Add toolsets or MCP servers here
    instructions=YOUR_AGENT_PROMPT,    # Agent instructions
    model_settings=settings,           # Model settings
    retries=3,                         # Number of retries on failure
)


# Optional: Add dynamic instructions that provide context
@your_agent.instructions
async def add_dynamic_context(ctx: RunContext) -> str:
    """
    This function runs before each agent call and adds dynamic context.
    Useful for providing current state, available options, etc.
    """
    # Fetch and return dynamic information
    return "Current context information..."
```

### 3. Add Tools to the Agent (Optional)

If your agent needs tools (MCP servers or custom functions):

#### Using MCP Servers

```python
from pydantic_ai.mcp import MCPServerSSE, MCPServerStreamableHTTP, MCPServerStdio

# HTTP-based MCP server
mcp_server = MCPServerStreamableHTTP(
    "https://api.example.com/mcp",
    headers={"Authorization": f"Bearer {os.getenv('API_TOKEN')}"},
)

# Or SSE-based MCP server
mcp_server = MCPServerSSE(
    "http://localhost:8123/mcp_server/sse",
    headers={"Authorization": f"Bearer {os.getenv('API_TOKEN')}"},
)

# Or stdio-based MCP server
mcp_server = MCPServerStdio(
    "python",
    args=["-m", "your.mcp.module"],
)

your_agent = Agent(
    "openai:gpt-5-mini",
    toolsets=[mcp_server],  # Add MCP server as toolset
    instructions=YOUR_AGENT_PROMPT,
    model_settings=settings,
)
```

#### Using FastMCP Toolsets

```python
from pydantic_ai.toolsets.fastmcp import FastMCPToolset
from your_mcp_module import mcp

mcp_toolset = FastMCPToolset(mcp)

your_agent = Agent(
    "openai:gpt-5-mini",
    toolsets=[mcp_toolset],
    instructions=YOUR_AGENT_PROMPT,
    model_settings=settings,
)
```

### 4. Register Agent as Tool in Main Agent

Add your agent as a tool in `src/homar.py`:

```python
from src.agents_as_tools.your_agent import your_agent

@homar.tool
async def your_service_api(ctx: RunContext[MyDeps], command: str) -> str:
    """Use this tool to interact with [Service Name] - [brief description of capabilities].
    
    Args:
        command: The natural language command to execute.
    
    Returns:
        The response from [Service Name] as a string.
    """
    r = await your_agent.run(
        command,
        usage=ctx.usage,
    )
    return r.output
```

**Important Notes:**

1. **`ctx` Parameter Not in Docstring**: According to PydanticAI documentation, the `ctx: RunContext[MyDeps]` parameter is **automatically passed** by the framework and should **NOT be documented** in the `Args:` section of the docstring. Only document the actual parameters that the LLM needs to provide.

2. **Tool Description**: The docstring serves two purposes:
   - First line: Brief description for the LLM to understand **when** to use this tool
   - `Args` section: Describes only the parameters the LLM needs to provide (excluding `ctx`)
   - `Returns` section: Describes what the tool returns

3. **Usage Tracking**: Pass `ctx.usage` to track token usage across the agent call chain.

### 5. Example: Complete Implementation

Here's a complete example based on the existing Todoist agent:

**File: `src/agents_as_tools/todoist_agent.py`**

```python
from pydantic_ai import Agent
from pydantic_ai.mcp import MCPServerStreamableHTTP
from datetime import date
import os
from pydantic_ai.models.openai import OpenAIResponsesModelSettings

# Initialize MCP server for Todoist
todoist_mcp_server = MCPServerStreamableHTTP(
    "https://ai.todoist.net/mcp",
    headers={"Authorization": f"Bearer {os.getenv('TODOIST_TOKEN')}"},
)

# Agent instructions
TODOIST_AGENT_PROMPT = """
You are an interface to the Todoist API.
To create a subtask, you must have an id of the parent task. Create or get it first.
Whenever you are asked to create any shopping list, grocy list or similar, follow these steps:
1. Create a parent task with the name of the list and due date if provided.
2. For each item in the list, create a subtask under the parent task created in step 1.

As a response, briefly summarize what have you done.
Do not ask follow up questions.
"""

# Model settings
settings = OpenAIResponsesModelSettings(
    openai_reasoning_effort="minimal",
    openai_reasoning_summary="concise",
)

# Create agent
todoist_agent = Agent(
    "openai:gpt-5-mini",
    toolsets=[todoist_mcp_server],
    instructions=TODOIST_AGENT_PROMPT,
    model_settings=settings,
)

# Add dynamic context
@todoist_agent.instructions
def add_current_date() -> str:
    return f"Today is {date.today()}."
```

**File: `src/homar.py` (excerpt)**

```python
from src.agents_as_tools.todoist_agent import todoist_agent

@homar.tool
async def todoist_api(ctx: RunContext[MyDeps], command: str) -> str:
    """Use this tool to interact with the Todoist API - todos, shopping list, tasks, things to remember, etc.

    Args:
        command: The natural language command to execute.

    Returns:
        The response from the Todoist API as a string.
    """
    r = await todoist_agent.run(
        command,
        usage=ctx.usage,
    )
    return r.output
```

### 6. Testing Your Agent

After implementing your agent, test it:

1. **Unit Test the Agent**: Test the agent directly

```python
if __name__ == "__main__":
    import asyncio

    async def main():
        result = await your_agent.run("Test command")
        print("Output:", result.output)

    asyncio.run(main())
```

2. **Integration Test via Main Agent**: Test through Discord bot or direct invocation

```python
from src.homar import run_homar

async def test():
    response = await run_homar("Command that should use your agent")
    print(response)
```

3. **Live Test**: Deploy and test through Discord

## Best Practices

### Agent Instructions

1. **Be Specific**: Clearly define what the agent should do and how it should behave
2. **Set Constraints**: Define what the agent should NOT do
3. **Provide Context**: Use `@agent.instructions` decorator to add dynamic context
4. **Keep it Concise**: Agents work better with clear, concise instructions

### Tool Descriptions

1. **First Line Matters**: The first line of the docstring should clearly indicate **when** to use the tool
2. **Don't Document `ctx`**: The `RunContext` parameter is automatically provided by PydanticAI
3. **Be Descriptive**: Help the main agent understand the tool's capabilities
4. **Include Examples**: When helpful, mention example use cases

### Model Settings

1. **Use Minimal Reasoning**: For most sub-agents, `openai_reasoning_effort="minimal"` is sufficient
2. **Concise Summaries**: Use `openai_reasoning_summary="concise"` to minimize token usage
3. **Consider Retries**: Set `retries=3` (or appropriate value) for reliability

### Error Handling

1. **Handle Errors Gracefully**: Return user-friendly error messages
2. **Log Errors**: Use logging to track issues
3. **Validate Inputs**: Check for required environment variables and dependencies

## Common Patterns

### Pattern 1: MCP Server Integration

Used for: External APIs that provide MCP endpoints

```python
mcp_server = MCPServerStreamableHTTP(
    "https://api.example.com/mcp",
    headers={"Authorization": f"Bearer {os.getenv('API_TOKEN')}"},
)

agent = Agent(
    "openai:gpt-5-mini",
    toolsets=[mcp_server],
    instructions=PROMPT,
    model_settings=settings,
)
```

**Examples**: `todoist_agent.py`, `home_assistant_agent.py`

### Pattern 2: FastMCP Integration

Used for: Custom MCP servers built with FastMCP

```python
from pydantic_ai.toolsets.fastmcp import FastMCPToolset
from your_module import mcp

toolset = FastMCPToolset(mcp)

agent = Agent(
    "openai:gpt-5-mini",
    toolsets=[toolset],
    instructions=PROMPT,
    model_settings=settings,
)
```

**Examples**: `grocy_agent.py`

### Pattern 3: Dynamic Instructions

Used for: Providing runtime context to agents

```python
@agent.instructions
async def add_context(ctx: RunContext) -> str:
    # Fetch current state
    state = await fetch_current_state()
    return f"Current state: {state}"
```

**Examples**: All existing agents use this pattern

## Troubleshooting

### Agent Not Being Called

**Symptom**: Main agent doesn't use your agent tool

**Solutions**:
1. Check tool description - ensure it's clear when to use this tool
2. Verify the tool is registered with the main agent
3. Check main agent instructions - ensure they encourage tool use
4. Test with explicit commands that should trigger your agent

### Missing Context or Errors

**Symptom**: Agent fails with missing information

**Solutions**:
1. Add dynamic instructions with `@agent.instructions`
2. Check environment variables are set
3. Verify MCP server is accessible
4. Add error handling and logging

### Token Usage Too High

**Symptom**: Agent calls are expensive

**Solutions**:
1. Use `openai_reasoning_effort="minimal"` for sub-agents
2. Keep instructions concise
3. Reduce message history if applicable
4. Consider using a smaller model for simple tasks

## Environment Variables

Add required environment variables to `.env`:

```bash
# Your service token
YOUR_SERVICE_TOKEN=your_token_here

# Other service-specific variables
YOUR_SERVICE_URL=https://api.example.com
```

Update the `.env.example` file with these variables for documentation.

## References

- [PydanticAI Documentation](https://ai.pydantic.dev/)
- [PydanticAI Tools Guide](https://ai.pydantic.dev/tools/)
- [PydanticAI MCP Integration](https://ai.pydantic.dev/mcp/)
- [Existing Agent Examples](../src/agents_as_tools/)

## Examples in This Codebase

Study these existing implementations:

1. **Todoist Agent** (`src/agents_as_tools/todoist_agent.py`)
   - Uses MCPServerStreamableHTTP
   - Dynamic date context
   - Task management instructions

2. **Home Assistant Agent** (`src/agents_as_tools/home_assistant_agent.py`)
   - Uses MCPServerSSE
   - Dynamic device list context
   - Home automation instructions

3. **Grocy Agent** (`src/agents_as_tools/grocy_agent.py`)
   - Uses FastMCPToolset
   - Custom MCP server integration
   - Inventory management instructions

4. **Image Generation Agent** (`src/agents_as_tools/image_generation_agent.py`)
   - Specialized image generation
   - Custom tools and workflow integration

## Checklist

When adding a new agent as a tool, ensure you:

- [ ] Create agent file in `src/agents_as_tools/`
- [ ] Define clear agent instructions
- [ ] Configure appropriate model settings
- [ ] Add toolsets (MCP servers or custom tools) if needed
- [ ] Add dynamic instructions if needed
- [ ] Register agent as tool in `src/homar.py`
- [ ] Write clear tool docstring (excluding `ctx` parameter)
- [ ] Pass `ctx.usage` for token tracking
- [ ] Add required environment variables to `.env`
- [ ] Test agent independently
- [ ] Test through main agent
- [ ] Update README.md if adding major functionality
- [ ] Document any special considerations

---

**Remember**: The `ctx: RunContext[MyDeps]` parameter in tool functions is **passed automatically by PydanticAI** and should **NOT** be documented in the docstring's `Args:` section. Only document the parameters that the LLM needs to provide!
