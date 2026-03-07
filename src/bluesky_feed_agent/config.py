"""Configuration and constants for the Bluesky agent."""

import logging

# ── Logging ──────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("bluesky_agent")

# LLM Configuration
DEFAULT_LLM_MODEL = "models/gemini-2.5-flash"
DEFAULT_TEMPERATURE = 0.7

# Bluesky Feed Configuration
DEFAULT_POST_LIMIT = 20
MAX_POST_LIMIT = 100

# Post quality filters
MIN_POST_LENGTH = 15  # ignore very short / empty posts
DUPLICATE_SIMILARITY_THRESHOLD = 0.85  # near-duplicate Jaccard threshold

# Chunking – max posts per LLM call before we chunk-and-merge
CHUNK_SIZE = 30

# Retry configuration
MAX_RETRIES = 3
RETRY_BACKOFF_BASE = 2  # exponential back-off base in seconds

# Prompt Templates
DEFAULT_SUMMARY_LENGTH = "3-7 paragraphs"

# Timeouts (in seconds)
BLUESKY_TIMEOUT = 30
LLM_TIMEOUT = 60

# Cache TTL (seconds) – how long a fetched feed is considered fresh
FEED_CACHE_TTL = 300  # 5 minutes

# Error Messages
MISSING_CREDENTIALS_ERROR = (
    "Missing Bluesky credentials. "
    "Please set BLUESKY_USERNAME and BLUESKY_PASSWORD environment variables."
)
MISSING_GOOGLE_KEY_ERROR = (
    "Missing Google API key. Please set GOOGLE_API_KEY environment variable."
)
