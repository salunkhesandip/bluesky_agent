"""LangGraph agent for Bluesky feed summarization."""

import asyncio
import os
from typing import Optional

from langchain_core.messages import HumanMessage
from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.graph import END, StateGraph

from src.bluesky_feed_agent.config import CHUNK_SIZE, logger
from src.bluesky_feed_agent.prompts import get_chunk_merge_prompt, get_summary_prompt
from src.bluesky_feed_agent.states import BlueskyFeedState
from src.bluesky_feed_agent.tools import BlueskyClient, format_posts_for_llm
from src.bluesky_feed_agent.utils import (
    generate_summary_audio,
    get_bluesky_credentials,
    get_openai_api_key,
    send_summary_email_oauth,
    send_summary_to_telegram,
)


# ── Helper: LLM singleton ───────────────────────────────────────────────
_llm_instance: ChatGoogleGenerativeAI | None = None


def _get_llm() -> ChatGoogleGenerativeAI:
    """Return a cached LLM instance."""
    global _llm_instance
    if _llm_instance is None:
        api_key = get_openai_api_key()
        _llm_instance = ChatGoogleGenerativeAI(
            model="models/gemini-2.5-flash",
            temperature=0.7,
            google_api_key=api_key,
        )
    return _llm_instance


# ── Graph nodes ──────────────────────────────────────────────────────────

def fetch_feed_node(state: BlueskyFeedState) -> BlueskyFeedState:
    """Fetch posts from Bluesky feed."""
    try:
        username, password = get_bluesky_credentials()

        try:
            limit = int(os.getenv("POST_LIMIT", "20"))
        except ValueError:
            limit = 20

        client = BlueskyClient(username=username, password=password)

        if state.user_handle:
            posts = client.get_user_feed(
                state.user_handle, limit=limit, sort_by_likes=True,
            )
        else:
            posts = client.get_home_feed(
                limit=limit, sort_by_likes=True, filter_replies=True, min_likes=50,
            )

        state.posts = posts
        logger.info("fetch_feed_node: %d posts loaded", len(posts))
        return state

    except Exception as e:
        logger.error("fetch_feed_node failed: %s", e)
        state.error = f"Failed to fetch feed: {e}"
        return state


def format_feed_node(state: BlueskyFeedState) -> BlueskyFeedState:
    """Format (and filter / deduplicate) posts for LLM processing."""
    try:
        state.raw_feed_text = format_posts_for_llm(state.posts)
        # ── state pruning: drop raw post dicts before the LLM step ──
        state.posts = []
        logger.info(
            "format_feed_node: formatted text length = %d chars",
            len(state.raw_feed_text),
        )
        return state
    except Exception as e:
        logger.error("format_feed_node failed: %s", e)
        state.error = f"Failed to format feed: {e}"
        return state


def summarize_feed_node(state: BlueskyFeedState) -> BlueskyFeedState:
    """Generate summary of feed using LLM, with chunking for large feeds."""
    try:
        if not state.raw_feed_text:
            state.error = "No feed content to summarize"
            return state

        llm = _get_llm()

        # ── Chunking: split long feeds into batches ─────────────────
        lines = state.raw_feed_text.split("\n")
        # Each "post block" is delimited by the separator line
        post_blocks: list[str] = []
        current: list[str] = []
        for line in lines:
            current.append(line)
            if line.startswith("-" * 10):
                post_blocks.append("\n".join(current))
                current = []
        if current:
            post_blocks.append("\n".join(current))

        if len(post_blocks) <= CHUNK_SIZE:
            # Single-shot summarisation
            prompt = get_summary_prompt(state.raw_feed_text)
            response = llm.invoke([HumanMessage(content=prompt)])
            state.summary = response.content
        else:
            # Chunk → summarise each → merge
            logger.info(
                "Large feed (%d blocks) – chunking into batches of %d",
                len(post_blocks),
                CHUNK_SIZE,
            )
            partial_summaries: list[str] = []
            for start in range(0, len(post_blocks), CHUNK_SIZE):
                chunk_text = "\n".join(post_blocks[start : start + CHUNK_SIZE])
                prompt = get_summary_prompt(chunk_text)
                resp = llm.invoke([HumanMessage(content=prompt)])
                partial_summaries.append(resp.content)

            merge_prompt = get_chunk_merge_prompt(partial_summaries)
            merged = llm.invoke([HumanMessage(content=merge_prompt)])
            state.summary = merged.content

        # ── state pruning: drop raw text after summarisation ─────────
        state.raw_feed_text = None
        logger.info("summarize_feed_node: summary generated (%d chars)", len(state.summary))
        return state

    except Exception as e:
        logger.error("summarize_feed_node failed: %s", e)
        state.error = f"Failed to generate summary: {e}"
        return state


def error_handler_node(state: BlueskyFeedState) -> BlueskyFeedState:
    """Log the error and pass state through."""
    logger.error("Pipeline error: %s", state.error)
    return state


def should_summarize(state: BlueskyFeedState) -> str:
    """Determine if summarization should proceed."""
    if state.error or not state.posts:
        return "error_handler"
    return "format_feed"


# ── Graph construction ───────────────────────────────────────────────────

def create_agent_graph() -> StateGraph:
    """Create the LangGraph workflow for feed summarization."""
    graph = StateGraph(BlueskyFeedState)

    graph.add_node("fetch_feed", fetch_feed_node)
    graph.add_node("format_feed", format_feed_node)
    graph.add_node("summarize", summarize_feed_node)
    graph.add_node("error_handler", error_handler_node)

    graph.set_entry_point("fetch_feed")
    graph.add_conditional_edges("fetch_feed", should_summarize)
    graph.add_edge("format_feed", "summarize")
    graph.add_edge("summarize", END)
    graph.add_edge("error_handler", END)

    return graph.compile()


# ── Async runner with parallel TTS + email + Telegram ────────────────────

async def run_feed_summary_agent(
    user_handle: Optional[str] = None,
) -> dict:
    """Run the feed summarization agent.

    Args:
        user_handle: Optional Bluesky user handle to summarize their feed

    Returns:
        Dictionary with posts, feed text, and summary
    """
    agent = create_agent_graph()

    initial_state = BlueskyFeedState(user_handle=user_handle or "")

    result = agent.invoke(initial_state)

    # Handle both dict and object returns
    if isinstance(result, dict):
        response = {
            "posts": result.get("posts"),
            "raw_feed": result.get("raw_feed_text"),
            "summary": result.get("summary"),
            "error": result.get("error"),
        }
    else:
        response = {
            "posts": result.posts,
            "raw_feed": result.raw_feed_text,
            "summary": result.summary,
            "error": result.error,
        }

    if response.get("summary") and not response.get("error"):
        # ── Parallel TTS + email ────────────────────────────────────
        audio_task = asyncio.create_task(_safe_tts(response["summary"]))
        # Wait for audio first so we can attach it to the email
        audio_path = await audio_task
        response["audio_path"] = audio_path

        # ── Send email (text only) and Telegram (MP3 only) in parallel ──
        email_task = asyncio.create_task(_safe_email(
            response["summary"], user_handle or "", None,
        ))
        telegram_task = asyncio.create_task(_safe_telegram(
            response["summary"], audio_path,
        ))

        response["email_status"] = await email_task
        response["telegram_status"] = await telegram_task

    return response


async def _safe_tts(summary: str) -> str | None:
    """Generate TTS audio, returning None on failure instead of raising."""
    try:
        return await generate_summary_audio(summary)
    except Exception as e:
        logger.error("TTS generation failed: %s", e)
        return None


async def _safe_email(summary: str, user_handle: str, audio_path: str | None) -> str:
    """Send email, returning status string instead of raising."""
    try:
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(
            None, send_summary_email_oauth, summary, user_handle, audio_path,
        )
    except Exception as e:
        logger.error("Email send failed: %s", e)
        return f"failed: {e}"


async def _safe_telegram(summary: str, audio_path: str | None) -> str:
    """Send to Telegram, returning status string instead of raising."""
    try:
        return await send_summary_to_telegram(summary, audio_path)
    except Exception as e:
        logger.error("Telegram send failed: %s", e)
        return f"failed: {e}"
