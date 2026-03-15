"""LangGraph agent for Bluesky feed summarization."""

import asyncio
import os
from typing import Any, Dict, Optional

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

# ── Constants ──────────────────────────────────────────────────────────
DEFAULT_POST_LIMIT = 20
SEPARATOR_THRESHOLD = 10  # Minimum separator line length
MIN_LIKES = 50  # Minimum likes threshold for filtering posts

# Response keys
RESP_POSTS = "posts"
RESP_RAW_FEED = "raw_feed"
RESP_SUMMARY = "summary"
RESP_ERROR = "error"
RESP_AUDIO_PATH = "audio_path"
RESP_EMAIL_STATUS = "email_status"
RESP_TELEGRAM_STATUS = "telegram_status"


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
            limit = int(os.getenv("POST_LIMIT", str(DEFAULT_POST_LIMIT)))
        except ValueError:
            logger.warning("Invalid POST_LIMIT, using default %d", DEFAULT_POST_LIMIT)
            limit = DEFAULT_POST_LIMIT

        client = BlueskyClient(username=username, password=password)

        if state.user_handle:
            posts = client.get_user_feed(
                state.user_handle, limit=limit, sort_by_likes=True,
            )
        else:
            posts = client.get_home_feed(
                limit=limit, sort_by_likes=True, filter_replies=True, min_likes=MIN_LIKES,
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

        import datetime
        # Generate date header
        today_header = '**' + datetime.datetime.now().strftime('%A, %d %B %Y') + '**'
        feed_with_date = today_header + '\n' + state.raw_feed_text
        if len(post_blocks) <= CHUNK_SIZE:
            # Single-shot summarisation
            prompt = get_summary_prompt(feed_with_date)
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
    logger.info("Agent graph execution completed")

    # Build response dictionary from result
    response: Dict[str, Any] = _build_response(result)

    if response.get(RESP_SUMMARY) and not response.get(RESP_ERROR):
        # ── Parallel TTS + email ────────────────────────────────────
        audio_task = asyncio.create_task(_safe_tts(response[RESP_SUMMARY]))
        # Wait for audio first so we can attach it to the email
        audio_path = await audio_task
        response[RESP_AUDIO_PATH] = audio_path

        # ── Send email (text only) and Telegram (MP3 only) in parallel ──
        email_task = asyncio.create_task(_safe_email(
            response[RESP_SUMMARY], user_handle or "", None,
        ))
        telegram_task = asyncio.create_task(_safe_telegram(
            response[RESP_SUMMARY], audio_path,
        ))

        response[RESP_EMAIL_STATUS] = await email_task
        response[RESP_TELEGRAM_STATUS] = await telegram_task

        email_ok = response[RESP_EMAIL_STATUS] == "sent"
        telegram_ok = response[RESP_TELEGRAM_STATUS] == "sent"

        if email_ok and telegram_ok:
            logger.info("Email and Telegram notifications sent")
        else:
            if not email_ok:
                logger.error("Email notification failed: %s", response[RESP_EMAIL_STATUS])
            if not telegram_ok:
                logger.error("Telegram notification failed: %s", response[RESP_TELEGRAM_STATUS])

    return response


async def _safe_tts(summary: str) -> Optional[str]:
    """Generate TTS audio, returning None on failure instead of raising.
    
    Args:
        summary: Summary text to convert to audio
        
    Returns:
        Path to generated MP3 file or None on failure
    """
    try:
        return await generate_summary_audio(summary)
    except Exception as e:
        logger.error("TTS generation failed: %s", e)
        return None


async def _safe_email(summary: str, user_handle: str, audio_path: Optional[str]) -> str:
    """Send email summary, returning status string instead of raising.
    
    Args:
        summary: Summary text to send
        user_handle: Bluesky user handle for email subject
        audio_path: Optional path to audio file (not used in email)
        
    Returns:
        Status string: "sent", "skipped", or error message
    """
    try:
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(
            None, send_summary_email_oauth, summary, user_handle, audio_path,
        )
    except Exception as e:
        logger.error("Email send failed: %s", e)
        return f"failed: {e}"


async def _safe_telegram(summary: str, audio_path: Optional[str]) -> str:
    """Send to Telegram with MP3 audio, returning status string instead of raising.
    
    Args:
        summary: Summary text to extract thematic overview from
        audio_path: Path to MP3 audio file to send
        
    Returns:
        Status string: "sent", "skipped", or error message
    """
    try:
        # Extract thematic overview (first sentence after date header)
        thematic_overview = _extract_thematic_overview(summary)
        return await send_summary_to_telegram(audio_path, thematic_overview)
    except Exception as e:
        logger.error("Telegram send failed: %s", e)
        return f"failed: {e}"


def _build_response(result: Any) -> Dict[str, Any]:
    """Build response dictionary from agent result.
    
    Handles both dict and object return types from LangGraph.
    
    Args:
        result: Agent execution result (dict or BlueskyFeedState object)
        
    Returns:
        Normalized response dictionary
    """
    if isinstance(result, dict):
        return {
            RESP_POSTS: result.get("posts"),
            RESP_RAW_FEED: result.get("raw_feed_text"),
            RESP_SUMMARY: result.get("summary"),
            RESP_ERROR: result.get("error"),
        }
    else:
        # Handle BlueskyFeedState object
        return {
            RESP_POSTS: result.posts,
            RESP_RAW_FEED: result.raw_feed_text,
            RESP_SUMMARY: result.summary,
            RESP_ERROR: result.error,
        }


def _extract_thematic_overview(summary: str) -> Optional[str]:
    """Extract thematic overview (first sentence) from summary.
    
    Args:
        summary: Full summary text
        
    Returns:
        First sentence after date header, or None if not found
    """
    lines = summary.split("\n")
    for line in lines:
        line = line.strip()
        if line and not line.startswith("**"):  # Skip date header
            return line
    return None
