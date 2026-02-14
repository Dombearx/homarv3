# Homarv3 Discord Bot

A Polish-speaking home assistant Discord bot powered by PydanticAI, with integrations for Home Assistant, Todoist, Grocy, and image generation.

## Features

- **Home Assistant Integration**: Control smart home devices (lights, PC, etc.)
- **Todoist Integration**: Manage tasks, shopping lists, and reminders
- **Grocy Integration**: Home groceries management
- **Image Generation**: Generate RPG scene images
- **Delayed Message Tool**: Schedule commands to be executed after a specified delay (see [docs/DELAYED_MESSAGES.md](docs/DELAYED_MESSAGES.md))
- **Conversation History**: Maintains context within Discord threads
- **Multi-Agent Architecture**: Specialized sub-agents for different tasks

## Project Structure

```
homarv3/
├── src/
│   ├── agents_as_tools/         # Specialized sub-agents
│   │   ├── todoist_agent.py     # Todoist API integration
│   │   ├── home_assistant_agent.py  # Home Assistant control
│   │   ├── grocy_agent.py       # Grocy groceries management
│   │   └── image_generation_agent.py  # RPG image generation
│   ├── delayed_message_scheduler.py  # Delayed message scheduling
│   ├── displayer/               # FastAPI image viewer service
│   ├── grocy_mcp/              # Grocy MCP server
│   ├── homar.py                # Main Homar agent
│   └── models/
│       └── schemas.py          # Pydantic models
├── docs/
│   ├── ADDING_AGENTS_AS_TOOLS.md  # Guide for creating agents as tools
│   └── DELAYED_MESSAGES.md        # Delayed message tool documentation
├── main.py                     # Discord bot entry point
├── pyproject.toml              # Poetry configuration
└── Dockerfile                  # Docker configuration
```

## Installation

1. **Clone the repository**:
   ```bash
   git clone <repository-url>
   cd homarv3
   ```

2. **Install Poetry** (if not already installed):
   ```bash
   curl -sSL https://install.python-poetry.org | python3 -
   ```

3. **Install dependencies**:
   ```bash
   poetry install
   ```

4. **Set up environment variables**:
   Create a `.env` file with the following variables:
   ```
   DISCORD_TOKEN=your_discord_bot_token
   TODOIST_TOKEN=your_todoist_token
   OPENAI_API_KEY=your_openai_api_key
   # Add other required tokens
   ```

## Running the Application

### Using Poetry

```bash
poetry run python main.py
```

This will start both:
- The Discord bot (connects to Discord)
- The FastAPI image displayer service (port 9005)

### Using Docker

```bash
# Build the image
make docker_build

# Run with docker-compose
docker-compose up -d
```

## Usage

The bot responds to messages in Discord channels and threads. It supports:

1. **Natural language commands**: Just talk to it naturally in Polish or English
2. **Home control**: "Włącz światło w sypialni" (Turn on bedroom light)
3. **Task management**: "Dodaj mleko do listy zakupów" (Add milk to shopping list)
4. **Delayed actions**: "Wyłącz światło za godzinę" (Turn off light in 1 hour)
5. **RPG image generation**: In #rpg or #rpg2 channels

For more details on the delayed message feature, see [docs/DELAYED_MESSAGES.md](docs/DELAYED_MESSAGES.md).

## Development

### Code Formatting

```bash
make format
```

This runs `ruff format` on the codebase.

### Adding New Tools

#### Simple Tools

To add a simple tool for the Homar agent:

1. Define the tool in `src/homar.py` using the `@homar.tool` decorator
2. Implement the tool function with appropriate parameters and return type
3. Update the agent instructions if needed
4. Test the tool by interacting with the bot

Example:
```python
@homar.tool
async def my_new_tool(ctx: RunContext[MyDeps], parameter: str) -> str:
    """Tool description for the AI to understand when to use it.
    
    Args:
        parameter: Description of the parameter.
    
    Returns:
        The result as a string.
    """
    # Implementation
    return "result"
```

**Note**: The `ctx` parameter is passed automatically by PydanticAI and should NOT be documented in the docstring.

#### Agents as Tools

For more complex functionality, you can create specialized sub-agents and integrate them as tools. This is the recommended approach for:
- External API integrations (Todoist, Home Assistant, Grocy, etc.)
- Domain-specific functionality with its own instructions and tools
- Modular, reusable components

See the complete guide: [docs/ADDING_AGENTS_AS_TOOLS.md](docs/ADDING_AGENTS_AS_TOOLS.md)

## Architecture Notes

- **PydanticAI**: AI agent framework with tool support
- **Discord.py**: Discord bot integration
- **MCP (Model Context Protocol)**: Used for external API integrations
- **FastMCP**: Toolset for Grocy integration
- **Logfire**: Observability and logging
- **asyncio**: Asynchronous task scheduling for delayed messages

## License

MIT License - see LICENSE file for details.
