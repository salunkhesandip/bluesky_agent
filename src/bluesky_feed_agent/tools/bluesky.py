"""Bluesky API tools for fetching feed data."""

import hashlib
import re
import time
from typing import Optional

from src.bluesky_feed_agent.config import (
    DUPLICATE_SIMILARITY_THRESHOLD,
    FEED_CACHE_TTL,
    MAX_RETRIES,
    MIN_POST_LENGTH,
    RETRY_BACKOFF_BASE,
    logger,
)

try:
    from atproto import Client
except ImportError:
    Client = None


# ── Simple in-memory feed cache ─────────────────────────────────────────
_feed_cache: dict[str, tuple[float, list[dict]]] = {}


def _cache_key(kind: str, handle: str, limit: int) -> str:
    return f"{kind}:{handle}:{limit}"


def _get_cached(key: str) -> list[dict] | None:
    entry = _feed_cache.get(key)
    if entry and (time.time() - entry[0]) < FEED_CACHE_TTL:
        logger.info("Feed cache hit for %s", key)
        return entry[1]
    return None


def _set_cache(key: str, posts: list[dict]) -> None:
    _feed_cache[key] = (time.time(), posts)


# ── Retry helper ─────────────────────────────────────────────────────────
def _retry(fn, *args, **kwargs):
    """Call *fn* with exponential back-off on failure."""
    last_exc: Exception | None = None
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            return fn(*args, **kwargs)
        except Exception as exc:
            last_exc = exc
            wait = RETRY_BACKOFF_BASE ** attempt
            logger.warning(
                "Attempt %d/%d failed (%s). Retrying in %ds…",
                attempt,
                MAX_RETRIES,
                exc,
                wait,
            )
            time.sleep(wait)
    raise RuntimeError(
        f"All {MAX_RETRIES} attempts failed. Last error: {last_exc}"
    ) from last_exc


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

    def get_home_feed(self, limit: int = 20, sort_by_likes: bool = True, filter_replies: bool = True, min_likes: int = 0) -> list[dict]:
        """Fetch posts from user's home feed.

        Args:
            limit: Maximum number of posts to fetch
            sort_by_likes: If True, sort posts by like_count descending
            filter_replies: If True, exclude reply posts (posts_no_replies behaviour)
            min_likes: Minimum number of likes required for a post to be included

        Returns:
            List of posts with text content
        """
        cache_key = _cache_key("home", "", limit)
        cached = _get_cached(cache_key)
        if cached is not None:
            return cached

        def _fetch():
            response = self.client.get_timeline(limit=limit)
            posts = []

            for feed_item in response.feed:
                post = feed_item.post
                # Skip replies if filter_replies is enabled
                if filter_replies and getattr(post.record, "reply", None) is not None:
                    continue
                # Skip posts with fewer likes than min_likes
                if min_likes > 0 and getattr(post, "like_count", 0) < min_likes:
                    continue
                posts.append(
                    {
                        "uri": post.uri,
                        "cid": post.cid,
                        "author": post.author.handle,
                        "display_name": getattr(post.author, "display_name", None) or post.author.handle,
                        "text": post.record.text,
                        "created_at": post.record.created_at,
                        "like_count": post.like_count,
                        "reply_count": post.reply_count,
                        "repost_count": post.repost_count,
                    }
                )
            logger.info("Fetched %d home-feed posts (after basic filter)", len(posts))
            if sort_by_likes:
                posts.sort(key=lambda p: p["like_count"], reverse=True)
            return posts

        try:
            posts = _retry(_fetch)
            _set_cache(cache_key, posts)
            return posts
        except Exception as e:
            raise RuntimeError(f"Failed to fetch Bluesky feed: {str(e)}")

    def get_user_feed(self, handle: str, limit: int = 20, sort_by_likes: bool = True) -> list[dict]:
        """Fetch posts from a specific user's feed.

        Args:
            handle: User's Bluesky handle
            limit: Maximum number of posts to fetch
            sort_by_likes: If True, sort posts by like_count descending

        Returns:
            List of posts with text content
        """
        cache_key = _cache_key("user", handle, limit)
        cached = _get_cached(cache_key)
        if cached is not None:
            return cached

        def _fetch():
            response = self.client.get_author_feed(handle, limit=limit, filter="posts_no_replies")
            posts = []

            for feed_item in response.feed:
                post = feed_item.post
                posts.append(
                    {
                        "uri": post.uri,
                        "cid": post.cid,
                        "author": post.author.handle,
                        "display_name": getattr(post.author, "display_name", None) or post.author.handle,
                        "text": post.record.text,
                        "created_at": post.record.created_at,
                        "like_count": post.like_count,
                        "reply_count": post.reply_count,
                        "repost_count": post.repost_count,
                    }
                )

            if sort_by_likes:
                posts.sort(key=lambda p: p["like_count"], reverse=True)
            logger.info("Fetched %d user-feed posts for @%s", len(posts), handle)
            return posts

        try:
            posts = _retry(_fetch)
            _set_cache(cache_key, posts)
            return posts
        except Exception as e:
            raise RuntimeError(f"Failed to fetch user feed: {str(e)}")


def _text_tokens(text: str) -> set[str]:
    """Tokenise text into a set of lower-case words (for Jaccard similarity)."""
    return set(re.findall(r"\w+", text.lower()))


def _jaccard(a: set[str], b: set[str]) -> float:
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


def filter_posts(posts: list[dict]) -> list[dict]:
    """Remove low-quality, spam-like, and near-duplicate posts.

    Filters applied:
    - Remove posts shorter than MIN_POST_LENGTH characters
    - Remove posts that are mostly URLs / hashtags with no substance
    - Remove near-duplicate posts (Jaccard similarity > threshold)

    Args:
        posts: Raw list of posts from Bluesky

    Returns:
        Cleaned list of posts
    """
    filtered: list[dict] = []
    seen_tokens: list[set[str]] = []

    for post in posts:
        text = (post.get("text") or "").strip()

        # ── skip too-short posts ────────────────────────────────────────
        if len(text) < MIN_POST_LENGTH:
            continue

        # ── skip posts that are almost entirely links / hashtags ─────────
        stripped = re.sub(r"https?://\S+", "", text)
        stripped = re.sub(r"#\w+", "", stripped).strip()
        if len(stripped) < MIN_POST_LENGTH:
            continue

        # ── near-duplicate detection ────────────────────────────────────
        tokens = _text_tokens(text)
        is_dup = any(
            _jaccard(tokens, prev) >= DUPLICATE_SIMILARITY_THRESHOLD
            for prev in seen_tokens
        )
        if is_dup:
            logger.debug("Dropping near-duplicate: %s…", text[:60])
            continue

        seen_tokens.append(tokens)
        filtered.append(post)

    logger.info(
        "Post filter: %d → %d posts (removed %d)",
        len(posts),
        len(filtered),
        len(posts) - len(filtered),
    )
    return filtered


def format_posts_for_llm(posts: list[dict]) -> str:
    """Filter, deduplicate, and format posts into readable text for LLM processing.

    Args:
        posts: List of posts from Bluesky

    Returns:
        Formatted text representation of posts
    """
    if not posts:
        return "No posts found in the feed."

    posts = filter_posts(posts)

    if not posts:
        return "No quality posts remaining after filtering."

    formatted = "=== Bluesky Feed Posts ===\n\n"

    for i, post in enumerate(posts, 1):
        name = post.get("display_name") or post["author"]
        formatted += f"Post {i}:\n"
        formatted += f"Author: {name} (@{post['author']})\n"
        formatted += f"Posted: {post['created_at']}\n"
        formatted += f"Content:\n{post['text']}\n"
        engagement = post["like_count"] + post["reply_count"] + post["repost_count"]
        formatted += (
            f"Engagement: {engagement} total "
            f"(Likes: {post['like_count']}, "
            f"Replies: {post['reply_count']}, "
            f"Reposts: {post['repost_count']})\n"
        )
        formatted += "-" * 50 + "\n\n"

    return formatted
