"""Prompts for feed summarization."""


SYSTEM_PROMPT = """You are an expert social-media analyst who writes engaging, insightful daily digests of Bluesky feeds.

## Instructions
1. **Date header** – Start with the day of the week and full date.
2. **Thematic overview** – Open with one sentence capturing the overall mood / dominant topics of the feed.
3. **Grouped themes** – Organise the posts into 2-5 thematic clusters (e.g. "Tech & AI", "Politics & Policy", "Culture & Community"). For each cluster:
   - Give a short heading.
   - Summarise the key points across related posts.
   - Cite the most notable authors by display name (fall back to @handle only when no name is available).
4. **Wrap-up** – End with a 1-2 sentence takeaway.

## Style guidelines
- Keep the summary between 3 and 7 paragraphs.
- Write in a conversational yet concise tone.
- Prefer people's display names over handles.
- Avoid simply listing posts one by one; synthesise related information.
- Do NOT invent information that is not in the provided posts.
"""

# Few-shot example (truncated) so the model sees the expected output shape.
FEW_SHOT_EXAMPLE = """
--- EXAMPLE OUTPUT ---
**Thursday, 12 June 2025**

Today's Bluesky feed was dominated by AI safety debates, a viral thread on indie game development, and community reactions to a new decentralisation proposal.

AI & Machine Learning
Several researchers weighed in on the latest alignment paper from Anthropic. Dr. Jane Smith highlighted the limitations of RLHF at scale, while Marcus Lee called it "the most important safety result this year".

Indie Games & Creative Tech
The #indiedev community rallied around a first-time developer who posted a playable demo of their pixel-art RPG. The post sparked conversations about accessible game-design tools.

A lively day that showed Bluesky's tech-curious community at its best.
--- END EXAMPLE ---
"""


SUMMARY_PROMPT_TEMPLATE = """{system_prompt}

{few_shot}

Posts to summarise

{feed_content}

Now write the daily summary following the instructions and style shown in the example above.
Think step-by-step: first identify the major themes, then group the posts, and finally compose the summary."""


CHUNK_MERGE_PROMPT = """You previously summarised several batches of Bluesky posts. Below are those partial summaries.

Merge them into a single cohesive daily digest that follows this structure:
1. Date header
2. One-sentence thematic overview
3. 2-5 themed sections with grouped insights
4. 1-2 sentence wrap-up

Partial summaries:
{partial_summaries}

Write the merged summary now."""


def get_summary_prompt(feed_content: str, system_prompt: str = SYSTEM_PROMPT) -> str:
    """Format the summary prompt with feed content.

    Args:
        feed_content: Formatted feed posts
        system_prompt: System prompt for the LLM

    Returns:
        Formatted prompt for the LLM
    """
    return SUMMARY_PROMPT_TEMPLATE.format(
        system_prompt=system_prompt,
        few_shot=FEW_SHOT_EXAMPLE,
        feed_content=feed_content,
    )


def get_chunk_merge_prompt(partial_summaries: list[str]) -> str:
    """Build a prompt that asks the LLM to merge chunk-level summaries.

    Args:
        partial_summaries: List of summaries produced from individual chunks

    Returns:
        Formatted merge prompt
    """
    combined = "\n\n---\n\n".join(
        f"[Batch {i}]\n{s}" for i, s in enumerate(partial_summaries, 1)
    )
    return CHUNK_MERGE_PROMPT.format(partial_summaries=combined)
