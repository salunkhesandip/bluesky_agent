# Setup Guide for Bluesky Feed Agent

## WSL Ubuntu Setup

This section covers setting up the Bluesky Feed Agent in Windows Subsystem for Linux (WSL) with Ubuntu.

### Prerequisites for WSL Ubuntu

1. **Install WSL 2** (if not already installed):
```powershell
# Run in Windows PowerShell (as Administrator)
wsl --install -d Ubuntu
```

2. **Open WSL Ubuntu Terminal**:
```powershell
wsl
```

### 1. Update System and Install Dependencies

```bash
# Update package lists
sudo apt update
sudo apt upgrade -y

# Install Python and development tools
sudo apt install -y python3.12 python3.12-venv python3.12-dev python3-pip git

# Set Python 3.12 as default (optional)
sudo update-alternatives --install /usr/bin/python3 python3 /usr/bin/python3.12 1
```

### 2. Install uv Package Manager

```bash
# Install uv
curl -Ls https://astral.sh/uv/install.sh | sh
# Verify installation
uv --version
```

### 3. Clone the Repository

```bash
# Navigate to your desired directory
cd ~

# Clone the repository (or use your local path)
git clone <your-repo-url> bluesky_agent
cd bluesky_agent
```

### 4. Install Project Dependencies

```bash
# Using uv (recommended)
uv sync

# Or with development tools
uv sync --all-extras
```

Alternatively, using pip and requirements.txt:

```bash
# Create virtual environment (optional)
python3 -m venv venv
source venv/bin/activate


### 5. Configure Credentials in WSL

#### Option A: Create .env file

```bash
# Copy the example file
cp .env.example .env

# Edit with nano or your preferred editor
nano .env
```

Then add your credentials:
```bash
BLUESKY_USERNAME=your_username
BLUESKY_PASSWORD=your_app_password
GOOGLE_API_KEY=your_google_api_key
```

Save and exit (Ctrl+X, then Y, then Enter for nano)

#### Option B: Set Environment Variables in WSL

```bash
# Add to ~/.bashrc for persistence
echo 'export BLUESKY_USERNAME="your_username"' >> ~/.bashrc
echo 'export BLUESKY_PASSWORD="your_app_password"' >> ~/.bashrc
echo 'export GOOGLE_API_KEY="your_google_api_key"' >> ~/.bashrc

# Reload bashrc
source ~/.bashrc
```

### 6. Run the Agent in WSL

```bash
# Run directly
python main.py

# Or with a specific user
python main.py --user example.user

# Or as a module
uv run python -m src.bluesky_feed_agent.agent
```

### 7. Run Tests in WSL

```bash
# Run all tests
uv run pytest src/bluesky_feed_agent/tests/

# Run with verbose output
uv run pytest -v src/bluesky_feed_agent/tests/

# Run with coverage
uv run pytest --cov=src/bluesky_feed_agent src/bluesky_feed_agent/tests/
```

### Accessing Files Between Windows and WSL

Your work in WSL is accessible from Windows at:
```
\\wsl$\Ubuntu\home\<username>\bluesky_agent
```

You can also mount Windows directories in WSL:
```bash
# Mount Windows C: drive (usually auto-mounted)
cd /mnt/c/Users/YourUsername/Documents

# Or mount specific folder
sudo mkdir /mnt/myshare
sudo mount -t drvfs 'C:\path\to\folder' /mnt/myshare
```

### Known Issues and Solutions

#### Permission Denied
If you get permission errors:
```bash
# Make scripts executable
chmod +x main.py
```

#### Python Not Found
```bash
# Verify Python installation
python3 --version

# Or use explicit path
/usr/bin/python3.11 main.py
```

#### uv Command Not Found
```bash
# Reinstall in WSL environment
pip install --user uv

# Add to PATH
echo 'export PATH="$PATH:$HOME/.local/bin"' >> ~/.bashrc
source ~/.bashrc
```

#### ModuleNotFoundError
```bash
# Reinstall dependencies
uv sync --force

# Or clear cache
uv cache clean
uv sync
```

---

## Quick Start

### 1. Prerequisites

- Python 3.12 or higher
- A Bluesky account
- A Google API key
- `uv` package manager (install with: `pip install uv`)

### 2. Installation

#### Clone or navigate to the project directory:

```bash
cd bluesky_agent
```

#### Install the package with dependencies:

```bash
# Using uv (recommended)
uv sync
```

Or install with development tools:

```bash
uv sync --all-extras
```

### 3. Configure Credentials

#### Option A: Using Environment Variables

Create a `.env` file in the project root:

```bash
BLUESKY_USERNAME=your_username
BLUESKY_PASSWORD=your_app_password
GOOGLE_API_KEY=your_google_api_key
```

Then load it before running:

```bash
# On Linux/macOS
source .env

# On Windows PowerShell
Get-Content .env | ForEach-Object { $key, $value = $_ -split '='; [Environment]::SetEnvironmentVariable($key, $value) }
```

#### Option B: Set Environment Variables Directly

```bash
# Linux/macOS
export BLUESKY_USERNAME=your_username
export BLUESKY_PASSWORD=your_app_password
export GOOGLE_API_KEY=your_google_api_key

# Windows PowerShell
$env:BLUESKY_USERNAME = "your_username"
$env:BLUESKY_PASSWORD = "your_app_password"
$env:GOOGLE_API_KEY = "your_google_api_key"
```

### 4. Getting Your Bluesky App Password

1. Go to https://bsky.app/settings/app-passwords
2. Create a new app password
3. Copy the password and use it as `BLUESKY_PASSWORD`

### 5. Getting Your Google API Key

1. Go to https://makersuite.google.com/app/apikey
2. Create a new API key
3. Copy and use it as `GOOGLE_API_KEY`

---

## Integrations

### Gmail Integration (OAuth)

Send summary emails to your inbox using Gmail API with OAuth 2.0.

#### Step 1: Create Google Cloud Project

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select an existing one
3. Enable the **Gmail API**:
   - Navigate to **APIs & Services > Library**
   - Search for "Gmail API" and click **Enable**

#### Step 2: Create OAuth Credentials

1. Go to **APIs & Services > Credentials**
2. Click **Create Credentials > OAuth client ID**
3. If prompted, configure the OAuth consent screen:
   - Choose **External** (or Internal for Workspace)
   - Add your email as a test user
4. Select **Desktop app** as the application type
5. Download the JSON file and save it as `credentials.json` in the project root

#### Step 3: Configure Environment Variables

```bash
GMAIL_OAUTH_ENABLED=true
GMAIL_CREDENTIALS_FILE=credentials.json
GMAIL_TOKEN_FILE=token.json
GMAIL_OAUTH_FLOW=local
SUMMARY_EMAIL_TO=your_email@gmail.com
```

#### Step 4: First Run Authentication

1. Run the agent: `python main.py`
2. A browser window opens for Google sign-in
3. Grant the requested Gmail permissions
4. A `token.json` file is created for future runs

#### WSL/Headless Environment

If the browser doesn't open automatically:

```bash
GMAIL_OAUTH_FLOW=manual
```

Then copy the printed URL, open it in your browser, and complete the sign-in.

#### Token Expiry

If you see `invalid_grant: Token has been expired or revoked`:

1. Delete `token.json`
2. Run the agent again to re-authenticate

> **Note**: Changing your Google account password invalidates all OAuth tokens.

---

### Telegram Integration

Send audio summaries to a Telegram chat or channel.

#### Step 1: Create a Telegram Bot

1. Open Telegram and search for [@BotFather](https://t.me/BotFather)
2. Send `/newbot` and follow the prompts
3. Copy the **bot token** (format: `123456789:ABCdefGHIjklMNOpqrsTUVwxyz`)

#### Step 2: Get Your Chat ID

**Option A: Personal Chat**
1. Send any message to your new bot
2. Visit: `https://api.telegram.org/bot<YOUR_BOT_TOKEN>/getUpdates`
3. Find `"chat":{"id":123456789}` in the response

**Option B: Group/Channel**
1. Add your bot to the group/channel
2. Make the bot an admin (for channels)
3. Send a message in the group/channel
4. Visit the getUpdates URL above
5. Group IDs are negative (e.g., `-1001234567890`)

#### Step 3: Configure Environment Variables

```bash
TELEGRAM_BOT_TOKEN=123456789:ABCdefGHIjklMNOpqrsTUVwxyz
TELEGRAM_CHAT_ID=123456789
```

#### What Gets Sent

- The TTS audio file (MP3) of the summary
- A caption with the thematic overview (first sentence of the summary)

---

### Text-to-Speech (TTS)

Summaries are automatically converted to MP3 audio using Microsoft Edge TTS (free, no API key required).

#### Configure Voice

```bash
# Default: US English female voice
EDGE_TTS_VOICE=en-US-AriaNeural

# US English male voice
EDGE_TTS_VOICE=en-US-GuyNeural

# British English female voice
EDGE_TTS_VOICE=en-GB-SoniaNeural

# Other languages available (Spanish, French, German, etc.)
```

#### List Available Voices

```bash
# Install edge-tts CLI
pip install edge-tts

# List all voices
edge-tts --list-voices

# Filter by language
edge-tts --list-voices | grep en-US
```

See [edge-tts documentation](https://github.com/rany2/edge-tts) for the complete voice list.

---

## Running the Agent

### Via CLI

```bash
# Summarize your home feed
python main.py

# Summarize a specific user's feed
python main.py --user example.user
```

### Via Python Code

```python
import asyncio
from src.bluesky_feed_agent.agent import run_feed_summary_agent

async def main():
    # Summarize home feed
    result = await run_feed_summary_agent()
    print(result["summary"])

asyncio.run(main())
```

### Via LangGraph Agent Directly

```python
from src.bluesky_feed_agent.agent import create_agent_graph
from src.bluesky_feed_agent.states import BlueskyFeedState

# Create agent
agent = create_agent_graph()

# Create state
state = BlueskyFeedState(user_handle="example.user")

# Run agent
result = agent.invoke(state)

print(result.summary)
```

## Testing

Run the test suite:

```bash
uv run pytest src/bluesky_feed_agent/tests/
```

With coverage:

```bash
uv run pytest --cov=src/bluesky_feed_agent src/bluesky_feed_agent/tests/
```

## Troubleshooting

### ImportError: No module named 'atproto'

```bash
uv pip install atproto
```

### "Failed to fetch Bluesky feed" error

- Check that your `BLUESKY_USERNAME` and `BLUESKY_PASSWORD` are correct
- Ensure you're using an app password, not your main password
- The app password must be generated from https://bsky.app/settings/app-passwords

### "Failed to generate summary" error

- Check that `GOOGLE_API_KEY` is set correctly
- Verify you have API credits available on your Google Cloud account
- Ensure the model is available in your account

### Pydantic validation errors

Update pydantic to version 2.0 or higher:

```bash
uv pip install --upgrade pydantic
```

## Project Structure

```
bluesky_agent/
├── src/bluesky_feed_agent/
│   ├── agent/              # LangGraph agent implementation
│   ├── tools/              # Bluesky API client and utilities
│   ├── states/             # State definitions (Pydantic models)
│   ├── prompts/            # LLM system and user prompts
│   └── utils/              # Helper functions
├── main.py                 # CLI entry point
├── examples.py             # Usage examples
├── pyproject.toml          # Project configuration and dependencies
└── README.md               # Project documentation
```

## Customization

### Change the LLM Model

In `src/bluesky_feed_agent/agent/graph.py`, modify the `summarize_feed_node` function:

```python
llm = ChatGoogleGenerativeAI(model="gemini-pro", temperature=0.7, google_api_key=api_key)
```

### Modify Summary Prompt

Edit `src/bluesky_feed_agent/prompts/summary_prompt.py`:

```python
SYSTEM_PROMPT = """Your custom prompt here..."""
```

### Adjust Post Fetch Limit

In `src/bluesky_feed_agent/agent/graph.py`, change the `limit` parameter:

```python
posts = client.get_home_feed(limit=50)  # Default is 20
```

### Add Additional Processing Steps

Add new nodes to the graph in `src/bluesky_feed_agent/agent/graph.py`:

```python
def my_custom_node(state: BlueskyFeedState) -> BlueskyFeedState:
    # Your custom logic here
    return state

graph.add_node("my_custom_node", my_custom_node)
graph.add_edge("format_feed", "my_custom_node")
graph.add_edge("my_custom_node", "summarize")
```

## Next Steps

- Customize the summary prompt for your use case
- Add persistence to save summaries to a database
- Create a web interface with FastAPI/Flask
- Schedule daily runs with APScheduler
- Add more Bluesky features (likes, reposts, replies analysis)

## Support

For issues or questions, check the README.md or submit an issue to the repository.
