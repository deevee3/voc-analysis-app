"""Prompt templates for GPT-5 insight extraction."""

from __future__ import annotations

from typing import Any

SYSTEM_PROMPT = """You are an expert Voice of Customer (VoC) analyst specializing in extracting actionable insights from customer feedback. Your task is to analyze customer content and produce structured insights including sentiment, pain points, feature requests, competitor mentions, and contextual information.

Guidelines:
- Be objective and precise in your analysis
- Extract explicit and implicit signals from the text
- Maintain the customer's voice and intent
- Identify patterns and themes
- Flag urgent or critical issues
- Preserve source attribution context"""


SINGLE_EXTRACTION_PROMPT = """Analyze the following customer feedback and extract structured insights.

**Feedback Content:**
{content}

**Metadata:**
- Source: {source}
- Platform: {platform}
- Posted: {posted_at}
- URL: {url}

**Instructions:**
1. Analyze sentiment with score (-1 to 1), label, and confidence
2. Write a concise summary (1-2 sentences) capturing the key message
3. Identify pain points with severity (critical, high, medium, low)
4. Extract feature requests with priority (urgent, high, medium, low)
5. Note competitor mentions with context and sentiment
6. Infer customer context (segment, experience level, domain)
7. Determine journey stage (awareness, consideration, purchase, retention, advocacy)
8. Assign urgency level (1-5 scale)
9. Tag with relevant themes

Return results in the specified JSON schema."""


BATCH_EXTRACTION_PROMPT = """Analyze the following batch of customer feedback items and extract structured insights for each.

**Batch Size:** {batch_size}

**Feedback Items:**
{feedback_items}

**Instructions:**
- Process each feedback item independently
- Apply consistent analysis criteria across all items
- Maintain context awareness for each source
- Return results as an array matching input order

Return results in the specified JSON schema."""


THEME_IDENTIFICATION_PROMPT = """Identify recurring themes across the following customer feedback collection.

**Feedback Collection:**
{feedback_collection}

**Instructions:**
1. Analyze patterns across all feedback
2. Identify 5-10 major themes
3. For each theme:
   - Provide a clear name
   - Write a description
   - Estimate prevalence (percentage)
   - Note sentiment trend

Return themes as a structured list."""


COMPETITOR_ANALYSIS_PROMPT = """Analyze competitor mentions and comparisons in the following feedback.

**Feedback Content:**
{content}

**Known Competitors:** {competitors}

**Instructions:**
1. Identify all competitor mentions (explicit and implicit)
2. Determine comparison context (feature comparison, pricing, UX, switching intent)
3. Assess sentiment toward each competitor
4. Extract specific comparison points
5. Identify switching triggers or retention risks

Return structured competitor analysis."""


def format_single_extraction_prompt(
    content: str,
    source: str,
    platform: str,
    posted_at: str,
    url: str | None = None,
) -> str:
    """Format prompt for single feedback extraction."""
    return SINGLE_EXTRACTION_PROMPT.format(
        content=content,
        source=source,
        platform=platform,
        posted_at=posted_at,
        url=url or "N/A",
    )


def format_batch_extraction_prompt(feedback_items: list[dict[str, Any]]) -> str:
    """Format prompt for batch feedback extraction."""
    formatted_items = []
    for idx, item in enumerate(feedback_items, start=1):
        formatted_items.append(
            f"""
Item {idx}:
Content: {item.get('content', 'N/A')}
Source: {item.get('source', 'N/A')}
Platform: {item.get('platform', 'N/A')}
Posted: {item.get('posted_at', 'N/A')}
---"""
        )

    return BATCH_EXTRACTION_PROMPT.format(
        batch_size=len(feedback_items),
        feedback_items="\n".join(formatted_items),
    )


def format_theme_identification_prompt(feedback_collection: list[str]) -> str:
    """Format prompt for theme identification across feedback."""
    formatted_collection = "\n---\n".join(
        f"Feedback {idx}: {content}" for idx, content in enumerate(feedback_collection, start=1)
    )
    return THEME_IDENTIFICATION_PROMPT.format(feedback_collection=formatted_collection)


def format_competitor_analysis_prompt(content: str, competitors: list[str]) -> str:
    """Format prompt for competitor analysis."""
    return COMPETITOR_ANALYSIS_PROMPT.format(
        content=content,
        competitors=", ".join(competitors) if competitors else "None specified",
    )


def build_extraction_messages(
    prompt: str,
    system_prompt: str = SYSTEM_PROMPT,
) -> list[dict[str, str]]:
    """Build message array for OpenAI API."""
    return [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": prompt},
    ]
