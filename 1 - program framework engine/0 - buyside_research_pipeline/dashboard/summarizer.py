"""
Thesis Evolution Summarizer
===========================
Generates concise summaries of thesis evolution using gpt-4o-mini.

Called after each iteration to provide a 2-3 sentence summary of:
- What thesis emerged/evolved
- What debates arose between analysts
- What key shifts occurred
"""

import asyncio
import logging
from typing import Dict, Optional

logger = logging.getLogger(__name__)

# Summary prompt template
SUMMARY_SYSTEM_PROMPT = """You are a concise financial analyst summarizer. Your task is to distill complex investment debates into clear, 2-3 sentence summaries.

Focus on:
1. The emerging or evolving investment thesis
2. Key points of agreement or disagreement between analysts
3. Critical concerns raised (especially kill conditions or risk factors)

Write in present tense, professional tone. Be specific about the thesis and debates. Never exceed 3 sentences."""

SUMMARY_USER_TEMPLATE = """Summarize the thesis evolution for iteration {iteration}.

Previous summary: {previous_summary}

Analyst conclusions:
{analyst_excerpts}

RD critiques:
{rd_excerpts}

Write a 2-3 sentence summary capturing: What thesis is emerging? What debates arose? What shifted?"""


async def generate_thesis_summary(
    iteration: int,
    analyst_reports: Dict[int, str],
    rd_critiques: Dict[int, str],
    previous_summary: Optional[str] = None,
    provider_factory: Optional["ProviderFactory"] = None,
) -> str:
    """Generate a thesis evolution summary for an iteration.

    Args:
        iteration: Current iteration number (1-5)
        analyst_reports: Dict mapping type_id -> analyst report content
        rd_critiques: Dict mapping type_id -> RD critique content
        previous_summary: Summary from the previous iteration (if any)
        provider_factory: Optional ProviderFactory instance. If None, creates one.

    Returns:
        A 2-3 sentence summary of the thesis evolution
    """
    try:
        # Extract key excerpts from reports
        analyst_excerpts = _extract_analyst_excerpts(analyst_reports)
        rd_excerpts = _extract_rd_excerpts(rd_critiques)

        # Build the prompt
        user_prompt = SUMMARY_USER_TEMPLATE.format(
            iteration=iteration,
            previous_summary=previous_summary or "None (first iteration)",
            analyst_excerpts=analyst_excerpts,
            rd_excerpts=rd_excerpts,
        )

        # Get provider
        if provider_factory is None:
            # Create a minimal provider factory for just this call
            from providers import ProviderFactory
            provider_factory = ProviderFactory()

        # Generate summary using gpt-4o-mini (fast, cheap, good at summarization)
        response = await provider_factory.generate(
            provider_type="openai",
            model="gpt-4o-mini",
            system_prompt=SUMMARY_SYSTEM_PROMPT,
            user_prompt=user_prompt,
            max_tokens=300,
            temperature=0.3,  # Lower temperature for consistency
        )

        summary = response.content.strip()
        logger.info(f"Generated thesis summary for iteration {iteration}: {len(summary)} chars")
        return summary

    except Exception as e:
        logger.error(f"Failed to generate thesis summary: {e}")
        # Return a fallback summary
        return f"Iteration {iteration} completed. Analysts continued debate on investment thesis."


def _extract_analyst_excerpts(reports: Dict[int, str], max_chars_per_report: int = 500) -> str:
    """Extract key excerpts from analyst reports.

    Focuses on conclusions and recommendations.
    """
    analyst_names = {
        1: "Quality Compounders",
        2: "Imaginative Growth",
        3: "Fundamental L/S",
        4: "Deep Value",
        5: "Event-Driven",
        6: "Macro-Tactical",
    }

    excerpts = []
    for type_id, content in reports.items():
        name = analyst_names.get(type_id, f"Analyst {type_id}")

        # Try to extract conclusion section
        excerpt = _extract_section(content, ["conclusion", "recommendation", "thesis", "verdict"])
        if not excerpt:
            # Fallback: take the last few paragraphs
            paragraphs = [p.strip() for p in content.split("\n\n") if p.strip()]
            excerpt = "\n".join(paragraphs[-2:]) if len(paragraphs) >= 2 else content

        # Truncate if too long
        if len(excerpt) > max_chars_per_report:
            excerpt = excerpt[:max_chars_per_report] + "..."

        excerpts.append(f"**{name}**: {excerpt}")

    return "\n\n".join(excerpts)


def _extract_rd_excerpts(critiques: Dict[int, str], max_chars_per_critique: int = 300) -> str:
    """Extract key critiques from RD reviews.

    Focuses on disagreements, concerns, and recommendations.
    """
    excerpts = []
    for type_id, content in critiques.items():
        # Try to extract key critique sections
        excerpt = _extract_section(content, ["concerns", "disagree", "challenge", "risk", "weakness"])
        if not excerpt:
            # Fallback: take first substantive paragraph
            paragraphs = [p.strip() for p in content.split("\n\n") if p.strip() and len(p) > 50]
            excerpt = paragraphs[0] if paragraphs else content[:max_chars_per_critique]

        # Truncate if too long
        if len(excerpt) > max_chars_per_critique:
            excerpt = excerpt[:max_chars_per_critique] + "..."

        excerpts.append(f"RD {type_id}: {excerpt}")

    return "\n\n".join(excerpts)


def _extract_section(content: str, keywords: list, context_chars: int = 500) -> str:
    """Extract a section of content containing any of the keywords.

    Args:
        content: Full report content
        keywords: List of section header keywords to look for
        context_chars: How many characters of context to extract

    Returns:
        Extracted section or empty string if not found
    """
    content_lower = content.lower()

    for keyword in keywords:
        # Look for section header
        idx = content_lower.find(f"## {keyword}")
        if idx == -1:
            idx = content_lower.find(f"# {keyword}")
        if idx == -1:
            idx = content_lower.find(f"**{keyword}")

        if idx != -1:
            # Extract from this point
            section = content[idx:idx + context_chars]
            # Try to end at a sentence boundary
            last_period = section.rfind(".")
            if last_period > context_chars // 2:
                section = section[:last_period + 1]
            return section.strip()

    return ""


# Synchronous wrapper for non-async contexts
def generate_thesis_summary_sync(
    iteration: int,
    analyst_reports: Dict[int, str],
    rd_critiques: Dict[int, str],
    previous_summary: Optional[str] = None,
    provider_factory: Optional["ProviderFactory"] = None,
) -> str:
    """Synchronous wrapper for generate_thesis_summary."""
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

    return loop.run_until_complete(
        generate_thesis_summary(
            iteration=iteration,
            analyst_reports=analyst_reports,
            rd_critiques=rd_critiques,
            previous_summary=previous_summary,
            provider_factory=provider_factory,
        )
    )
