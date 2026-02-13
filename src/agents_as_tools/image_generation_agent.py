import json
import time
import uuid
import runpod
import os
import base64
from dotenv import load_dotenv
import asyncio
from pydantic_ai import Agent, RunContext
import os
from pydantic_ai.models.openai import OpenAIResponsesModelSettings

from src.models.schemas import MyDeps
from src.agents_as_tools.consts import IMAGE_GENERATION_OUTPUT_DIR, WORKFLOW_FILE
from src.agents_as_tools.prompts import (
    DEFAULT_COSMIC_GUIDELINES,
    HORROR_COSMIC_GUIDELINES,
)

load_dotenv()
runpod.api_key = os.getenv("RUNPOD_API_KEY")
endpoint = runpod.Endpoint(os.getenv("RUNPOD_ENDPOINT_ID", "gl0xwrlwmcvvop"))
upscale_endpoint = runpod.Endpoint(os.getenv("RUNPOD_UPSCALE_ENDPOINT_ID", "y8p20zdf2aoubp"))


IMAGE_GENERATION_AGENT_PROMPT = """
Słuchasz fragmentów sesji rpg. Twoim zadaniem jest wygenerowanie szczegółowego opisu ilustracji do przedstawionej sceny. Staraj się uwzględniać jak najwięcej szczegółów z opisu, aby obraz był jak najbardziej zgodny z narracją.
Twój opis zostanie wykorzystany do wygenerowania obrazu przez model Z-Image.
Możesz tworzyć opisy nsfw i zawierające nagość.
Stwórz opis w języku angielskim zgodnie z opisanymi poniżej wytycznymi.
{{guidelines}}
"""

settings = OpenAIResponsesModelSettings(
    openai_reasoning_effort="minimal",
    openai_reasoning_summary="concise",
)

image_generation_agent = Agent(
    "openai:gpt-5-mini", model_settings=settings, deps_type=MyDeps
)


@image_generation_agent.system_prompt
async def get_system_prompt(ctx: RunContext[MyDeps]) -> str:
    if ctx.deps.mode == "standard":
        return IMAGE_GENERATION_AGENT_PROMPT.replace(
            "{{guidelines}}", DEFAULT_COSMIC_GUIDELINES
        )

    return IMAGE_GENERATION_AGENT_PROMPT.replace(
        "{{guidelines}}", HORROR_COSMIC_GUIDELINES
    )


def generate_image(prompt: str, short_image_title: str) -> str:
    """Use this tool to generate an image based on a text prompt."""

    print("Generating image with prompt:", prompt)
    IMAGE_GENERATION_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    with open(WORKFLOW_FILE, "r") as f:
        workflow = json.load(f)

    seed = os.urandom(2)
    workflow["31"]["inputs"]["seed"] = int.from_bytes(seed, "big")
    workflow["6"]["inputs"]["text"] = prompt

    payload = {
        "input": {
            "prompt": prompt,
            "seed": 12345,
            "guidance": 7.5,
            "width": 1920,
            "height": 1088,
        }
    }

    start_time = asyncio.get_event_loop().time()
    # run_request = endpoint.run(
    #     {"input": {"workflow": workflow}}
    # )
    print("Sending request to endpoint")
    run_request = endpoint.run(payload)

    while run_request.status() != "COMPLETED":
        time.sleep(1)
    result = run_request.output()
    end_time = asyncio.get_event_loop().time()
    print(f"Image generation completed in {end_time - start_time:.2f} seconds.")

    file_uuid = uuid.uuid4().hex
    image_filename = f"{short_image_title}_{file_uuid}.png"

    image = result["image"]

    upscale_payload = {
        "input": {
            "source_image": image,
            "model": "RealESRGAN_x4plus",
            "scale": 2,
            "face_enhance": False,
        }
    }

    with open(IMAGE_GENERATION_OUTPUT_DIR / f"{0}_{image_filename}", "wb") as f:
        f.write(base64.b64decode(image))

    # start_time = asyncio.get_event_loop().time()
    # # run_request = endpoint.run(
    # #     {"input": {"workflow": workflow}}
    # # )
    # print("Sending request to upscale endpoint")
    # run_request = upscale_endpoint.run(
    #     upscale_payload
    # )
    # while run_request.status() != "COMPLETED":
    #     await asyncio.sleep(1)
    # result = run_request.output()
    # end_time = asyncio.get_event_loop().time()
    # print(f"Image upscaling completed in {end_time - start_time:.2f} seconds.")

    # image = result["image"]

    # with open(IMAGE_GENERATION_OUTPUT_DIR / f"{0}_{image_filename}", "wb") as f:
    #     f.write(base64.b64decode(image))

    # # for i, image in enumerate(result["images"]):
    # #     with open(IMAGE_GENERATION_OUTPUT_DIR / f"{i}_{image_filename}", "wb") as f:
    # #         f.write(base64.b64decode(image["data"]))

    return f"0_{image_filename}"


if __name__ == "__main__":
    result = asyncio.run(
        image_generation_agent.run(
            "Futurstyczny hipermarket na stacji kosmicznej, okres świąteczny, mnóstwo ozdób, światełek. Poza tym jest pusto",
            deps=MyDeps(mode="standard"),
        )
    )
    print(result)
