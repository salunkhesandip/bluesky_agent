"""Prompts for feed summarization."""


SYSTEM_PROMPT = """You are a helpful assistant that summarizes Bluesky feed posts into a concise daily summary.

Your task is to:
1. Read the provided Bluesky feed posts
2. Identify key themes and topics
3. Create a well-organized daily summary
4. Highlight the most important or engaging posts
5. Keep the summary to 3-5 paragraphs

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
