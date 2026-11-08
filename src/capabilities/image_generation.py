"""Image generation capability: a prompt-writing subagent plus the RunPod image endpoint."""

import asyncio

from pydantic_ai import ModelRetry, RunContext
from pydantic_ai.capabilities import Capability

from src.agents_as_tools.consts import IMAGE_GENERATION_OUTPUT_DIR
from src.agents_as_tools.image_generation_agent import (
    generate_image,
    image_generation_agent,
)
from src.models.schemas import MyDeps

image_generation = Capability(
    id="image_generation",
    description="Generowanie obrazów i ilustracji na podstawie opisu.",
    instructions="Po wygenerowaniu obrazu nie opisuj go szczegółowo - zostanie wysłany jako załącznik.",
    defer_loading=True,
)


@image_generation.tool(retries=2)
async def generate_image_from_description(
    ctx: RunContext[MyDeps], description: str
) -> str:
    """Generate an image; it is attached to your reply automatically.

    Args:
        description: Natural language description of the image with all important details.
    """
    try:
        prompt = await image_generation_agent.run(
            description, deps=ctx.deps, usage=ctx.usage
        )
        image_filename = await asyncio.to_thread(
            generate_image, prompt.output, "homar_generated"
        )
    except Exception as e:
        raise ModelRetry(f"Image generation failed: {e}")
    ctx.deps.generated_images.append(str(IMAGE_GENERATION_OUTPUT_DIR / image_filename))
    return f"Image generated: {image_filename}"
