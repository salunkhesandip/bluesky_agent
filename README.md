# Bluesky Feed Agent

A LangGraph agent that fetches posts from Bluesky and generates AI-powered daily summaries.

## Features

- **Bluesky Integration**: Fetch posts from your home feed or any user's feed using the ATProto protocol
- **AI Summarization**: Use Google's Gemini models to generate intelligent summaries of Bluesky feeds
- **LangGraph Workflow**: Structured agent workflow for reliable processing
- **Async Support**: Non-blocking async operations for better performance

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
