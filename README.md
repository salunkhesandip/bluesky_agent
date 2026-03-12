# Bluesky Feed Agent

A LangGraph agent that fetches posts from Bluesky and generates AI-powered daily summaries.

## Features

- **Bluesky Integration**: Fetch posts from your home feed or any user's feed using the ATProto protocol
- **AI Summarization**: Use Google's Gemini models to generate intelligent summaries of Bluesky feeds
- **LangGraph Workflow**: Structured agent workflow for reliable processing
- **Async Support**: Non-blocking async operations for better performance
- **Text-to-Speech**: Convert summaries to MP3 audio using Edge TTS
- **Gmail Integration**: Send summary emails via Gmail OAuth
- **Telegram Integration**: Send audio summaries to Telegram chats/channels

## Project Structure

```
src/bluesky_feed_agent/
├── agent/           # Main agent graph and workflow
├── tools/          # Bluesky API client and utilities
├── states/         # State definitions for the agent
├── prompts/        # LLM prompt templates
└── utils/          # Helper utilities
```

## Setup

**For detailed setup instructions, see [SETUP.md](SETUP.md)**

> **Windows Users**: For WSL Ubuntu setup instructions, see the [WSL Ubuntu Setup](SETUP.md#wsl-ubuntu-setup) section in SETUP.md

### Quick Start

**Prerequisites**: Install `uv` first with:
```bash
pip install uv
```

1. Install dependencies:

```bash
uv sync
```

Or with development tools:
```bash
uv sync --all-extras
```

2. Set environment variables

Create a `cp .env.example .env` file or set these environment variables:

```bash
# Bluesky credentials (get app password from https://bsky.app/settings/app-passwords)
BLUESKY_USERNAME=your_username
BLUESKY_PASSWORD=your_app_password

# Google Generative AI API key (get from https://makersuite.google.com/app/apikey)
GOOGLE_API_KEY=your_google_api_key

# Optional: Gmail OAuth email delivery for summaries
GMAIL_OAUTH_ENABLED=false
GMAIL_CREDENTIALS_FILE=credentials.json
GMAIL_TOKEN_FILE=token.json
GMAIL_OAUTH_FLOW=local
SUMMARY_EMAIL_TO=your_email@gmail.com

# Optional: Telegram audio delivery
TELEGRAM_BOT_TOKEN=your_bot_token
TELEGRAM_CHAT_ID=your_chat_id

# Optional: TTS voice (default: en-US-AriaNeural)
EDGE_TTS_VOICE=en-US-AriaNeural
```

### 3. Usage

#### Using the Agent Directly

```python
from src.bluesky_feed_agent.agent import run_feed_summary_agent

# Summarize home feed
result = await run_feed_summary_agent()

# Summarize a specific user's feed
result = await run_feed_summary_agent(user_handle="example.user")

print(result["summary"])
```

### Email Summary to Gmail (OAuth)

1. In Google Cloud Console, enable Gmail API and create an OAuth Client ID for a Desktop app.
2. Download the OAuth file and place it in project root as `credentials.json`.
3. In `.env`, set `GMAIL_OAUTH_ENABLED=true` and `SUMMARY_EMAIL_TO=your_email@gmail.com`.
4. Run the agent once; browser consent creates `token.json` for future runs.
5. If browser sign-in spins, set `GMAIL_OAUTH_FLOW=manual` and rerun; open the printed URL and finish consent in browser.

> **Note**: If you change your Google account password, the token becomes invalid. Delete `token.json` and re-authenticate.

### Telegram Audio Delivery

1. Create a bot via [@BotFather](https://t.me/BotFather) and copy the bot token.
2. Get your chat ID (send a message to your bot, then visit `https://api.telegram.org/bot<TOKEN>/getUpdates`).
3. In `.env`, set `TELEGRAM_BOT_TOKEN` and `TELEGRAM_CHAT_ID`.
4. The agent sends the TTS audio file with a thematic caption to your chat.

### Text-to-Speech (TTS)

Summaries are automatically converted to MP3 audio using Microsoft Edge TTS. Configure the voice:

```bash
# Default voice
EDGE_TTS_VOICE=en-US-AriaNeural

# Other examples: en-US-GuyNeural, en-GB-SoniaNeural
```

See [edge-tts voices](https://github.com/rany2/edge-tts) for all available options.

#### Using the CLI

```bash
# Summarize your home feed
python main.py

# Summarize a specific user's feed e.g. handle for PBS News
python main.py --user pbsnews.org
```

## Agent Workflow

The agent executes the following workflow:

1. **fetch_feed**: Fetches latest posts from Bluesky
2. **format_feed**: Formats posts into readable text for the LLM
3. **summarize**: Generates an AI-powered summary of the posts

## Customization

### Changing the Summary Prompt

Edit `src/bluesky_feed_agent/prompts/summary_prompt.py`:

```python
SYSTEM_PROMPT = """Your custom system prompt here..."""
```

### Adjusting Post Limit

In `src/bluesky_feed_agent/agent/graph.py`, modify the `limit` parameter:

```python
posts = client.get_home_feed(limit=50)  # Fetch more posts
```

### Using Different LLM Models

In `src/bluesky_feed_agent/agent/graph.py`, change the model:

```python
llm = ChatGoogleGenerativeAI(model="gemini-pro", temperature=0.7, google_api_key=api_key)
```

## Testing

Run tests with:

```bash
uv run pytest src/bluesky_feed_agent/tests/
```

## Requirements

- Python 3.12+
- LangGraph
- LangChain
- Google Generative AI API key
- Bluesky account with app password

## License

MIT
