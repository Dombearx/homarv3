import asyncio
import os
import re
import threading
import discord
from discord.ext import commands
import httpx
from loguru import logger
from dotenv import load_dotenv
import logfire
import uvicorn
from src.models.schemas import MyDeps
from src.agents_as_tools.image_generation_agent import (
    image_generation_agent,
    generate_image,
)
from src.homar import run_homar_with_history
import platform

logfire.configure(send_to_logfire=True)
logfire.instrument_pydantic_ai()

# Marker for delayed commands
DELAYED_COMMAND_MARKER = "[DELAYED_COMMAND]"

def in_wsl():
    version = platform.release().lower()
    if "microsoft" in version or "wsl" in version:
        return True

    try:
        with open("/proc/version", "rt") as f:
            return "microsoft" in f.read().lower()
    except FileNotFoundError:
        return False


load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")

if not TOKEN:
    raise RuntimeError("DISCORD_TOKEN is not set in the environment")

intents = discord.Intents.default()
intents.message_content = True
intents.messages = True

bot = commands.Bot(command_prefix="!", intents=intents)


def _sanitize_thread_name(s: str, max_len: int = 30) -> str:
    s = re.sub(r"\s+", " ", (s or "").strip())
    s = re.sub(r"[^\w\- ,.()]+", "", s)
    return s[:max_len] or "discussion"


async def _send_message_to_thread(message: str, thread_id: int):
    """Send a message to a Discord thread by ID."""
    try:
        channel = bot.get_channel(thread_id)
        if channel is None:
            # Try to fetch the thread if not in cache
            channel = await bot.fetch_channel(thread_id)
        
        if channel and isinstance(channel, discord.Thread):
            thread = channel
            await thread.send(message)
            logger.info(f"Sent delayed message to thread {thread_id}")
        else:
            logger.error(f"Could not find thread {thread_id} or it's not a Thread object")
    except Exception as e:
        logger.error(f"Error sending message to thread {thread_id}: {e}")


async def _get_thread_history(thread: discord.Thread) -> list:
    """Fetch message history from Discord thread and convert to ModelMessage format."""
    from pydantic_ai import ModelMessage, TextPart
    
    # Fetch last 50 messages from thread
    messages = []
    async for msg in thread.history(limit=50):
        # Skip system messages, include both user and bot messages
        if msg.type != discord.MessageType.default:
            continue
        
        # Determine role: bot messages are "assistant", user messages are "user"
        role = "assistant" if msg.author.bot else "user"
        messages.append(ModelMessage(
            role=role,
            content=[TextPart(text=msg.content)]
        ))
    
    # Reverse to get chronological order
    return list(reversed(messages))


@bot.event
async def on_ready():
    print(f"{bot.user} has connected to Discord!")


@bot.event
async def on_message(message: discord.Message):
    # Check if this is a delayed command from the bot itself
    is_delayed_command = (
        message.author == bot.user and 
        message.content.startswith(DELAYED_COMMAND_MARKER)
    )
    
    # Skip regular bot messages but allow delayed commands through
    if message.author == bot.user and not is_delayed_command:
        return
    
    # if the machine is not wsl and channel is testy - skip
    if message.channel.name == "testy":
        if not in_wsl():
            return

    if message.channel.name == "rpg" or message.channel.name == "rpg2":
        start_time = asyncio.get_event_loop().time()
        mode = "horror" if message.channel.name == "rpg2" else "standard"
        image_description = await image_generation_agent.run(
            message.content, deps=MyDeps(mode=mode)
        )
        image_filename = generate_image(image_description.output, "rpg_scene")
        logger.info(f"Generated {mode} RPG image: {image_filename}")
        try:
            async with httpx.AsyncClient() as client:
                await client.get(f"http://127.0.0.1:9005/show_image/{image_filename}")
        except Exception as e:
            logger.error(f"Failed to display image: {e}")
        end_time = asyncio.get_event_loop().time()
        logger.info(
            f"RPG image generation and display took {end_time - start_time:.2f} seconds."
        )
        return

    if isinstance(message.channel, discord.Thread):
        thread = message.channel
    else:
        try:
            thread_name = _sanitize_thread_name(
                message.content or f"from {message.author.display_name}"
            )
            thread = await message.create_thread(name=thread_name)
        except Exception:
            thread = message.channel

    try:
        async with thread.typing():
            # If this is a delayed command, extract the actual command
            if is_delayed_command:
                actual_message = message.content[len(DELAYED_COMMAND_MARKER):].strip()
                logger.info(f"Processing delayed command: {actual_message}")
            else:
                actual_message = message.content
            
            # Fetch thread history from Discord instead of external database
            thread_history = await _get_thread_history(thread)
            
            # Create deps with thread context for delayed message support
            deps = MyDeps(
                thread_id=thread.id,
                send_message_callback=_send_message_to_thread
            )
            
            response_message, _ = await run_homar_with_history(
                new_message=actual_message, history=thread_history, deps=deps
            )
            await thread.send(response_message)
    except Exception as e:
        logger.error(f"Error processing message: {e}")
        try:
            await thread.send(f"Error getting response: {e}")
        except Exception as send_error:
            logger.error(f"Failed to send error message: {send_error}")


def run_discord_bot():
    bot.run(TOKEN)


def run_fastapi():
    uvicorn.run(
        "src.displayer.main:app",
        host="0.0.0.0",
        port=9005,
        log_level="info",
    )


if __name__ == "__main__":
    threading.Thread(target=run_fastapi, daemon=True).start()
    run_discord_bot()
    print("Discord bot has stopped running.")
