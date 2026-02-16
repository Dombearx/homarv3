# Homarv3 - Discord Bot Copilot Instructions

This is a Python-based Discord bot named "Homar" (Polish-speaking home assistant) built with PydanticAI. The bot integrates with Home Assistant, Todoist, Grocy, Google Calendar, and HumbleBundle to provide smart home control, task management, and various other features through natural language interactions in Discord.

## Code Standards

### Required Before Each Commit
- Run `make format` before committing any changes to ensure proper code formatting
- This will run `ruff format` on all Python files to maintain consistent style

### Development Flow
- **Format code**: `make format`
- **Run tests**: `make test` or `poetry run pytest`
- **Run bot locally**: `make run` or `poetry run python main.py`

### Testing
- Tests are written using pytest with async support
- Test files follow the `*_test.py` naming convention
- Tests are located alongside source files in `src/` and in the root directory
- Run tests with `make test` or `poetry run pytest`
- Use `pytest-asyncio` for async test functions
- Mock external dependencies (APIs, Discord, etc.) in tests

## Repository Structure

- `src/`: Main source code directory
  - `agents_as_tools/`: Specialized sub-agents for different integrations
    - `todoist_agent.py`: Todoist API integration for task management
    - `home_assistant_agent.py`: Home Assistant control for smart home devices
    - `grocy_agent.py`: Grocy groceries management
    - `google_calendar_agent.py`: Google Calendar integration
    - `humblebundle_agent.py`: HumbleBundle deals checker
    - `image_generation_agent.py`: RPG image generation using RunPod
    - `prompts.py`: Prompt templates for agents
    - `consts.py`: Shared constants
  - `delayed_message_scheduler.py`: Asyncio-based delayed message scheduling
  - `displayer/`: FastAPI service for displaying generated images
  - `grocy_mcp/`: Grocy MCP (Model Context Protocol) server implementation
  - `homar.py`: Main Homar agent definition with PydanticAI
  - `models/`: Pydantic models and schemas
- `docs/`: Documentation files
  - `DELAYED_MESSAGES.md`: Documentation for delayed message feature
- `main.py`: Discord bot entry point and event loop
- `pyproject.toml`: Poetry configuration and dependencies
- `Dockerfile`: Docker configuration for containerized deployment
- `conftest.py`: Pytest configuration and shared test fixtures

## Key Technologies & Frameworks

1. **PydanticAI**: AI agent framework with tool support - primary framework for building agents
2. **Discord.py**: Discord bot integration
3. **FastAPI & Uvicorn**: Web service for image display
4. **MCP (Model Context Protocol)**: Used for external API integrations (Google Calendar, Grocy)
5. **FastMCP**: Toolset for Grocy integration
6. **Poetry**: Dependency management
7. **Ruff**: Code formatting
8. **Pytest**: Testing framework with async support
9. **Logfire**: Observability and logging
10. **Loguru**: Additional logging

## Key Guidelines

1. **Follow Python best practices**: Use type hints, async/await patterns, and Pydantic models
2. **Maintain existing architecture**: The bot uses a multi-agent architecture with specialized sub-agents
3. **Write async code**: Most functions should be async as the bot is built on asyncio
4. **Use PydanticAI patterns**:
   - Define tools using the `@agent.tool` decorator
   - Use `RunContext[MyDeps]` for dependency injection
   - Return structured data using Pydantic models
5. **Handle Polish language**: The bot primarily interacts in Polish, so support Polish in user-facing messages
6. **Write tests**: Add tests for new functionality following the `*_test.py` convention
7. **Mock external services**: Use `pytest-mock` or `unittest.mock` to mock external APIs and services in tests
8. **Document tools clearly**: Tool docstrings help the AI understand when to use them
9. **Environment variables**: Use `.env` file for configuration (see `.env.example` or README for required variables)
10. **Error handling**: Handle API errors gracefully and provide useful error messages

## Agent-Specific Notes

### Adding New Tools to Homar Agent
To add a new tool for the main Homar agent (`src/homar.py`):

1. Define the tool using the `@homar.tool` decorator
2. Implement the tool function with appropriate type hints and return type
3. Use `RunContext[MyDeps]` for dependency injection if needed
4. Provide a clear docstring explaining what the tool does (AI reads this)
5. Handle errors and edge cases appropriately

Example:
```python
@homar.tool
async def my_new_tool(ctx: RunContext[MyDeps], parameter: str) -> str:
    """
    Tool description for the AI to understand when to use it.
    
    Args:
        parameter: Description of what this parameter does
    """
    # Implementation
    return "result"
```

### Creating New Sub-Agents
Create a sub-agent (rather than a plain tool) when:
- The tool requires specific instructions on how to properly use it (e.g., Todoist agent has instructions on creating shopping lists correctly)
- There are many related tools that work together and share context
- The functionality benefits from its own dedicated agent with specialized behavior

New sub-agents should be created in `src/agents_as_tools/` and follow the pattern:
- Import and use PydanticAI Agent
- Define tools specific to that integration
- Add agent-specific instructions if needed
- Export the agent for use in the main Homar agent

## Discord Bot Specifics

- The bot maintains conversation history within Discord threads
- It responds to mentions and messages in channels it monitors
- Delayed message scheduling allows commands to be executed after a specified delay
- Special channels like #rpg trigger specific behaviors (image generation)

## Common Patterns

- **Dependency injection**: Use `MyDeps` class to pass shared resources to tools
- **Async operations**: Almost all functions are async
- **MCP integrations**: External APIs are often wrapped using MCP servers
- **Tool composition**: Main agent can invoke sub-agents as tools

## Important Conventions

- The bot responds in the same language as the user's input (no additional work needed)
- Keep responses concise and to the point (as per bot's instructions)
- Comments and logs should be in English
- Environment variables should be loaded via `python-dotenv`
- Mock `logfire` module in tests to avoid authentication issues (see `conftest.py`)
- Set fake environment variables in tests to prevent initialization errors
