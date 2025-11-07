from pydantic_ai import Agent
from pydantic_ai.mcp import MCPServerStreamableHTTP
import os

todoist_mcp_server = MCPServerStreamableHTTP(
    "https://ai.todoist.net/mcp",
    headers={"Authorization": f"Bearer {os.getenv('TODOIST_TOKEN')}"},
)

TODOIST_AGENT_PROMPT = """
You are an interface to the Todoist API.
To create a subtask, you must have an id of the parent task. Create or get it first.
Whenever you are asked to create shopping list, create separate subtasks for each item. Subtasks should not have due date, but parent task should have due date.
As a response, summarize what have you done or if action was not possible, explain why.
Do not ask follow up questions.
"""

todoist_agent = Agent(
    "openai:gpt-5-mini",
    toolsets=[todoist_mcp_server],
    instructions=TODOIST_AGENT_PROMPT,
)
