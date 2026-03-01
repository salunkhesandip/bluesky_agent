"""Configuration and constants for the Bluesky agent."""

# LLM Configuration
DEFAULT_LLM_MODEL = "models/gemini-2.5-flash"
DEFAULT_TEMPERATURE = 0.7

# Bluesky Feed Configuration
DEFAULT_POST_LIMIT = 20
MAX_POST_LIMIT = 100

# Prompt Templates
DEFAULT_SUMMARY_LENGTH = "3-7 paragraphs"

# Timeouts (in seconds)
BLUESKY_TIMEOUT = 30
LLM_TIMEOUT = 60

# Error Messages
MISSING_CREDENTIALS_ERROR = (
    "Missing Bluesky credentials. "
    "Please set BLUESKY_USERNAME and BLUESKY_PASSWORD environment variables."
)
MISSING_GOOGLE_KEY_ERROR = (
    "Missing Google API key. Please set GOOGLE_API_KEY environment variable."
)
