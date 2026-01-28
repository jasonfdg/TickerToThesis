#!/usr/bin/env python3
"""
Debate History Tracking System
==============================
Manages per-analyst debate history JSON files to capture the evolution arc
of analyst <-> Research Director debates across iterations.

Key Features:
- LLM-based extraction (Haiku) for robust handling of format variations
- Per-analyst files to avoid cross-pollution
- Structured format: key claims, critiques, resolutions
- ~150 tokens/iteration target for efficient context use
- Markdown injection for both analyst and RD prompts
"""

import json
import logging
import os
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

# Support both module and direct script execution
try:
    from .config import INVESTING_TYPES
except ImportError:
    from config import INVESTING_TYPES

logger = logging.getLogger(__name__)


# Schema version for debate history files
SCHEMA_VERSION = "1.1"  # Bumped for LLM-based extraction


@dataclass
class AnalystEntry:
    """Extracted data from an analyst report."""
    thesis_statement: str = ""
    key_claims: List[str] = field(default_factory=list)
    stance: str = ""  # LONG, SHORT, PASS
    target_price: Optional[float] = None
    conviction: str = ""  # high, medium, low


@dataclass
class RDEntry:
    """Extracted data from an RD review."""
    engagement_score: Optional[float] = None
    engagement_quality: str = ""  # Thorough, Adequate, Superficial, Dismissive
    top_critiques: List[str] = field(default_factory=list)
    acknowledged_strengths: List[str] = field(default_factory=list)
    overall_score: Optional[float] = None


@dataclass
class Resolution:
    """Resolution of critiques from analyst response."""
    accepted: List[str] = field(default_factory=list)
    rejected: List[str] = field(default_factory=list)
    key_pivot: str = ""


class DebateHistoryExtractor:
    """LLM-based extraction from analyst/RD reports using Gemini Flash Lite.

    Uses Gemini Flash Lite for fast, cheap, and robust extraction that handles
    format variations naturally without brittle regex patterns.
    """

    # Extraction prompts
    ANALYST_EXTRACTION_PROMPT = """Extract the following from this analyst investment report. Return ONLY valid JSON, no other text.

Report:
{content}

Extract and return this JSON structure:
{{
    "stance": "LONG" or "SHORT" or "PASS" (the analyst's recommendation),
    "thesis_statement": "1-2 sentence summary of the core thesis",
    "key_claims": ["claim 1", "claim 2", "claim 3"] (top 3 key forces or arguments, max 80 chars each),
    "target_price": number or null (the target/action price if mentioned),
    "conviction": "high" or "medium" or "low" (inferred from language)
}}

Rules:
- For stance: What is the CURRENT recommendation at TODAY's price?
  - "Pass at $X" or "Hold" or "Wait" or "Avoid" = PASS (even if "Buy below $Y" is mentioned)
  - "Buy" or "Long" (unconditional) = LONG
  - "Sell" or "Short" = SHORT
- For thesis_statement: Extract the core investment thesis, not the full section.
- For key_claims: Focus on the 1-3 key forces that drive the thesis.
- For target_price: The conditional price (e.g., "Buy below $9" → 9, "Pass at $11.50" → 11.50).
- Return ONLY the JSON object, no markdown formatting or explanation."""

    RD_EXTRACTION_PROMPT = """Extract the following from this Research Director review. Return ONLY valid JSON, no other text.

Review:
{content}

Extract and return this JSON structure:
{{
    "overall_score": number or null (X/10 score if mentioned),
    "engagement_score": number or null (engagement assessment score if this is iteration 2+),
    "engagement_quality": "Thorough" or "Adequate" or "Superficial" or "Dismissive" or "" (if mentioned),
    "top_critiques": ["critique 1", "critique 2", "critique 3"] (top 3 critiques/weaknesses, max 100 chars each),
    "acknowledged_strengths": ["strength 1", "strength 2"] (top 2 things the analyst got right, max 80 chars each)
}}

Rules:
- For top_critiques: Extract the main gaps, weaknesses, or challenges raised. Be specific.
- For acknowledged_strengths: Extract what the RD praised or credited.
- Return ONLY the JSON object, no markdown formatting or explanation."""

    RESOLUTION_EXTRACTION_PROMPT = """Extract how this analyst responded to RD critique. Return ONLY valid JSON, no other text.

Analyst Report (with response to RD critique):
{content}

Extract and return this JSON structure:
{{
    "accepted": ["critique 1 they accepted", "critique 2 they accepted"] (critiques the analyst agreed with and addressed),
    "rejected": ["critique 1 they defended against"] (critiques the analyst disagreed with and defended their position),
    "key_pivot": "description of main change" or "" (the most significant change in thinking, max 120 chars)
}}

Rules:
- Look for "Response to Research Director" or similar sections.
- For accepted: Critiques marked "Accept" or where analyst acknowledged error.
- For rejected: Critiques marked "Reject" or where analyst defended their position.
- For key_pivot: Look for "What I Got Wrong" or major thesis changes.
- Return ONLY the JSON object, no markdown formatting or explanation."""

    def __init__(self, provider_factory=None):
        """Initialize the extractor.

        Args:
            provider_factory: Optional ProviderFactory for API calls.
                             If None, will create one on first use.
        """
        self._provider_factory = provider_factory
        self._client = None

        # Load environment variables for API key
        try:
            from dotenv import load_dotenv
            env_path = Path(__file__).parent / ".env"
            if env_path.exists():
                load_dotenv(env_path)
        except ImportError:
            pass  # dotenv not available, assume env vars are set

    def _get_client(self):
        """Get or create Gemini client for Flash Lite calls."""
        if self._client is None:
            try:
                from google import genai
                api_key = os.environ.get("GOOGLE_API_KEY")
                if not api_key:
                    logger.error("GOOGLE_API_KEY not set")
                    raise ValueError("GOOGLE_API_KEY environment variable required")
                self._client = genai.Client(api_key=api_key)
            except ImportError:
                logger.error("google-genai package not installed")
                raise
        return self._client

    def _call_llm(self, prompt: str) -> str:
        """Make a synchronous Gemini Flash Lite call for extraction.

        Args:
            prompt: The extraction prompt with content embedded

        Returns:
            Raw response text from Gemini
        """
        client = self._get_client()

        try:
            from google import genai
            gen_config = genai.types.GenerateContentConfig(
                max_output_tokens=1024,
                temperature=0.1,  # Low temp for consistent extraction
            )
            response = client.models.generate_content(
                model="models/gemini-2.5-flash-lite",
                contents=prompt,
                config=gen_config,
            )
            return response.text if response.text else "{}"
        except Exception as e:
            logger.error(f"Gemini extraction failed: {e}")
            return "{}"

    def _parse_json_response(self, response: str, default: Dict) -> Dict:
        """Parse JSON from LLM response with fallback.

        Args:
            response: Raw LLM response
            default: Default dict to return on failure

        Returns:
            Parsed JSON dict or default
        """
        # Clean up response - remove markdown code blocks if present
        cleaned = response.strip()
        if cleaned.startswith("```"):
            # Remove ```json and ``` markers
            lines = cleaned.split("\n")
            cleaned = "\n".join(lines[1:-1] if lines[-1].strip() == "```" else lines[1:])

        try:
            return json.loads(cleaned)
        except json.JSONDecodeError as e:
            logger.warning(f"Failed to parse extraction response: {e}")
            logger.debug(f"Response was: {response[:200]}...")
            return default

    def extract_analyst_entry(self, content: str, iteration: int) -> AnalystEntry:
        """Extract structured data from an analyst report.

        Args:
            content: Full analyst report content (markdown)
            iteration: Current iteration number

        Returns:
            AnalystEntry with extracted data
        """
        # Truncate content to reduce tokens (first 4000 chars usually has key info)
        truncated = content[:6000] if len(content) > 6000 else content

        prompt = self.ANALYST_EXTRACTION_PROMPT.format(content=truncated)
        response = self._call_llm(prompt)

        default = {
            "stance": "",
            "thesis_statement": "",
            "key_claims": [],
            "target_price": None,
            "conviction": "medium",
        }
        data = self._parse_json_response(response, default)

        return AnalystEntry(
            thesis_statement=str(data.get("thesis_statement", ""))[:300],
            key_claims=[str(c)[:100] for c in data.get("key_claims", [])[:3]],
            stance=str(data.get("stance", "")).upper(),
            target_price=data.get("target_price"),
            conviction=str(data.get("conviction", "medium")).lower(),
        )

    def extract_rd_entry(self, content: str) -> RDEntry:
        """Extract structured data from an RD review.

        Args:
            content: Full RD review content (markdown)

        Returns:
            RDEntry with extracted data
        """
        # Truncate content to reduce tokens
        truncated = content[:6000] if len(content) > 6000 else content

        prompt = self.RD_EXTRACTION_PROMPT.format(content=truncated)
        response = self._call_llm(prompt)

        default = {
            "overall_score": None,
            "engagement_score": None,
            "engagement_quality": "",
            "top_critiques": [],
            "acknowledged_strengths": [],
        }
        data = self._parse_json_response(response, default)

        return RDEntry(
            engagement_score=data.get("engagement_score"),
            engagement_quality=str(data.get("engagement_quality", "")),
            top_critiques=[str(c)[:150] for c in data.get("top_critiques", [])[:3]],
            acknowledged_strengths=[str(s)[:100] for s in data.get("acknowledged_strengths", [])[:2]],
            overall_score=data.get("overall_score"),
        )

    def extract_resolution(self, content: str) -> Resolution:
        """Extract resolution info from analyst's response to RD critique.

        Args:
            content: Analyst report content with response section

        Returns:
            Resolution tracking accepted/rejected critiques
        """
        # Look for response section specifically (first 5000 chars should have it)
        truncated = content[:5000] if len(content) > 5000 else content

        prompt = self.RESOLUTION_EXTRACTION_PROMPT.format(content=truncated)
        response = self._call_llm(prompt)

        default = {
            "accepted": [],
            "rejected": [],
            "key_pivot": "",
        }
        data = self._parse_json_response(response, default)

        return Resolution(
            accepted=[str(a)[:100] for a in data.get("accepted", [])[:3]],
            rejected=[str(r)[:100] for r in data.get("rejected", [])[:2]],
            key_pivot=str(data.get("key_pivot", ""))[:150],
        )


class DebateHistoryManager:
    """Manages per-analyst debate history JSON files.

    Creates and maintains debate history files that track:
    - Thesis evolution (stance changes, conviction arc)
    - Key debates between analyst and RD
    - Resolutions and pivots

    Files are stored in the interim directory with naming:
    analyst_{short_name}_rd_debate_history.json
    """

    def __init__(self, ticker: str, interim_dir: Path, provider_factory=None):
        """Initialize the manager.

        Args:
            ticker: Stock ticker symbol
            interim_dir: Path to interim directory for storing history files
            provider_factory: Optional ProviderFactory for LLM extraction
        """
        self.ticker = ticker.upper()
        self.interim_dir = Path(interim_dir)
        self.extractor = DebateHistoryExtractor(provider_factory)

        # Ensure interim directory exists
        self.interim_dir.mkdir(parents=True, exist_ok=True)

    def _get_history_path(self, type_id: int) -> Path:
        """Get the path to debate history file for an analyst type.

        Args:
            type_id: Analyst type ID (1-6)

        Returns:
            Path to the debate history JSON file
        """
        short_name = INVESTING_TYPES.get(type_id, {}).get("short_name", f"type_{type_id}")
        return self.interim_dir / f"analyst_{short_name}_rd_debate_history.json"

    def _get_analyst_name(self, type_id: int) -> str:
        """Get human-readable analyst name for type ID.

        Args:
            type_id: Analyst type ID (1-6)

        Returns:
            Human-readable analyst name
        """
        return INVESTING_TYPES.get(type_id, {}).get("name", f"Analyst {type_id}")

    def load_history(self, type_id: int) -> Dict[str, Any]:
        """Load debate history for an analyst type.

        Args:
            type_id: Analyst type ID (1-6)

        Returns:
            Debate history dict, or empty structure if file doesn't exist
        """
        path = self._get_history_path(type_id)

        if path.exists():
            try:
                return json.loads(path.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, IOError) as e:
                logger.warning(f"Failed to load debate history from {path}: {e}")

        # Return empty structure
        return self._create_empty_history(type_id)

    def _create_empty_history(self, type_id: int) -> Dict[str, Any]:
        """Create empty debate history structure.

        Args:
            type_id: Analyst type ID (1-6)

        Returns:
            Empty debate history dict conforming to schema
        """
        return {
            "ticker": self.ticker,
            "analyst_type": type_id,
            "analyst_name": self._get_analyst_name(type_id),
            "schema_version": SCHEMA_VERSION,
            "created_at": datetime.now().isoformat(),
            "thesis_evolution": {
                "initial_stance": None,
                "current_stance": None,
                "stance_history": [],
                "conviction_arc": [],
            },
            "debate_entries": [],
        }

    def save_history(self, type_id: int, data: Dict[str, Any]) -> None:
        """Save debate history to file.

        Args:
            type_id: Analyst type ID (1-6)
            data: Debate history dict to save
        """
        path = self._get_history_path(type_id)

        # Update timestamp
        data["updated_at"] = datetime.now().isoformat()

        try:
            path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
            logger.debug(f"Saved debate history to {path}")
        except IOError as e:
            logger.error(f"Failed to save debate history to {path}: {e}")

    def append_analyst_entry(self, type_id: int, iteration: int, content: str) -> None:
        """Append analyst report data to debate history.

        Args:
            type_id: Analyst type ID (1-6)
            iteration: Current iteration number
            content: Full analyst report content
        """
        history = self.load_history(type_id)

        # Extract data from analyst report using LLM
        analyst_entry = self.extractor.extract_analyst_entry(content, iteration)
        resolution = self.extractor.extract_resolution(content) if iteration > 1 else Resolution()

        # Update thesis evolution
        evolution = history["thesis_evolution"]
        if analyst_entry.stance:
            evolution["stance_history"].append(analyst_entry.stance)
            if evolution["initial_stance"] is None:
                evolution["initial_stance"] = analyst_entry.stance
            evolution["current_stance"] = analyst_entry.stance

        if analyst_entry.conviction:
            evolution["conviction_arc"].append(analyst_entry.conviction)

        # Find or create debate entry for this iteration
        debate_entry = None
        for entry in history["debate_entries"]:
            if entry.get("iteration") == iteration:
                debate_entry = entry
                break

        if debate_entry is None:
            debate_entry = {"iteration": iteration}
            history["debate_entries"].append(debate_entry)

        # Add analyst entry
        debate_entry["analyst_entry"] = {
            "thesis_statement": analyst_entry.thesis_statement,
            "key_claims": analyst_entry.key_claims,
            "stance": analyst_entry.stance,
            "target_price": analyst_entry.target_price,
            "conviction": analyst_entry.conviction,
        }

        # Add resolution if iteration > 1
        if iteration > 1:
            debate_entry["resolution"] = {
                "accepted": resolution.accepted,
                "rejected": resolution.rejected,
                "key_pivot": resolution.key_pivot,
            }

        self.save_history(type_id, history)
        logger.info(f"Appended analyst entry for type {type_id}, iteration {iteration}")

    def append_rd_entry(self, type_id: int, iteration: int, content: str) -> None:
        """Append RD review data to debate history.

        Args:
            type_id: Analyst type ID (1-6)
            iteration: Current iteration number
            content: Full RD review content
        """
        history = self.load_history(type_id)

        # Extract data from RD review using LLM
        rd_entry = self.extractor.extract_rd_entry(content)

        # Find or create debate entry for this iteration
        debate_entry = None
        for entry in history["debate_entries"]:
            if entry.get("iteration") == iteration:
                debate_entry = entry
                break

        if debate_entry is None:
            debate_entry = {"iteration": iteration}
            history["debate_entries"].append(debate_entry)

        # Add RD entry
        debate_entry["rd_entry"] = {
            "engagement_score": rd_entry.engagement_score,
            "engagement_quality": rd_entry.engagement_quality,
            "top_critiques": rd_entry.top_critiques,
            "acknowledged_strengths": rd_entry.acknowledged_strengths,
            "overall_score": rd_entry.overall_score,
        }

        self.save_history(type_id, history)
        logger.info(f"Appended RD entry for type {type_id}, iteration {iteration}")

    def format_for_analyst_prompt(self, type_id: int) -> str:
        """Format debate history as markdown for injection into analyst prompts.

        Args:
            type_id: Analyst type ID (1-6)

        Returns:
            Formatted markdown string for prompt injection
        """
        history = self.load_history(type_id)

        # Skip if no debate entries yet
        if not history["debate_entries"]:
            return ""

        lines = []
        lines.append("## Your Debate History with Research Director\n")

        # Thesis arc summary
        evolution = history["thesis_evolution"]
        if evolution["stance_history"]:
            stance_arc = " -> ".join([
                f"{s} (v{i+1})" if i > 0 else s
                for i, s in enumerate(evolution["stance_history"])
            ])
            lines.append(f"**Thesis Arc:** {stance_arc}")

        if evolution["conviction_arc"]:
            conviction_arc = " -> ".join(evolution["conviction_arc"])
            lines.append(f"**Conviction:** {conviction_arc}")

        lines.append("")
        lines.append("### Key Debates:\n")

        # Format each debate entry
        for entry in history["debate_entries"]:
            iteration = entry.get("iteration", 0)
            if iteration <= 1:
                continue  # Skip v1, no debate yet

            lines.append(f"**v{iteration-1} -> v{iteration}:**")

            # RD critiques from previous iteration
            rd_entry = entry.get("rd_entry", {})
            critiques = rd_entry.get("top_critiques", [])
            for critique in critiques[:2]:
                lines.append(f"- RD: \"{critique}\"")

            # Resolution from analyst response
            resolution = entry.get("resolution", {})
            for accepted in resolution.get("accepted", [])[:2]:
                lines.append(f"- You accepted: {accepted}")
            for rejected in resolution.get("rejected", [])[:1]:
                lines.append(f"- You defended: {rejected}")

            if resolution.get("key_pivot"):
                lines.append(f"- Key pivot: {resolution['key_pivot']}")

            lines.append("")

        return "\n".join(lines)

    def format_for_rd_prompt(self, type_id: int) -> str:
        """Format debate history as markdown for injection into RD prompts.

        Args:
            type_id: Analyst type ID (1-6)

        Returns:
            Formatted markdown string for prompt injection
        """
        history = self.load_history(type_id)

        # Skip if no debate entries yet
        if not history["debate_entries"]:
            return ""

        analyst_name = history.get("analyst_name", f"Analyst {type_id}")
        lines = []
        lines.append(f"### Debate History with {analyst_name}\n")

        # Thesis arc summary
        evolution = history["thesis_evolution"]
        if evolution["stance_history"]:
            stance_arc = " -> ".join([
                f"{s} (v{i+1})" if i > 0 else s
                for i, s in enumerate(evolution["stance_history"])
            ])
            lines.append(f"**Thesis Arc:** {stance_arc}")

        # Engagement quality summary
        engagement_scores = []
        for entry in history["debate_entries"]:
            rd_entry = entry.get("rd_entry", {})
            if rd_entry.get("engagement_score"):
                try:
                    engagement_scores.append(int(rd_entry["engagement_score"]))
                except (ValueError, TypeError):
                    pass  # Skip invalid scores

        if engagement_scores:
            avg_score = sum(engagement_scores) / len(engagement_scores)
            qualities = [entry.get("rd_entry", {}).get("engagement_quality", "")
                        for entry in history["debate_entries"]
                        if entry.get("rd_entry", {}).get("engagement_quality")]
            quality_arc = " -> ".join(qualities) if qualities else "N/A"
            lines.append(f"**Engagement Quality:** {avg_score:.1f}/10 avg ({quality_arc})")

        lines.append("")
        lines.append("### Key Debates:\n")

        # Format debate history
        for entry in history["debate_entries"]:
            iteration = entry.get("iteration", 0)
            if iteration <= 1:
                continue

            lines.append(f"**v{iteration-1} -> v{iteration}:**")

            # What you critiqued
            rd_entry = entry.get("rd_entry", {})
            critiques = rd_entry.get("top_critiques", [])
            for critique in critiques[:2]:
                lines.append(f"- You raised: \"{critique}\"")

            # How analyst responded
            resolution = entry.get("resolution", {})
            if resolution.get("accepted"):
                lines.append(f"- They accepted: {resolution['accepted'][0]}")
            if resolution.get("rejected"):
                lines.append(f"- They defended against: {resolution['rejected'][0]}")

            lines.append("")

        return "\n".join(lines)

    def format_for_synthesis(self) -> str:
        """Format summary of all analysts' debate histories for synthesis.

        Returns:
            Formatted markdown summarizing all debate arcs
        """
        lines = []
        lines.append("## Debate History Summary (All Analysts)\n")

        for type_id in range(1, 7):
            history = self.load_history(type_id)

            if not history["debate_entries"]:
                continue

            analyst_name = history.get("analyst_name", f"Analyst {type_id}")
            evolution = history["thesis_evolution"]

            # Stance evolution
            stance_arc = " -> ".join(evolution.get("stance_history", [])) or "N/A"
            current_stance = evolution.get("current_stance", "N/A")

            lines.append(f"### {analyst_name}")
            lines.append(f"- **Final Stance:** {current_stance}")
            lines.append(f"- **Evolution:** {stance_arc}")

            # Key pivot if any
            for entry in reversed(history["debate_entries"]):
                resolution = entry.get("resolution", {})
                if resolution.get("key_pivot"):
                    lines.append(f"- **Key Pivot:** {resolution['key_pivot']}")
                    break

            lines.append("")

        return "\n".join(lines)


# Export classes for module use
__all__ = [
    "DebateHistoryManager",
    "DebateHistoryExtractor",
    "AnalystEntry",
    "RDEntry",
    "Resolution",
    "SCHEMA_VERSION",
]
