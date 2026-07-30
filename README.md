# SirBOTato

A small [discord.py](https://discordpy.readthedocs.io/) bot that sends Discord prompts to a local [Ollama](https://ollama.com/) chat model through the OpenAI Python SDK and Ollama's OpenAI-compatible API. It replies to DMs and to messages that mention it in a server.

## Setup

1. Install Python 3.10 or newer, then create and activate a virtual environment:

   ```powershell
   py -m venv .venv
   .\.venv\Scripts\Activate.ps1
   pip install -r requirements.txt
   ```

2. Install and start Ollama, then download the model (use the exact name available in your Ollama library):

   ```powershell
   ollama pull qwen3.6
   ollama serve
   ```

3. In the [Discord Developer Portal](https://discord.com/developers/applications), create an application and bot. Under **Bot**, enable the **Message Content Intent**. Generate an installation URL with the `bot` scope and the permissions to View Channels, Send Messages, Read Message History, and Embed Links; then invite it to your server.

4. Copy `.env.example` to `.env`, set `DISCORD_TOKEN`, and adjust the Ollama settings if needed:

   ```powershell
   Copy-Item .env.example .env
   ```

5. Run the bot:

   ```powershell
   python bot.py
   ```

## Use

- Mention the bot in a server: `@YourBot explain black holes simply`
- Or send it a direct message.
- Send `!reset` in a DM or after mentioning the bot to clear that channel's saved context.

`MAX_HISTORY_MESSAGES` controls the number of stored user/assistant messages per conversation (default 20); use `0` for stateless prompts. The OpenAI SDK is pointed at `OLLAMA_BASE_URL/v1` (default `http://127.0.0.1:11434/v1`), so model traffic stays local. `OLLAMA_API_KEY` may stay as `ollama` for Ollama's default local server.
