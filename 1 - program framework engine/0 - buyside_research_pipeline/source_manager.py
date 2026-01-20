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

    def update_from_report(self, report_content: str, new_source_data: str) -> None:
        """
        Update source file with new data from source_summary_agent.

        Args:
            report_content: The analyst/RD report that generated new sources
            new_source_data: JSON string from source_summary_agent
        """
        try:
            new_data = json.loads(new_source_data)
            self.save_source_file(new_data)
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse source update: {e}")
            # Try to extract JSON from the response if it's wrapped in markdown
            import re

            json_match = re.search(r"```json\s*(.*?)\s*```", new_source_data, re.DOTALL)
            if json_match:
                try:
                    new_data = json.loads(json_match.group(1))
                    self.save_source_file(new_data)
                except json.JSONDecodeError:
                    logger.error("Failed to extract valid JSON from markdown block")

    def get_source_content(self) -> str:
        """
        Get the source file content as a JSON string for inclusion in prompts.

        Returns:
            JSON string of the source file content
        """
        data = self.load_source_file()
        return json.dumps(data, indent=2, ensure_ascii=False)

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

Remember:
- Never delete existing sources
- Deduplicate by normalized URL
- Preserve the audit trail in the reason field
- Output ONLY the complete JSON, no other text
"""

        return prompt

    def clear_cache(self) -> None:
        """Clear the cached source file content."""
        self._cache = None

    def has_sources(self) -> bool:
        """Check if the source file has any sources."""
        data = self.load_source_file()
        return len(data.get("sources", [])) > 0

    def get_thesis_points(self) -> List[Dict[str, Any]]:
        """Get all thesis points from the source file."""
        data = self.load_source_file()
        return data.get("research_context", {}).get("thesis_points", [])

    def get_key_debates(self) -> List[Dict[str, Any]]:
        """Get all key debates from the source file."""
        data = self.load_source_file()
        return data.get("research_context", {}).get("key_debates", [])
