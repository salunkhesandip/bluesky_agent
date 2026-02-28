"""Main entry point for the Bluesky feed summarization agent."""

import asyncio
import argparse
from typing import Optional
from dotenv import load_dotenv

from src.bluesky_feed_agent.agent import run_feed_summary_agent

# Load environment variables from .env file
load_dotenv()


async def main(user_handle: Optional[str] = None) -> None:
    """Run the Bluesky feed summarization agent.

    Args:
        user_handle: Optional Bluesky user handle to summarize their feed.
                     If not provided, summarizes the home feed.
    """
    print("Starting Bluesky Feed Summarization Agent...")
    print()

    if user_handle:
        print(f"Fetching feed for @{user_handle}...")
    else:
        print("Fetching home feed...")

    result = await run_feed_summary_agent(user_handle=user_handle)

    if result["error"]:
        print(f"Error: {result['error']}")
        return

    print(f"\nFetched {len(result['posts'])} posts from Bluesky")
    print("\n" + "=" * 70)
    print("GENERATED SUMMARY")
    print("=" * 70)
    print(result["summary"])
    print("=" * 70)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Summarize Bluesky feed with AI"
    )
    parser.add_argument(
        "--user",
        type=str,
        help="Bluesky user handle to fetch feed from (default: home feed)",
        default=None,
    )

    args = parser.parse_args()

    asyncio.run(main(user_handle=args.user))
