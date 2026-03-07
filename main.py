"""Main entry point for the Bluesky feed summarization agent."""

import asyncio
import argparse
from typing import Optional
from dotenv import load_dotenv
import time
import logging
logging.getLogger("httpx").setLevel(logging.WARNING)
from src.bluesky_feed_agent.config import logger
logger.info(f"Program started at {time.strftime('%Y-%m-%d %H:%M:%S')}")
from src.bluesky_feed_agent.agent import run_feed_summary_agent

# Load environment variables from .env file
load_dotenv()


async def main(user_handle: Optional[str] = None) -> None:
    """Run the Bluesky feed summarization agent.

    Args:
        user_handle: Optional Bluesky user handle to summarize their feed.
                     If not provided, summarizes the home feed.
    """
    
    if user_handle:
        logger.info(f"Fetching feed for @{user_handle}...")
    else:
        logger.info("Fetching home feed...")

    result = await run_feed_summary_agent(user_handle=user_handle)

    if result["error"]:
        logger.error(f"Error: {result['error']}")
        logger.info(f"Program ended at {time.strftime('%Y-%m-%d %H:%M:%S')}")
        return

    logger.info(f"Fetched {len(result['posts'])} posts from Bluesky")
    logger.info("GENERATED SUMMARY:\n" + result["summary"])

    if result.get("email_status"):
        logger.info(f"Email status: {result['email_status']}")

    logger.info(f"Program ended at {time.strftime('%Y-%m-%d %H:%M:%S')}")


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
