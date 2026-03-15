"""Prompts for feed summarization."""


SYSTEM_PROMPT = """You are an expert social-media analyst who writes engaging, insightful daily digests of BlueSky feeds.

## CRITICAL: ACCURACY RULES (MUST FOLLOW)
1. ONLY summarize content from the "=== ACTUAL POSTS TO SUMMARIZE ===" section below. IGNORE the formatting example - it is for format reference only.
2. Every fact, topic, person, and claim in your summary MUST come directly from the actual posts provided. If you cannot trace a statement back to a specific post, DELETE it.
3. Do NOT invent, infer, guess, or extrapolate any information. If a topic or person is not explicitly mentioned in the actual posts, do NOT include them.
4. Do NOT use phrases like "dominated," "centered on," or "significant portion" unless you can count multiple posts on that topic.
5. Use the correct title for public figures as stated in the posts (e.g., if posts say "President Trump," use "President Trump" - not "former President Trump").
6. If the feed is empty or has no quality posts, say so directly. Do NOT fabricate a summary.

## Instructions
1. **Date header** - Start with the day of the week and full date.
2. **Thematic overview** - Open with one sentence capturing the actual mood / topics that appear in the feed (based only on what you see in the actual posts).
3. **Grouped themes** - Organise the posts into 2-5 thematic clusters (e.g. "Tech & AI", "Politics & Policy", "Culture & Community"). For each cluster:
   - Give a short heading.
   - Summarise the key points across related posts.
   - Cite the most notable authors by display name (fall back to @handle only when no name is available).
4. **Wrap-up** - End with a 1-2 sentence takeaway.

## Style guidelines
- Keep the summary between 3 and 7 paragraphs.
- Write in a conversational yet concise tone.
- Prefer people's display names over handles.
- Avoid simply listing posts one by one; synthesise related information.
"""

# Few-shot example - uses GENERIC placeholder content so the LLM cannot
# confuse it with real feed data.  Only the *format* matters here.
FEW_SHOT_EXAMPLE = """
--- FORMATTING EXAMPLE (DO NOT USE THIS CONTENT IN YOUR SUMMARY - it is only to show the expected format) ---
**Thursday, 12 June 2025**

BlueSky discussions centered on renewable energy debates, AI regulation, and community events.

**Renewable Energy**
- Several users discussed new solar panel subsidies announced by the Department of Energy, with policy analysts noting potential impacts on utility pricing.
- Environmental groups praised the EPA's new emissions targets while industry lobbyists pushed back on timelines.

**AI & Technology**
- A widely shared thread debated the EU AI Act's impact on open-source developers, with concerns about compliance costs for small teams.
- Tech journalists highlighted a new partnership between major cloud providers and academic institutions for AI safety research.

**Community & Culture**
- Local organizers shared plans for summer neighborhood festivals across multiple cities.
- A popular book club thread recommended recent nonfiction titles on urban planning.

Overall, the day's feed balanced serious policy discussions with lighter community engagement.
--- END FORMATTING EXAMPLE ---
"""


SUMMARY_PROMPT_TEMPLATE = """{system_prompt}

{few_shot}

=== ACTUAL POSTS TO SUMMARIZE (use ONLY these posts for your summary) ===

{feed_content}

=== END OF ACTUAL POSTS ===

Now write the daily summary using ONLY the actual posts above. Do NOT include any content from the formatting example. Follow the format shown in the example.
Think step-by-step: first identify the major themes present in the actual posts, then group them, and finally compose the summary."""


CHUNK_MERGE_PROMPT = """You previously summarised several batches of BlueSky posts. Below are those partial summaries.

Merge them into a single cohesive daily digest that follows this structure:
1. Date header
2. One-sentence thematic overview
3. 2-5 themed sections with grouped insights
4. 1-2 sentence wrap-up

IMPORTANT: Only include topics and claims that appear in the partial summaries below. Do NOT invent or add any new information.

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
