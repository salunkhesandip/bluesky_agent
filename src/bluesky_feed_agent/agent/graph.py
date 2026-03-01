"""LangGraph agent for Bluesky feed summarization."""

import os
from typing import Optional
from langgraph.graph import StateGraph, END
from langchain_core.messages import HumanMessage
from langchain_google_genai import ChatGoogleGenerativeAI

from src.bluesky_feed_agent.states import BlueskyFeedState
from src.bluesky_feed_agent.tools import BlueskyClient, format_posts_for_llm
from src.bluesky_feed_agent.prompts import get_summary_prompt
from src.bluesky_feed_agent.utils import get_bluesky_credentials, get_openai_api_key

def fetch_feed_node(state: BlueskyFeedState) -> BlueskyFeedState:
    """Fetch posts from Bluesky feed.

    Args:
        state: Current agent state

    Returns:
        Updated state with fetched posts
    """
    try:
        # Get credentials from environment
        username, password = get_bluesky_credentials()

        # Determine how many posts to pull
        try:
            limit = int(os.getenv("POST_LIMIT", "20"))
        except ValueError:
            limit = 20

        # Initialize Bluesky client
        client = BlueskyClient(username=username, password=password)

        # Fetch feed
        if state.user_handle:
            posts = client.get_user_feed(state.user_handle, limit=limit)
        else:
            posts = client.get_home_feed(limit=limit)

        state.posts = posts
        return state

    except Exception as e:
        state.error = f"Failed to fetch feed: {str(e)}"
        return state


def format_feed_node(state: BlueskyFeedState) -> BlueskyFeedState:
    """Format posts for LLM processing.

    Args:
        state: Current agent state

    Returns:
        Updated state with formatted feed text
    """
    try:
        state.raw_feed_text = format_posts_for_llm(state.posts)
        return state
    except Exception as e:
        state.error = f"Failed to format feed: {str(e)}"
        return state


def summarize_feed_node(state: BlueskyFeedState) -> BlueskyFeedState:
    """Generate summary of feed using LLM.

    Args:
        state: Current agent state

    Returns:
        Updated state with generated summary
    """
    try:
        if not state.raw_feed_text:
            state.error = "No feed content to summarize"
            return state

        # Initialize LLM
        api_key = get_openai_api_key()
        llm = ChatGoogleGenerativeAI(model="models/gemini-2.5-flash", temperature=0.7, google_api_key=api_key)

        # Get prompt
        prompt = get_summary_prompt(state.raw_feed_text)

        # Generate summary
        message = HumanMessage(content=prompt)
        response = llm.invoke([message])

        state.summary = response.content
        return state

    except Exception as e:
        state.error = f"Failed to generate summary: {str(e)}"
        return state


def should_summarize(state: BlueskyFeedState) -> str:
    """Determine if summarization should proceed.

    Args:
        state: Current agent state

    Returns:
        Next node to execute
    """
    if state.error or not state.posts:
        return "error_handler"
    return "format_feed"


def create_agent_graph() -> StateGraph:
    """Create the LangGraph workflow for feed summarization.

    Returns:
        Compiled LangGraph graph
    """
    # Create graph
    graph = StateGraph(BlueskyFeedState)

    # Add nodes
    graph.add_node("fetch_feed", fetch_feed_node)
    graph.add_node("format_feed", format_feed_node)
    graph.add_node("summarize", summarize_feed_node)
    graph.add_node("error_handler", lambda state: state)

    # Add edges
    graph.set_entry_point("fetch_feed")
    graph.add_conditional_edges("fetch_feed", should_summarize)
    graph.add_edge("format_feed", "summarize")
    graph.add_edge("summarize", END)
    graph.add_edge("error_handler", END)

    return graph.compile()


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
        return {
            "posts": result.get("posts"),
            "raw_feed": result.get("raw_feed_text"),
            "summary": result.get("summary"),
            "error": result.get("error"),
        }
    else:
        return {
            "posts": result.posts,
            "raw_feed": result.raw_feed_text,
            "summary": result.summary,
            "error": result.error,
        }
