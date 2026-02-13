from pydantic_ai import Agent, RunContext
from pydantic_ai.models.openai import OpenAIResponsesModelSettings
from pydantic_ai.mcp import MCPServerStdio
from src.grocy_mcp.grocy_mcp import list_locations, list_quantity_units, list_products
from pydantic_ai.toolsets.fastmcp import FastMCPToolset
from datetime import datetime
from src.grocy_mcp.grocy_mcp import mcp

# grocy_mcp_server = MCPServerStdio(
#     "python",
#     args=["-m", "src.grocy_mcp.grocy_mcp"],
# )

grocy_mcp_toolset = FastMCPToolset(mcp)

GROCY_AGENT_PROMPT = """
You are an interface to the Grocy API. Execute user commands precisely and always use provided tools to interact with Grocy.
The default location is fridge unless specified otherwise.
Is data needed to perform the task is insufficient, ask for clarification.

Products represent only the item type (e.g., "Milk"), while stock entries (batches) represent specific quantities of that product with details like amount, best before date, and opened status.

Use only polish language for products names.
"""

settings = OpenAIResponsesModelSettings(
    openai_reasoning_effort="minimal",
    openai_reasoning_summary="concise",
)

grocy_agent = Agent(
    "openai:gpt-5-mini",
    toolsets=[grocy_mcp_toolset],
    instructions=GROCY_AGENT_PROMPT,
    model_settings=settings,
    retries=3,
)


@grocy_agent.instructions
async def add_devices_info(ctx: RunContext) -> str:
    locations = list_locations()
    quantity_units = list_quantity_units()
    products = list_products()

    current_date = datetime.now().strftime("%Y-%m-%d")

    return (
        f"Current Date: {current_date}\n\n{locations}\n\n{quantity_units}\n\n{products}"
    )


if __name__ == "__main__":
    import asyncio

    async def main():
        r = await grocy_agent.run(
            "Open a milk",
        )
        print("Output:", r.output)

    asyncio.run(main())