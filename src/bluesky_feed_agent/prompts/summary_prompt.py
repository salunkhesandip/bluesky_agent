"""Prompts for feed summarization."""


SYSTEM_PROMPT = """You are a helpful assistant that summarizes Bluesky feed posts into a concise daily summary.

Your task is to:
1. Start with day and date and a brief overview of the feed's main themes
2. Read the provided Bluesky feed posts
3. Identify key themes and topics
4. Create a well-organized daily summary
5. Highlight the most important or engaging posts
6. Include personalities or notable users if they are relevant to the feed's content
7. Use persons names instead of handles when possible
8. Keep the summary to 3-7 paragraphs

Format the summary to be engaging and informative."""


SUMMARY_PROMPT_TEMPLATE = """{system_prompt}

Here are the Bluesky feed posts to summarize:

{feed_content}

Please provide a daily summary of this feed. Focus on the main topics, notable posts, and interesting discussions."""


def get_summary_prompt(feed_content: str, system_prompt: str = SYSTEM_PROMPT) -> str:
    """Format the summary prompt with feed content.

    Args:
        feed_content: Formatted feed posts
        system_prompt: System prompt for the LLM

    Returns:
        Formatted prompt for the LLM
    """
    return SUMMARY_PROMPT_TEMPLATE.format(
        system_prompt=system_prompt, feed_content=feed_content
    )
