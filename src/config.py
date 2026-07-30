"""Environment-based application configuration."""

import os
from dataclasses import dataclass

from dotenv import load_dotenv


@dataclass(frozen=True)
class Settings:
    discord_token: str
    llm_base_url: str
    llm_model: str
    llm_api_key: str
    system_prompt: str
    max_history_messages: int
    request_timeout_seconds: int = 180
    discord_message_limit: int = 2000

    @property
    def api_base_url(self) -> str:
        base_url = self.llm_base_url.rstrip("/")
        return base_url if base_url.endswith("/v1") else f"{base_url}/v1"

    @classmethod
    def from_environment(cls) -> "Settings":
        load_dotenv()
        token = os.getenv("DISCORD_TOKEN")
        if not token:
            raise SystemExit("DISCORD_TOKEN is missing. Copy .env.example to .env and set it.")

        max_history = int(os.getenv("MAX_HISTORY_MESSAGES", "20"))
        if max_history < 0:
            raise SystemExit("MAX_HISTORY_MESSAGES must be zero or a positive integer.")

        return cls(
            discord_token=token,
            llm_base_url=os.getenv("LLM_BASE_URL", "http://127.0.0.1:11434"),
            llm_model=os.getenv("LLM_MODEL", "qwen3.6"),
            llm_api_key=os.getenv("LLM_API_KEY", "ollama"),
            system_prompt=os.getenv(
                "SYSTEM_PROMPT", "You are a helpful, concise assistant in a Discord server."
            ),
            max_history_messages=max_history,
        )
