"""Utility functions for the agent."""

import os
from typing import Optional


def get_bluesky_credentials() -> tuple[str, str]:
    """Get Bluesky credentials from environment variables.

    Returns:
        Tuple of (username, password)

    Raises:
        ValueError: If credentials are not set
    """
    username = os.getenv("BLUESKY_USERNAME")
    password = os.getenv("BLUESKY_PASSWORD")

    if not username or not password:
        raise ValueError(
            "Please set BLUESKY_USERNAME and BLUESKY_PASSWORD environment variables"
        )

    return username, password


def get_openai_api_key() -> str:
    """Get Google Generative AI API key from environment.

    Returns:
        Google API key for Generative AI

    Raises:
        ValueError: If API key is not set
    """
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        raise ValueError("Please set GOOGLE_API_KEY environment variable")
    return api_key
