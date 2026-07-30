"""Discord-specific event handling and output formatting."""

import asyncio
import logging
from collections import defaultdict
from typing import Dict, List

import discord
from openai import APIConnectionError, APIStatusError, APITimeoutError

from src.config import Settings
from src.model_inference import ModelInference
from src.workflow import build_workflow

logger = logging.getLogger("ollama_discord_bot")


def split_message(text: str, limit: int) -> List[str]:
    """Split output into Discord-sized pieces, favoring line boundaries."""
    chunks: List[str] = []
    remaining = text.strip() or "I couldn't generate a response."
    while len(remaining) > limit:
        boundary = remaining.rfind("\n", 0, limit)
        if boundary <= 0:
            boundary = remaining.rfind(" ", 0, limit)
        if boundary <= 0:
            boundary = limit
        chunks.append(remaining[:boundary])
        remaining = remaining[boundary:].lstrip()
    chunks.append(remaining)
    return chunks


def create_discord_client(settings: Settings) -> discord.Client:
    """Create a Discord client wired to the LangGraph message workflow."""
    intents = discord.Intents.default()
    intents.message_content = True
    client = discord.Client(intents=intents)
    model = ModelInference(settings)
    graph = build_workflow(model)
    channel_locks: Dict[int, asyncio.Lock] = defaultdict(asyncio.Lock)

    @client.event
    async def on_ready() -> None:
        assert client.user is not None
        logger.info("Logged in as %s (%s); model=%s", client.user, client.user.id, settings.llm_model)

    @client.event
    async def on_message(message: discord.Message) -> None:
        if message.author.bot:
            return

        async with channel_locks[message.channel.id]:
            try:
                async with message.channel.typing():
                    assert client.user is not None
                    was_mentioned = client.user.mentioned_in(message)
                    prompt = message.content.replace(client.user.mention, "").strip()
                    result = await graph.ainvoke(
                        {
                            "channel_id": message.channel.id,
                            "prompt": prompt,
                            "is_direct_message": isinstance(message.channel, discord.DMChannel),
                            "bot_name": client.user.display_name,
                            "bot_mention": client.user.mention if was_mentioned else "",
                            "was_mentioned": was_mentioned,
                        }
                    )
                if not result.get("is_addressed"):
                    return
                if result.get("reset"):
                    await message.reply("Conversation history cleared.", mention_author=False)
                    return
                answer = result.get("answer", "")
                if not answer:
                    raise RuntimeError("The response workflow completed without an answer")
                for chunk in split_message(answer, settings.discord_message_limit):
                    await message.reply(chunk, mention_author=False)
            except (APIConnectionError, APIStatusError, APITimeoutError, asyncio.TimeoutError, RuntimeError) as error:
                logger.exception("Model request failed")
                await message.reply(
                    "I couldn't reach my internal model. Check that the model is running and "
                    f"that `{settings.llm_model}` is installed. ({error})",
                    mention_author=False,
                )

    return client
