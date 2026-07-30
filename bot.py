"""Discord-to-Ollama bridge.

Replies to DMs and messages that @mention the bot.  Use !reset to clear the
conversation history for the current channel or DM.
"""

import asyncio
import logging
import os
from collections import defaultdict, deque
from typing import Deque, Dict, List

import discord
from dotenv import load_dotenv
from openai import APIConnectionError, APIStatusError, APITimeoutError, AsyncOpenAI

load_dotenv()

TOKEN = os.getenv("DISCORD_TOKEN")
OLLAMA_BASE_URL = os.getenv("LLM_BASE_URL", "http://127.0.0.1:11434").rstrip("/")
OLLAMA_MODEL = os.getenv("LLM_MODEL", "qwen3.6")
OLLAMA_API_KEY = os.getenv("LLM_API_KEY", "ollama")
SYSTEM_PROMPT = os.getenv("SYSTEM_PROMPT", "You are a helpful, concise assistant in a Discord server.")
MAX_HISTORY_MESSAGES = int(os.getenv("MAX_HISTORY_MESSAGES", "20"))
REQUEST_TIMEOUT_SECONDS = 180
DISCORD_MESSAGE_LIMIT = 2000

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger("ollama_discord_bot")

intents = discord.Intents.default()
intents.message_content = True
client = discord.Client(intents=intents)

# Ollama exposes an OpenAI-compatible endpoint at /v1. Supplying an arbitrary
# key is fine for the default local Ollama server; the SDK requires one.
openai_base_url = OLLAMA_BASE_URL if OLLAMA_BASE_URL.endswith("/v1") else f"{OLLAMA_BASE_URL}/v1"

llm = AsyncOpenAI(
    base_url=openai_base_url,
    api_key=OLLAMA_API_KEY,
    timeout=REQUEST_TIMEOUT_SECONDS,
)

# A separate short context is kept for each Discord channel (and each DM).
history: Dict[int, Deque[Dict[str,str]]] = defaultdict(lambda: deque(maxlen=MAX_HISTORY_MESSAGES or None))
# Prevent overlapping requests in one conversation from producing scrambled context.
channel_locks: Dict[int, asyncio.Lock] = defaultdict(asyncio.Lock)


def requested_text(message: discord.Message) -> str | None:
    """Return the user prompt if the message is intended for this bot."""
    if isinstance(message.channel, discord.DMChannel):
        return message.content.strip()

    if client.user and client.user.mentioned_in(message):
        return message.content.replace(client.user.mention, "").strip()
    return None


def split_message(text: str) -> List[str]:
    """Split output into Discord-sized pieces, favoring line boundaries."""
    chunks: List[str] = []
    remaining = text.strip() or "I couldn't generate a response."
    while len(remaining) > DISCORD_MESSAGE_LIMIT:
        boundary = remaining.rfind("\n", 0, DISCORD_MESSAGE_LIMIT)
        if boundary <= 0:
            boundary = remaining.rfind(" ", 0, DISCORD_MESSAGE_LIMIT)
        if boundary <= 0:
            boundary = DISCORD_MESSAGE_LIMIT
        chunks.append(remaining[:boundary])
        remaining = remaining[boundary:].lstrip()
    chunks.append(remaining)
    return chunks


async def ask_model(channel_id: int, prompt: str) -> str:
    messages: List[Dict[str, str]] = []
    if SYSTEM_PROMPT:
        messages.append({"role": "system", "content": SYSTEM_PROMPT})
    messages.extend(history[channel_id])
    messages.append({"role": "user", "content": f"\nothink {prompt}"})

    completion = await llm.chat.completions.create(
        model=OLLAMA_MODEL,
        messages=messages,  # type: ignore[arg-type]  # Discord history uses OpenAI chat roles.
    )
    answer = completion.choices[0].message.content.strip() if completion.choices and completion.choices[0].message.content else ""
    if not answer:
        raise RuntimeError("Ollama returned no message content")
    if MAX_HISTORY_MESSAGES > 0:
        history[channel_id].append({"role": "user", "content": prompt})
        history[channel_id].append({"role": "assistant", "content": answer})
    return answer


@client.event
async def on_ready() -> None:
    assert client.user is not None
    logger.info("Logged in as %s (%s); model=%s", client.user, client.user.id, OLLAMA_MODEL)


@client.event
async def on_message(message: discord.Message) -> None:
    if message.author.bot:
        return

    prompt = requested_text(message)
    if prompt is None:
        return

    if prompt.lower() == "!reset":
        history.pop(message.channel.id, None)
        await message.reply("Conversation history cleared.", mention_author=False)
        return
    if not prompt:
        await message.reply("Send a prompt after mentioning me, or DM me directly.", mention_author=False)
        return

    async with channel_locks[message.channel.id]:
        try:
            async with message.channel.typing():
                answer = await ask_model(message.channel.id, prompt)
            for chunk in split_message(answer):
                await message.reply(chunk, mention_author=False)
        except (APIConnectionError, APIStatusError, APITimeoutError, asyncio.TimeoutError, RuntimeError) as error:
            logger.exception("Model request failed")
            await message.reply(
                "I couldn't reach my internal model. Check that the model is running and "
                f"that `{OLLAMA_MODEL}` is installed. ({error})",
                mention_author=False,
            )


if __name__ == "__main__":
    if not TOKEN:
        raise SystemExit("DISCORD_TOKEN is missing. Copy .env.example to .env and set it.")
    if MAX_HISTORY_MESSAGES < 0:
        raise SystemExit("MAX_HISTORY_MESSAGES must be zero or a positive integer.")
    client.run(TOKEN, log_handler=None)
