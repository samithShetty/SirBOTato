"""OpenAI-SDK access to the local Ollama model and conversation memory."""

from collections import defaultdict, deque
from typing import Deque, Dict, List

from openai import AsyncOpenAI

from src.config import Settings


class ModelInference:
    """Runs completions and owns the short per-channel chat history."""

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.client = AsyncOpenAI(
            base_url=settings.api_base_url,
            api_key=settings.llm_api_key,
            timeout=settings.request_timeout_seconds,
        )
        self.history: Dict[int, Deque[Dict[str, str]]] = defaultdict(
            lambda: deque(maxlen=settings.max_history_messages or None)
        )

    async def complete(self, messages: List[Dict[str, str]]) -> str:
        completion = await self.client.chat.completions.create(
            model=self.settings.llm_model,
            messages=messages,  # type: ignore[arg-type]  # Plain dicts match OpenAI chat roles.
        )
        answer = completion.choices[0].message.content if completion.choices else None
        if not answer or not answer.strip():
            raise RuntimeError("Ollama returned no message content")
        return answer.strip()

    async def answer(self, channel_id: int, prompt: str) -> str:
        messages: List[Dict[str, str]] = []
        if self.settings.system_prompt:
            messages.append({"role": "system", "content": self.settings.system_prompt})
        messages.extend(self.history[channel_id])
        messages.append({"role": "user", "content": prompt})

        answer = await self.complete(messages)
        if self.settings.max_history_messages > 0:
            self.history[channel_id].append({"role": "user", "content": prompt})
            self.history[channel_id].append({"role": "assistant", "content": answer})
        return answer

    def clear_history(self, channel_id: int) -> None:
        self.history.pop(channel_id, None)
