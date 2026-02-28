"""Tests for the Bluesky feed agent."""

import pytest
from unittest.mock import Mock, patch
from src.bluesky_feed_agent.states import BlueskyFeedState
from src.bluesky_feed_agent.tools import format_posts_for_llm


@pytest.fixture
def sample_posts():
    """Sample Bluesky posts for testing."""
    return [
        {
            "uri": "at://did:plc:123/app.bsky.feed.post/abc123",
            "cid": "abc123",
            "author": "user1.bsky.social",
            "text": "Hello everyone! This is my first post.",
            "created_at": "2024-02-23T10:00:00.000Z",
            "like_count": 42,
            "reply_count": 5,
            "repost_count": 3,
        },
        {
            "uri": "at://did:plc:456/app.bsky.feed.post/def456",
            "cid": "def456",
            "author": "user2.bsky.social",
            "text": "Check out this interesting article about AI!",
            "created_at": "2024-02-23T11:00:00.000Z",
            "like_count": 120,
            "reply_count": 15,
            "repost_count": 45,
        },
    ]


def test_format_posts_for_llm(sample_posts):
    """Test formatting posts for LLM."""
    formatted = format_posts_for_llm(sample_posts)

    assert "Bluesky Feed Posts" in formatted
    assert "user1.bsky.social" in formatted
    assert "user2.bsky.social" in formatted
    assert "Hello everyone!" in formatted
    assert "Check out this interesting article" in formatted
    assert "Likes: 42" in formatted
    assert "Likes: 120" in formatted


def test_format_empty_posts():
    """Test formatting empty posts list."""
    formatted = format_posts_for_llm([])
    assert "No posts found" in formatted


def test_bluesky_feed_state():
    """Test BlueskyFeedState initialization."""
    state = BlueskyFeedState(user_handle="test.user")

    assert state.user_handle == "test.user"
    assert state.posts == []
    assert state.summary is None
    assert state.error is None


def test_bluesky_feed_state_with_posts(sample_posts):
    """Test BlueskyFeedState with posts."""
    state = BlueskyFeedState(posts=sample_posts)

    assert len(state.posts) == 2
    assert state.posts[0]["author"] == "user1.bsky.social"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
