"""State passed between LangGraph nodes."""

from typing import TypedDict


class BotState(TypedDict, total=False):
    channel_id: int
    prompt: str
    is_direct_message: bool
    bot_name: str
    bot_mention: str
    was_mentioned: bool
    is_addressed: bool
    answer: str
    reset: bool
