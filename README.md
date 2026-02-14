# Homarv3 Discord Bot

A Polish-speaking home assistant Discord bot powered by PydanticAI, with integrations for Home Assistant, Todoist, Grocy, Google Calendar, and image generation.

## Features

- **Home Assistant Integration**: Control smart home devices (lights, PC, etc.)
- **Todoist Integration**: Manage tasks, shopping lists, and reminders
- **Grocy Integration**: Home groceries management
- **Google Calendar Integration**: Manage calendar events, appointments, and meetings
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
│   │   ├── google_calendar_agent.py  # Google Calendar integration
│   │   └── image_generation_agent.py  # RPG image generation
│   ├── delayed_message_scheduler.py  # Delayed message scheduling
│   ├── displayer/               # FastAPI image viewer service
│   ├── grocy_mcp/              # Grocy MCP server
│   ├── homar.py                # Main Homar agent
│   └── models/
│       └── schemas.py          # Pydantic models
├── docs/
│   └── DELAYED_MESSAGES.md     # Delayed message tool documentation
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
   GOOGLE_CALENDAR_CREDENTIALS_PATH=/path/to/credentials.json
   # Add other required tokens
   ```

5. **Set up Google Calendar credentials** (if using Google Calendar integration):
   
   a. Go to [Google Cloud Console](https://console.cloud.google.com/)
   
   b. Create a new project or select an existing one
   
   c. Enable the Google Calendar API:
      - Navigate to "APIs & Services" > "Library"
      - Search for "Google Calendar API"
      - Click "Enable"
   
   d. Configure OAuth consent screen:
      - Go to "APIs & Services" > "OAuth consent screen"
      - Choose "External" and click "Create"
      - Fill in the required fields (App name, User support email, Developer contact)
      - Add the scopes:
        - `https://www.googleapis.com/auth/calendar.readonly`
        - `https://www.googleapis.com/auth/calendar.events`
      - Add test users if needed
   
   e. Create OAuth credentials:
      - Go to "APIs & Services" > "Credentials"
      - Click "Create Credentials" > "OAuth client ID"
      - Choose "Desktop app" as the application type
      - Download the credentials JSON file
      - Save it and set the path in `GOOGLE_CALENDAR_CREDENTIALS_PATH` environment variable
   
   f. On first run, the MCP server will open a browser for OAuth authorization. Follow the prompts to authorize access.

6. **Install Node.js** (required for Google Calendar MCP server):
   The Google Calendar agent uses the `mcp-google-calendar` npm package which runs via `npx`.
   ```bash
   # Install Node.js if not already installed
   # On Ubuntu/Debian:
   sudo apt-get install nodejs npm
   
   # On macOS:
   brew install node
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
4. **Calendar management**: "Co mam w kalendarzu jutro?" (What's on my calendar tomorrow?)
5. **Delayed actions**: "Wyłącz światło za godzinę" (Turn off light in 1 hour)
6. **RPG image generation**: In #rpg or #rpg2 channels

For more details on the delayed message feature, see [docs/DELAYED_MESSAGES.md](docs/DELAYED_MESSAGES.md).

## Development

### Code Formatting

```bash
make format
```

This runs `ruff format` on the codebase.

### Adding New Tools

To add a new tool for the Homar agent:

1. Define the tool in `src/homar.py` using the `@homar.tool` decorator
2. Implement the tool function with appropriate parameters and return type
3. Update the agent instructions if needed
4. Test the tool by interacting with the bot

Example:
```python
@homar.tool
async def my_new_tool(ctx: RunContext[MyDeps], parameter: str) -> str:
    """Tool description for the AI to understand when to use it."""
    # Implementation
    return "result"
```

## Architecture Notes

- **PydanticAI**: AI agent framework with tool support
- **Discord.py**: Discord bot integration
- **MCP (Model Context Protocol)**: Used for external API integrations
- **FastMCP**: Toolset for Grocy integration
- **Logfire**: Observability and logging
- **asyncio**: Asynchronous task scheduling for delayed messages

## License

MIT License - see LICENSE file for details.
