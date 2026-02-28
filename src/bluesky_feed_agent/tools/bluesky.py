"""Bluesky API tools for fetching feed data."""

import json
from typing import Optional

try:
    from atproto import Client
except ImportError:
    Client = None


class BlueskyClient:
    """Client for fetching posts from Bluesky feed."""

    def __init__(self, username: str, password: str):
        """Initialize Bluesky client.

        Args:
            username: Bluesky username
            password: Bluesky password or app password
        """
        if Client is None:
            raise ImportError(
                "atproto is required. Install it with: pip install atproto"
            )

        self.client = Client()
        self.client.login(username, password)

    def get_home_feed(self, limit: int = 20) -> list[dict]:
        """Fetch posts from user's home feed.

        Args:
            limit: Maximum number of posts to fetch

        Returns:
            List of posts with text content
        """
        try:
            response = self.client.get_timeline(limit=limit)
            posts = []

            for feed_item in response.feed:
                post = feed_item.post
                posts.append(
                    {
                        "uri": post.uri,
                        "cid": post.cid,
                        "author": post.author.handle,
                        "text": post.record.text,
                        "created_at": post.record.created_at,
                        "like_count": post.like_count,
                        "reply_count": post.reply_count,
                        "repost_count": post.repost_count,
                    }
                )

            return posts
        except Exception as e:
            raise RuntimeError(f"Failed to fetch Bluesky feed: {str(e)}")

    def get_user_feed(self, handle: str, limit: int = 20) -> list[dict]:
        """Fetch posts from a specific user's feed.

        Args:
            handle: User's Bluesky handle
            limit: Maximum number of posts to fetch

        Returns:
            List of posts with text content
        """
        try:
            response = self.client.get_author_feed(handle, limit=limit)
            posts = []

            for feed_item in response.feed:
                post = feed_item.post
                posts.append(
                    {
                        "uri": post.uri,
                        "cid": post.cid,
                        "author": post.author.handle,
                        "text": post.record.text,
                        "created_at": post.record.created_at,
                        "like_count": post.like_count,
                        "reply_count": post.reply_count,
                        "repost_count": post.repost_count,
                    }
                )

            return posts
        except Exception as e:
            raise RuntimeError(f"Failed to fetch user feed: {str(e)}")


def format_posts_for_llm(posts: list[dict]) -> str:
    """Format posts into readable text for LLM processing.

    Args:
        posts: List of posts from Bluesky

    Returns:
        Formatted text representation of posts
    """
    if not posts:
        return "No posts found in the feed."

    formatted = "=== Bluesky Feed Posts ===\n\n"

    for i, post in enumerate(posts, 1):
        formatted += f"Post {i}:\n"
        formatted += f"Author: @{post['author']}\n"
        formatted += f"Posted: {post['created_at']}\n"
        formatted += f"Content:\n{post['text']}\n"
        formatted += f"Stats - Likes: {post['like_count']}, Replies: {post['reply_count']}, Reposts: {post['repost_count']}\n"
        formatted += "-" * 50 + "\n\n"

    return formatted
