from pydantic_ai import Agent
from pydantic_ai.mcp import MCPServerStreamableHTTP
from datetime import datetime
from zoneinfo import ZoneInfo
import os
from pydantic_ai.models.openai import OpenAIResponsesModelSettings

# Default timezone for date/time operations
DEFAULT_TIMEZONE = "Europe/Warsaw"

todoist_mcp_server = MCPServerStreamableHTTP(
    "https://ai.todoist.net/mcp",
    headers={"Authorization": f"Bearer {os.getenv('TODOIST_TOKEN')}"},
)

TODOIST_AGENT_PROMPT = """
You are an interface to the Todoist API.
To create a subtask, you must have an id of the parent task. Create or get it first.
Whenever you are asked to create any shopping list, grocy list or similar, follow these steps:
1. Create a parent task with the name of the list and due date if provided. If due date is not provided, set it to today.
2. For each item in the list, create a subtask under the parent task created in step 1. Do it in batch calls to not exceed rate limits. Subtask can never have due date, even if provided.

As a response, briefly summarize what have you done or if action was not possible, explain why.
Do not ask follow up questions.
"""

settings = OpenAIResponsesModelSettings(
    openai_reasoning_effort="minimal",
    openai_reasoning_summary="concise",
)

todoist_agent = Agent(
    "openai:gpt-5-mini",
    toolsets=[todoist_mcp_server],
    instructions=TODOIST_AGENT_PROMPT,
    model_settings=settings,
)


@todoist_agent.instructions
def add_current_date() -> str:
    tz = ZoneInfo(DEFAULT_TIMEZONE)
    today = datetime.now(tz=tz).date()
    return f"Today is {today}."
