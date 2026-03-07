"""Telegram utilities for sending Bluesky summaries."""

import os

from telegram import Bot

from src.bluesky_feed_agent.config import logger


async def send_summary_to_telegram(
    summary: str, audio_path: str | None = None
) -> str:
    """Send summary text and optional MP3 audio to a Telegram chat.

    Requires environment variables:
        TELEGRAM_BOT_TOKEN: Bot API token from BotFather
        TELEGRAM_CHAT_ID: Target chat/group ID

    Args:
        summary: Summary text to send
        audio_path: Optional path to an MP3 file to send

    Returns:
        Status string: "sent", "skipped", or error message
    """
    bot_token = os.getenv("TELEGRAM_BOT_TOKEN", "")
    chat_id = os.getenv("TELEGRAM_CHAT_ID", "")

    if not bot_token or not chat_id:
        return "skipped: TELEGRAM_BOT_TOKEN or TELEGRAM_CHAT_ID not set"

    bot = Bot(token=bot_token)

    # Send MP3 audio only
    if audio_path and os.path.exists(audio_path):
        with open(audio_path, "rb") as audio:
            await bot.send_audio(chat_id=chat_id, audio=audio, title="Bluesky Feed Summary")
        logger.info("Telegram: audio file sent to chat %s", chat_id)
        return "sent"

    return "skipped: no audio file available"
