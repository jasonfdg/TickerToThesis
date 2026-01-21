"""
Source Manager
==============
Manages the source file JSON operations for the pipeline.
"""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

try:
    from .config import get_source_file_path
    from .prompt_loader import PromptLoader
except ImportError:
    from config import get_source_file_path
    from prompt_loader import PromptLoader

logger = logging.getLogger(__name__)

# Source type filters by analyst investing philosophy
# Each analyst type prioritizes different source categories
ANALYST_SOURCE_FILTERS = {
    1: ["sec_filing", "earnings", "company_ir", "sellside"],  # Quality Compounders
    2: ["industry", "alternative", "news", "expert"],  # Imaginative Growth
    3: ["sec_filing", "sellside", "alternative"],  # Fundamental L/S
    4: ["sec_filing", "earnings", "academic"],  # Deep Value
    5: ["news", "sec_filing", "litigation"],  # Event-Driven (8-K focus)
    6: ["industry", "macro", "news"],  # Macro-Tactical
}


class SourceManager:
    """
    Manages the source file (${TICKER}_webSource.json) for a ticker.

    Handles:
    - Loading and saving source files
    - Building prompts for source_summary_agent
    - Providing source content for inclusion in other prompts
    """

    def __init__(self, ticker: str, prompt_loader: Optional[PromptLoader] = None):
        self.ticker = ticker.upper()
        self.source_file_path = get_source_file_path(self.ticker)
        self.prompt_loader = prompt_loader or PromptLoader()
        self._cache: Optional[Dict[str, Any]] = None

    def _get_empty_source_file(self) -> Dict[str, Any]:
        """Create an empty source file structure."""
        return {
            "ticker": self.ticker,
            "last_updated": datetime.now().isoformat(),
            "source_count": 0,
            "config": {"max_analysts": 10},
            "analysts": [],
            "categories": {
                "core": [
                    "sec_filing",
                    "earnings",
                    "company_ir",
                    "sellside",
                    "news",
                    "industry",
                    "alternative",
                    "expert",
                    "academic",
                ],
                "custom": [],
            },
            "research_context": {
                "thesis_points": [],
                "key_debates": [],
                "research_iterations": [],
            },
            "report_summaries": [],
            "sources": [],
        }

    def load_source_file(self) -> Dict[str, Any]:
        """
        Load the source file for this ticker.

        Returns:
            The source file content as a dict, or an empty structure if not found.
        """
        if self._cache is not None:
            return self._cache

        if self.source_file_path.exists():
            try:
                content = self.source_file_path.read_text(encoding="utf-8")
                self._cache = json.loads(content)
                logger.debug(f"Loaded source file: {self.source_file_path}")
            except json.JSONDecodeError as e:
                logger.error(f"Invalid JSON in source file: {e}")
                self._cache = self._get_empty_source_file()
        else:
            logger.debug(f"Source file not found, creating empty: {self.source_file_path}")
            self._cache = self._get_empty_source_file()

        return self._cache

    def save_source_file(self, data: Dict[str, Any]) -> None:
        """
        Save updated source file content.

        Args:
            data: The source file content to save
        """
        # Update timestamp
        data["last_updated"] = datetime.now().isoformat()
        data["source_count"] = len(data.get("sources", []))

        # Ensure directory exists
        self.source_file_path.parent.mkdir(parents=True, exist_ok=True)

        # Write file
        self.source_file_path.write_text(
            json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8"
        )
        self._cache = data
        logger.info(f"Saved source file: {self.source_file_path}")

    def _extract_json_from_response(self, response: str) -> Optional[Dict[str, Any]]:
        """
        Extract JSON from various LLM response formats.

        Handles:
        - Pure JSON
        - Markdown-wrapped JSON (```json ... ```)
        - JSON with text before/after
        - BOM and whitespace issues
        - Truncated JSON (attempts repair)

        Returns:
            Parsed JSON dict or None if extraction fails
        """
        import re

        if not response or not response.strip():
            logger.warning("Empty response from source_summary_agent")
            return None

        # Clean up common issues
        cleaned = response.strip()
        cleaned = cleaned.lstrip('\ufeff')  # Remove BOM if present

        # Strategy 1: Try direct JSON parse
        try:
            return json.loads(cleaned)
        except json.JSONDecodeError:
            pass

        # Strategy 2: Extract from markdown code blocks
        json_blocks = re.findall(r"```(?:json)?\s*([\s\S]*?)\s*```", cleaned)
        for block in json_blocks:
            try:
                parsed = json.loads(block.strip())
                if isinstance(parsed, dict) and "ticker" in parsed:
                    return parsed
            except json.JSONDecodeError:
                continue

        # Strategy 3: Find JSON by locating first { and trying progressively shorter substrings
        # This handles cases where there's extra text after the JSON
        first_brace = cleaned.find('{')
        if first_brace == -1:
            return None

        # Try parsing from first { to progressively earlier } positions
        last_brace = cleaned.rfind('}')
        while last_brace > first_brace:
            potential_json = cleaned[first_brace:last_brace + 1]
            try:
                parsed = json.loads(potential_json)
                if isinstance(parsed, dict) and "ticker" in parsed:
                    return parsed
            except json.JSONDecodeError:
                pass
            # Try finding the previous }
            last_brace = cleaned.rfind('}', first_brace, last_brace)

        # Strategy 4: Attempt to repair truncated JSON
        # If response starts with { and contains "ticker", try to close unclosed braces/brackets
        if cleaned.startswith('{') and '"ticker"' in cleaned:
            repaired = self._attempt_json_repair(cleaned[first_brace:])
            if repaired:
                try:
                    parsed = json.loads(repaired)
                    if isinstance(parsed, dict) and "ticker" in parsed:
                        logger.info("Successfully repaired truncated JSON")
                        return parsed
                except json.JSONDecodeError:
                    pass

        return None

    def _attempt_json_repair(self, json_str: str) -> Optional[str]:
        """
        Attempt to repair truncated or malformed JSON by closing unclosed brackets.

        This is a best-effort repair for common truncation issues.
        """
        # Count unclosed brackets
        open_braces = 0
        open_brackets = 0
        in_string = False
        escape_next = False

        for char in json_str:
            if escape_next:
                escape_next = False
                continue
            if char == '\\' and in_string:
                escape_next = True
                continue
            if char == '"' and not escape_next:
                in_string = not in_string
                continue
            if in_string:
                continue

            if char == '{':
                open_braces += 1
            elif char == '}':
                open_braces -= 1
            elif char == '[':
                open_brackets += 1
            elif char == ']':
                open_brackets -= 1

        # If we're still in a string, close it
        if in_string:
            json_str += '"'

        # Close unclosed brackets and braces
        json_str += ']' * max(0, open_brackets)
        json_str += '}' * max(0, open_braces)

        # Only return if we made meaningful repairs
        if open_braces > 0 or open_brackets > 0 or in_string:
            return json_str
        return None

    def _validate_source_data(self, data: Dict[str, Any]) -> bool:
        """Validate that parsed JSON has required structure."""
        required_fields = ["ticker", "sources"]
        for field in required_fields:
            if field not in data:
                logger.warning(f"Source data missing required field: {field}")
                return False

        if not isinstance(data.get("sources"), list):
            logger.warning("Source data 'sources' field is not a list")
            return False

        return True

    def _merge_sources_incrementally(self, new_sources: List[Dict]) -> None:
        """
        Fallback: merge new sources into existing file incrementally.
        Used when full JSON update fails but we can extract sources list.
        """
        current_data = self.load_source_file()
        existing_urls = {
            self._normalize_url(s.get("url", ""))
            for s in current_data.get("sources", [])
        }

        # Find max source ID
        max_id = 0
        for src in current_data.get("sources", []):
            if src.get("id", "").startswith("src_"):
                try:
                    num = int(src["id"].replace("src_", ""))
                    max_id = max(max_id, num)
                except ValueError:
                    pass

        added_count = 0
        for new_src in new_sources:
            new_url = self._normalize_url(new_src.get("url", ""))
            if new_url and new_url not in existing_urls:
                max_id += 1
                new_src["id"] = f"src_{max_id:03d}"
                new_src["added_at"] = datetime.now().isoformat()
                current_data.setdefault("sources", []).append(new_src)
                existing_urls.add(new_url)
                added_count += 1

        if added_count > 0:
            self.save_source_file(current_data)
            logger.info(f"Incrementally added {added_count} new sources")

    def _normalize_url(self, url: str) -> str:
        """Normalize URL for deduplication."""
        if not url:
            return ""
        url = url.lower().strip()
        url = url.rstrip("/")
        # Remove tracking params
        import re
        url = re.sub(r"[?&](utm_\w+|ref|source)=[^&]*", "", url)
        # Remove www prefix
        url = re.sub(r"^https?://(www\.)?", "https://", url)
        return url

    def update_from_report(self, report_content: str, new_source_data: str) -> bool:
        """
        Update source file with new data from source_summary_agent.

        Args:
            report_content: The analyst/RD report that generated new sources
            new_source_data: JSON string from source_summary_agent

        Returns:
            True if update succeeded, False otherwise
        """
        # Clear cache to ensure we're working with fresh data
        self.clear_cache()

        # Try to extract JSON from the response
        new_data = self._extract_json_from_response(new_source_data)

        if new_data is None:
            logger.error(
                f"Failed to extract JSON from source_summary_agent response. "
                f"Response length: {len(new_source_data)} chars, "
                f"First 200 chars: {new_source_data[:200]!r}"
            )
            return False

        # Validate the extracted data
        if not self._validate_source_data(new_data):
            logger.error("Source data validation failed, attempting incremental merge")

            # Fallback: try to extract just the sources array
            sources = new_data.get("sources", [])
            if sources:
                self._merge_sources_incrementally(sources)
                return True
            return False

        # Full update succeeded
        self.save_source_file(new_data)
        logger.info(
            f"Source file updated: {new_data.get('source_count', len(new_data.get('sources', [])))} sources, "
            f"{len(new_data.get('research_context', {}).get('research_iterations', []))} iterations"
        )
        return True

    def get_source_content(self) -> str:
        """
        Get the source file content as a JSON string for inclusion in prompts.

        Returns:
            JSON string of the source file content
        """
        data = self.load_source_file()
        return json.dumps(data, indent=2, ensure_ascii=False)

    def get_slim_source_content(self) -> str:
        """
        Get minimal source content for prompts (~40-50% smaller).

        Returns only essential fields: id, type, url, title, summary, tags.
        Excludes: thesis_relevance, interpretations, reason, cited_in, amended_at.

        Returns:
            Compact JSON string for analyst prompts
        """
        data = self.load_source_file()
        slim = {
            "ticker": data["ticker"],
            "source_count": data.get("source_count", 0),
            "sources": [
                {
                    "id": s["id"],
                    "type": s.get("type", "unknown"),
                    "url": s.get("url", ""),
                    "title": s.get("title", ""),
                    "summary": s.get("summary", ""),
                    "tags": s.get("tags", []),
                }
                for s in data.get("sources", [])
            ],
        }
        return json.dumps(slim, indent=2, ensure_ascii=False)

    def get_filtered_sources_for_analyst(
        self,
        analyst_type_id: int,
        previously_cited_urls: Optional[List[str]] = None,
    ) -> str:
        """
        Get sources filtered for a specific analyst investing philosophy.

        Args:
            analyst_type_id: Analyst type (1-6)
            previously_cited_urls: URLs analyst has cited before (always include)

        Returns:
            Compact JSON string with relevant sources for this analyst type
        """
        data = self.load_source_file()
        source_types = ANALYST_SOURCE_FILTERS.get(analyst_type_id, [])
        previously_cited = set(previously_cited_urls or [])

        filtered_sources = []
        for s in data.get("sources", []):
            src_type = s.get("type", "unknown")
            src_url = s.get("url", "")

            # Include if type matches OR previously cited by this analyst
            if src_type in source_types or src_url in previously_cited:
                filtered_sources.append({
                    "id": s["id"],
                    "type": src_type,
                    "url": src_url,
                    "title": s.get("title", ""),
                    "summary": s.get("summary", ""),
                    "tags": s.get("tags", []),
                })

        result = {
            "ticker": data["ticker"],
            "source_count": len(filtered_sources),
            "total_available": data.get("source_count", 0),
            "filter": f"analyst_type_{analyst_type_id}",
            "sources": filtered_sources,
        }

        logger.debug(
            f"Filtered sources for analyst {analyst_type_id}: "
            f"{len(filtered_sources)}/{data.get('source_count', 0)}"
        )
        return json.dumps(result, indent=2, ensure_ascii=False)

    def get_source_summary(self) -> str:
        """
        Get a brief summary of the source file for inclusion in prompts.

        Returns:
            Human-readable summary of sources
        """
        data = self.load_source_file()
        sources = data.get("sources", [])

        if not sources:
            return f"No sources collected yet for {self.ticker}."

        # Count by type
        type_counts: Dict[str, int] = {}
        for src in sources:
            src_type = src.get("type", "unknown")
            type_counts[src_type] = type_counts.get(src_type, 0) + 1

        # Build summary
        lines = [
            f"Source file for {self.ticker}: {len(sources)} sources",
            "By type:",
        ]
        for src_type, count in sorted(type_counts.items(), key=lambda x: -x[1]):
            lines.append(f"  - {src_type}: {count}")

        # Add thesis points if present
        thesis_points = data.get("research_context", {}).get("thesis_points", [])
        if thesis_points:
            bull = sum(1 for tp in thesis_points if tp.get("stance") == "bull")
            bear = sum(1 for tp in thesis_points if tp.get("stance") == "bear")
            lines.append(f"Thesis points: {len(thesis_points)} ({bull} bull, {bear} bear)")

        return "\n".join(lines)

    def build_source_update_prompt(
        self,
        new_report: str,
        report_type: str = "analyst_report",
        analyst_id: Optional[str] = None,
    ) -> str:
        """
        Build the prompt for source_summary_agent to update sources.

        Args:
            new_report: The new analyst report or director feedback
            report_type: Type of report ('analyst_report' or 'director_feedback')
            analyst_id: Optional analyst identifier

        Returns:
            Complete prompt for source_summary_agent
        """
        current_source = self.get_source_content()

        prompt = f"""Process the following {report_type} for ticker {self.ticker}.

## Current Source File
```json
{current_source}
```

## New Report to Process
```markdown
{new_report}
```

## Instructions
1. Extract all citations, links, and references from the new report
2. For existing sources (by URL), amend with new context
3. For new sources, add with complete metadata
4. Update research_context if thesis points or key debates identified
5. Log this iteration in research_iterations
6. Output the complete updated JSON

## CRITICAL OUTPUT REQUIREMENTS
- Output ONLY valid JSON - no explanation, no markdown formatting, no text before or after
- Start your response with {{ and end with }}
- The JSON must be parseable by json.loads()
- Include the complete source file structure with all existing + new sources
- Do not wrap in ```json``` code blocks

Example of correct output format:
{{"ticker": "{self.ticker}", "last_updated": "...", "sources": [...], ...}}
"""

        return prompt

    def build_slim_source_update_prompt(
        self,
        extractions: List[Dict[str, Any]],
        iteration: int,
    ) -> str:
        """
        Build a structured prompt for source_summary_agent_v2 using pre-extracted data.

        This version uses pre-extracted citations and thesis claims (JSON),
        making the task tractable for Haiku.

        Args:
            extractions: List of extraction results from CitationExtractor
            iteration: Current pipeline iteration (1-5)

        Returns:
            Structured JSON prompt for source_summary_agent_v2
        """
        current_source = self.load_source_file()

        # Build the structured input for v2 agent
        prompt_data = {
            "ticker": self.ticker,
            "current_sources": current_source,
            "extractions": extractions,
            "iteration": iteration,
        }

        prompt = f"""Process the pre-extracted citations and thesis claims for {self.ticker}.

## Structured Input
```json
{json.dumps(prompt_data, indent=2, ensure_ascii=False)}
```

## Instructions
1. For each source in extractions:
   - If URL exists in current_sources: AMEND (enrich summary, merge tags)
   - If URL is new: ADD with complete metadata (generate next src_XXX)
2. For each thesis_claim in extractions:
   - If similar claim exists with different stance: add to analyst_disagreements
   - If new claim: CREATE thesis_point with author = analyst_type_X
3. Log this iteration in research_iterations
4. Set schema_version: 2

## CRITICAL OUTPUT REQUIREMENTS
- Output ONLY valid JSON
- Start with {{ and end with }}
- Include ALL existing sources + new sources
- Include ALL existing thesis_points + new thesis_points
- Update source_count and last_updated

{{"ticker": "{self.ticker}", "schema_version": 2, "sources": [...], "research_context": {{...}}, ...}}
"""

        return prompt

    def validate_thesis_extraction(self, response_data: Dict[str, Any]) -> bool:
        """
        Validate that thesis extraction was successful.

        Returns True if thesis_points and research_iterations are properly populated.
        Used to determine if Haiku->Sonnet escalation is needed.
        """
        if not response_data:
            return False

        research_context = response_data.get("research_context", {})

        # Check thesis_points exist and have required fields
        thesis_points = research_context.get("thesis_points", [])
        if thesis_points:
            for tp in thesis_points:
                if not all(k in tp for k in ["id", "stance", "claim", "author"]):
                    return False

        # Check research_iterations are logged
        iterations = research_context.get("research_iterations", [])
        if not iterations:
            logger.warning("No research_iterations logged - thesis extraction may have failed")
            return False

        return True

    def clear_cache(self) -> None:
        """Clear the cached source file content."""
        self._cache = None

    def has_sources(self) -> bool:
        """Check if the source file has any sources."""
        data = self.load_source_file()
        return len(data.get("sources", [])) > 0

    def log_research_iteration(
        self,
        report_name: str,
        iteration_type: str,
        focus: str,
        sources_added: int = 0,
        thesis_points_added: Optional[List[str]] = None,
        action_items: Optional[List[str]] = None,
        analyst_id: Optional[str] = None,
    ) -> None:
        """
        Log a research iteration to track pipeline progress.

        Args:
            report_name: Filename of the report (e.g., "analyst_1_v2.md")
            iteration_type: "analyst_report" or "director_feedback" or "source_scout"
            focus: Brief description of iteration focus
            sources_added: Number of sources added this iteration
            thesis_points_added: List of thesis point IDs added
            action_items: List of outstanding action items
            analyst_id: Analyst ID (required for analyst_report type)
        """
        data = self.load_source_file()

        # Ensure research_context exists
        if "research_context" not in data:
            data["research_context"] = {
                "thesis_points": [],
                "key_debates": [],
                "research_iterations": [],
            }

        iteration_entry = {
            "report": report_name,
            "date": datetime.now().strftime("%Y-%m-%d"),
            "type": iteration_type,
            "focus": focus,
            "sources_added": sources_added,
            "thesis_points_added": thesis_points_added or [],
            "action_items": action_items or [],
        }

        # Include analyst ID for analyst reports
        if analyst_id and iteration_type == "analyst_report":
            iteration_entry["analyst"] = analyst_id

        data["research_context"]["research_iterations"].append(iteration_entry)
        self.save_source_file(data)

        logger.info(
            f"Logged research iteration: {report_name} "
            f"({iteration_type}, +{sources_added} sources)"
        )

    def get_thesis_points(self) -> List[Dict[str, Any]]:
        """Get all thesis points from the source file."""
        data = self.load_source_file()
        return data.get("research_context", {}).get("thesis_points", [])

    def get_key_debates(self) -> List[Dict[str, Any]]:
        """Get all key debates from the source file."""
        data = self.load_source_file()
        return data.get("research_context", {}).get("key_debates", [])
