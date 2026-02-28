"""Agent state definitions."""

from typing import Optional
from pydantic import BaseModel


class BlueskyFeedState(BaseModel):
    """State for the Bluesky feed summarization agent."""

    posts: list[dict] = []
    """List of posts fetched from Bluesky feed"""

    raw_feed_text: Optional[str] = None
    """Raw text representation of the feed"""

    summary: Optional[str] = None
    """Generated summary of the daily feed"""

    error: Optional[str] = None
    """Error message if any step fails"""

    user_handle: str = ""
    """Bluesky user handle to fetch feed for"""


class AgentState(BaseModel):
    """State used by the LangGraph agent."""

    messages: list = []
    """Chat message history"""

    feed_state: BlueskyFeedState
    """Current feed processing state"""
