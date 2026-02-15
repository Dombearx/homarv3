from pydantic_ai import Agent, RunContext
from pydantic_ai.mcp import MCPServerStdio
from datetime import date
import os
from pydantic_ai.models.openai import OpenAIResponsesModelSettings
from dotenv import load_dotenv

load_dotenv()

# Initialize Google Calendar MCP server
# The server will be run via npx, using the credentials from environment variable
google_calendar_mcp_server = MCPServerStdio(
    "npx",
    args=["-y", "@cocal/google-calendar-mcp"],
    env={
        "GOOGLE_OAUTH_CREDENTIALS": os.getenv(
            "GOOGLE_OAUTH_CREDENTIALS"
        ),
        "GOOGLE_CALENDAR_MCP_TOKEN_PATH": os.getenv(
            "GOOGLE_CALENDAR_MCP_TOKEN_PATH"
        )
    },
)

GOOGLE_CALENDAR_AGENT_PROMPT = """
You are an interface to the Google Calendar API. Execute user commands precisely and always use provided tools to interact with Google Calendar.

You can:
- List upcoming events
- Create new events with title, date, time, and optional description
- Update existing events
- Delete events
- Search for specific events

When creating events, always ask for clarification if the date, time, or other important details are missing or unclear.
As a response, briefly summarize what you have done or if the action was not possible, explain why.
Do not ask follow up questions unless absolutely necessary.
"""

settings = OpenAIResponsesModelSettings(
    openai_reasoning_effort="minimal",
    openai_reasoning_summary="concise",
)

google_calendar_agent = Agent(
    "openai:gpt-5-mini",
    toolsets=[google_calendar_mcp_server],
    instructions=GOOGLE_CALENDAR_AGENT_PROMPT,
    model_settings=settings,
)


@google_calendar_agent.instructions
def add_current_date() -> str:
    return f"Today is {date.today()}."
