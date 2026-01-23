"""
Source Manager
==============
Manages the source file JSON operations for the pipeline.
"""

import json
import logging
import shutil
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

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
        """Create an empty source file structure (v4 schema - simplified)."""
        return {
            "ticker": self.ticker,
            "schema_version": 4,
            "last_updated": datetime.now().isoformat(),
            "source_count": 0,
            "iterations": [],
            "sources": [],
        }

    def _validate_before_save(self, data: Dict[str, Any]) -> bool:
        """
        Validate source file structure before saving.

        Checks:
        - Required top-level fields exist (ticker, sources)
        - 'sources' is a list
        - Each source has minimum required fields (id, url)

        Returns:
            True if valid, False otherwise
        """
        required_top = ["ticker", "sources"]
        for field in required_top:
            if field not in data:
                logger.error(f"Validation failed: missing required field '{field}'")
                return False

        if not isinstance(data.get("sources"), list):
            logger.error("Validation failed: 'sources' must be a list")
            return False

        # Validate each source has minimum fields
        for i, src in enumerate(data.get("sources", [])):
            if not src.get("id"):
                logger.warning(f"Source at index {i} missing 'id' field")
            if not src.get("url"):
                logger.warning(f"Source at index {i} missing 'url' field")

        return True

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
        Save updated source file content with validation and atomic write.

        Uses atomic write pattern (temp file -> rename) to prevent corruption.
        Creates backup of previous version before overwriting.

        Args:
            data: The source file content to save

        Raises:
            ValueError: If data validation fails
        """
        # Validate before saving
        if not self._validate_before_save(data):
            raise ValueError("Source data validation failed, refusing to save corrupted data")

        # Update metadata
        data["last_updated"] = datetime.now().isoformat()
        data["source_count"] = len(data.get("sources", []))

        # Ensure directory exists
        self.source_file_path.parent.mkdir(parents=True, exist_ok=True)

        # Define paths for atomic write
        temp_path = self.source_file_path.with_suffix('.tmp')
        backup_path = self.source_file_path.with_suffix('.backup')

        # Serialize JSON
        json_content = json.dumps(data, indent=2, ensure_ascii=False)

        # Write to temp file first
        temp_path.write_text(json_content, encoding="utf-8")

        # Backup existing file if it exists
        if self.source_file_path.exists():
            try:
                shutil.copy2(self.source_file_path, backup_path)
                logger.debug(f"Created backup: {backup_path}")
            except Exception as e:
                logger.warning(f"Failed to create backup: {e}")

        # Atomic rename: temp -> target
        temp_path.rename(self.source_file_path)

        self._cache = data
        logger.info(
            f"Saved source file: {self.source_file_path} "
            f"({data['source_count']} sources, {len(json_content)} bytes)"
        )

    def _extract_json_from_response(self, response: str) -> Optional[Dict[str, Any]]:
        """
        Extract JSON from various LLM response formats.

        Handles:
        - Pure JSON
        - Markdown-wrapped JSON (```json ... ```)
        - JSON with text before/after
        - BOM and whitespace issues
        - Truncated JSON (attempts repair)
        - Trailing commas (common LLM mistake)

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
        except json.JSONDecodeError as e:
            logger.warning(f"Direct JSON parse failed at position {e.pos}: {e.msg}. Context: ...{cleaned[max(0,e.pos-50):e.pos+50]}...")

        # Strategy 1b: Fix trailing commas (common LLM mistake) and try again
        fixed = self._fix_trailing_commas(cleaned)
        if fixed != cleaned:
            try:
                return json.loads(fixed)
            except json.JSONDecodeError:
                pass

        # Strategy 2: Strip markdown code fences if present (handles incomplete fences)
        # This handles cases like: ```json\n{...}\n``` or ```json\n{...} (no closing fence)
        if cleaned.startswith('```'):
            # Remove opening fence (```json or ```)
            lines = cleaned.split('\n', 1)
            if len(lines) > 1:
                cleaned = lines[1]  # Skip the first line with ```json
            # Remove closing fence if present
            if cleaned.rstrip().endswith('```'):
                cleaned = cleaned.rstrip()[:-3].rstrip()
            # Try parsing after stripping fences
            try:
                parsed = json.loads(cleaned)
                if isinstance(parsed, dict) and "ticker" in parsed:
                    return parsed
            except json.JSONDecodeError:
                pass

        # Strategy 3: Extract from markdown code blocks (greedy match)
        json_blocks = re.findall(r"```(?:json)?\s*([\s\S]*?)\s*```", cleaned)
        for block in json_blocks:
            try:
                parsed = json.loads(block.strip())
                if isinstance(parsed, dict) and "ticker" in parsed:
                    return parsed
            except json.JSONDecodeError:
                continue

        # Strategy 4: Find JSON by locating first { and trying progressively shorter substrings
        # This handles cases where there's extra text after the JSON
        first_brace = cleaned.find('{')
        if first_brace == -1:
            return None

        # Try parsing from first { to progressively earlier } positions
        last_brace = cleaned.rfind('}')
        while last_brace > first_brace:
            potential_json = cleaned[first_brace:last_brace + 1]
            # Try with and without trailing comma fix
            for candidate in [potential_json, self._fix_trailing_commas(potential_json)]:
                try:
                    parsed = json.loads(candidate)
                    if isinstance(parsed, dict) and "ticker" in parsed:
                        return parsed
                except json.JSONDecodeError:
                    pass
            # Try finding the previous }
            last_brace = cleaned.rfind('}', first_brace, last_brace)

        # Strategy 5: Attempt to repair truncated JSON
        # If response starts with { and contains "ticker", try to close unclosed braces/brackets
        if first_brace >= 0 and '"ticker"' in cleaned:
            repaired = self._attempt_json_repair(cleaned[first_brace:])
            if repaired:
                # Try with and without trailing comma fix
                for candidate in [repaired, self._fix_trailing_commas(repaired)]:
                    try:
                        parsed = json.loads(candidate)
                        if isinstance(parsed, dict) and "ticker" in parsed:
                            logger.info("Successfully repaired truncated JSON")
                            return parsed
                    except json.JSONDecodeError:
                        pass

        return None

    def _fix_trailing_commas(self, json_str: str) -> str:
        """Remove trailing commas before ] or } (common LLM mistake)."""
        import re
        # Remove trailing commas before closing brackets/braces
        # Handle: [1, 2, 3,] -> [1, 2, 3]
        # Handle: {"a": 1,} -> {"a": 1}
        fixed = re.sub(r',(\s*[}\]])', r'\1', json_str)
        return fixed

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
        last_structure = []  # Track what we're inside: 'object', 'array', 'key', 'value'

        for i, char in enumerate(json_str):
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
                last_structure.append('object')
            elif char == '}':
                open_braces -= 1
                if last_structure and last_structure[-1] in ('object', 'value'):
                    last_structure.pop()
            elif char == '[':
                open_brackets += 1
                last_structure.append('array')
            elif char == ']':
                open_brackets -= 1
                if last_structure and last_structure[-1] == 'array':
                    last_structure.pop()
            elif char == ':' and last_structure and last_structure[-1] == 'object':
                last_structure.append('value')
            elif char == ',' and last_structure:
                if last_structure[-1] == 'value':
                    last_structure.pop()

        # If we're still in a string, close it and handle context
        if in_string:
            json_str += '"'
            # After closing string, we might be in a value context - add null if needed
            # Check if we just closed a value string (common case)
            stripped = json_str.rstrip()
            if stripped.endswith('",'):
                # We're good, value is complete
                pass
            elif stripped.endswith('"'):
                # Check what came before to see if we need anything
                # This handles: "key": "truncated value" -> needs , or } next
                pass

        # Remove any trailing comma before we close brackets (invalid JSON)
        json_str = json_str.rstrip()
        while json_str.endswith(','):
            json_str = json_str[:-1].rstrip()

        # Close unclosed brackets and braces in correct order
        for _ in range(max(0, open_brackets)):
            json_str += ']'
        for _ in range(max(0, open_braces)):
            json_str += '}'

        # Return the string (repaired or original) - let caller try parsing
        return json_str

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

    def update_from_report(
        self,
        report_content: str,
        new_source_data: str,
        mark_verified: bool = False,
    ) -> bool:
        """
        Update source file with new data from source_summary_agent.

        Args:
            report_content: The analyst/RD report that generated new sources
            new_source_data: JSON string from source_summary_agent
            mark_verified: If True, mark all sources as verified (for web search sources)

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

        # Mark sources as verified if requested (for web search results)
        if mark_verified:
            for source in new_data.get("sources", []):
                if "verified" not in source:
                    source["verified"] = True

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

            # ALWAYS include stock_data with full structured_data (financial baseline)
            if src_type == "stock_data":
                filtered_sources.append(s)  # Full source, not slim
            # Include if type matches OR previously cited by this analyst
            elif src_type in source_types or src_url in previously_cited:
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

        return "\n".join(lines)

    def clear_cache(self) -> None:
        """Clear the cached source file content."""
        self._cache = None

    def has_sources(self) -> bool:
        """Check if the source file has any sources."""
        data = self.load_source_file()
        return len(data.get("sources", [])) > 0

    def initialize_with_bootstrap(
        self,
        stock_data: Optional[Dict[str, Any]] = None,
        bootstrap_sources: Optional[List[Dict[str, Any]]] = None,
    ) -> int:
        """
        Initialize source file with stock data + bootstrap sources in single write.

        Combines the initial yfinance stock data fetch and bootstrap web research
        into a single atomic write, reducing writes from 2 to 1.

        Args:
            stock_data: Stock data entry from StockData.to_source_json()
            bootstrap_sources: List of source entries extracted from bootstrap

        Returns:
            Number of sources added
        """
        try:
            self.clear_cache()
            data = self.load_source_file()

            sources_added = 0

            # Track existing URLs for deduplication
            existing_urls = {
                self._normalize_url(s.get("url", ""))
                for s in data.get("sources", [])
            }

            # Find max source ID
            max_id = 0
            for src in data.get("sources", []):
                if src.get("id", "").startswith("src_"):
                    try:
                        num = int(src["id"].replace("src_", ""))
                        max_id = max(max_id, num)
                    except ValueError:
                        pass

            # Add stock data as first source (verified ground truth)
            if stock_data:
                stock_url = stock_data.get("url", "")
                normalized_stock_url = self._normalize_url(stock_url)

                if normalized_stock_url not in existing_urls:
                    max_id += 1
                    stock_data["id"] = f"src_{max_id:03d}"
                    stock_data["added_at"] = datetime.now().isoformat()
                    stock_data["verified"] = True  # yfinance API = verified source
                    data.setdefault("sources", []).insert(0, stock_data)
                    existing_urls.add(normalized_stock_url)
                    sources_added += 1
                    logger.debug(f"Added stock data source: {stock_data.get('title', 'Unknown')}")

            # Add bootstrap sources
            if bootstrap_sources:
                for source in bootstrap_sources:
                    url = source.get("url", "")
                    if not url:
                        continue

                    normalized_url = self._normalize_url(url)
                    if normalized_url in existing_urls:
                        continue

                    max_id += 1
                    source["id"] = f"src_{max_id:03d}"
                    source["added_at"] = datetime.now().isoformat()
                    source["verified"] = True  # Perplexity search = verified source
                    data.setdefault("sources", []).append(source)
                    existing_urls.add(normalized_url)
                    sources_added += 1

            # Log the initialization (v4 schema uses top-level iterations)
            if "iterations" not in data:
                data["iterations"] = []
            data["iterations"].append({
                "iteration": 0,
                "date": datetime.now().strftime("%Y-%m-%d"),
                "sources_added": sources_added,
                "type": "bootstrap",
            })

            # Single atomic save
            self.save_source_file(data)

            logger.info(
                f"Initialized source file: {sources_added} sources "
                f"(stock_data: {stock_data is not None}, "
                f"bootstrap: {len(bootstrap_sources) if bootstrap_sources else 0})"
            )

            return sources_added

        except Exception as e:
            logger.error(f"Failed to initialize source file: {e}", exc_info=True)
            return 0

    def update_sources_from_scout_direct(
        self,
        scout_report_content: str,
        iteration: int,
    ) -> int:
        """
        Update webSource.json with sources from Source Scout (no LLM).

        Extracts sources directly from JSON block in Source Scout output,
        or falls back to CitationExtractor for markdown links.

        Args:
            scout_report_content: The Source Scout report content (markdown with URLs)
            iteration: Current pipeline iteration (1-5)

        Returns:
            Number of sources added (0 on error)
        """
        import re

        try:
            from citation_extractor import CitationExtractor
        except ImportError:
            from .citation_extractor import CitationExtractor

        try:
            self.clear_cache()
            data = self.load_source_file()

            # Track existing URLs for deduplication
            existing_urls = {
                self._normalize_url(s.get("url", ""))
                for s in data.get("sources", [])
            }

            # Find max source ID
            max_id = 0
            for src in data.get("sources", []):
                if src.get("id", "").startswith("src_"):
                    try:
                        num = int(src["id"].replace("src_", ""))
                        max_id = max(max_id, num)
                    except ValueError:
                        pass

            sources_added = 0
            extracted_sources: List[Dict[str, Any]] = []

            # Strategy 1: Try to extract JSON from ## Source Additions block
            json_match = re.search(
                r'##\s*Source\s+Additions?\s*\n```(?:json)?\s*([\s\S]*?)```',
                scout_report_content,
                re.IGNORECASE
            )
            if json_match:
                try:
                    json_content = json_match.group(1).strip()
                    parsed = json.loads(json_content)
                    if isinstance(parsed, list):
                        extracted_sources = parsed
                    elif isinstance(parsed, dict) and "sources" in parsed:
                        extracted_sources = parsed["sources"]
                    logger.info(f"Extracted {len(extracted_sources)} sources from JSON block")
                except json.JSONDecodeError as e:
                    logger.warning(f"JSON parse failed in Source Additions: {e}")

            # Strategy 2: Fall back to CitationExtractor for markdown links
            if not extracted_sources:
                extractor = CitationExtractor()
                extraction = extractor.extract_from_report(
                    scout_report_content,
                    analyst_type_id=0,  # Source scout is not analyst-specific
                    iteration=iteration,
                )
                extracted_sources = [
                    {
                        "url": src.url,
                        "title": src.title,
                        "type": src.source_type,
                        "summary": src.summary or src.context,
                    }
                    for src in extraction.sources
                ]
                logger.info(f"Extracted {len(extracted_sources)} sources via CitationExtractor")

            # Add sources to data
            for source in extracted_sources:
                url = source.get("url", "")
                if not url:
                    continue

                normalized_url = self._normalize_url(url)
                if normalized_url in existing_urls:
                    continue

                max_id += 1
                source_entry = {
                    "id": f"src_{max_id:03d}",
                    "url": url,
                    "title": source.get("title", "Untitled"),
                    "type": source.get("type", "web"),
                    "summary": source.get("summary", ""),
                    "tags": source.get("tags", []),
                    "added_at": datetime.now().isoformat(),
                    "cited_by": ["source_scout"],
                    "iteration": iteration,
                    "verified": True,  # Web search = verified
                }
                data.setdefault("sources", []).append(source_entry)
                existing_urls.add(normalized_url)
                sources_added += 1

            # Log the iteration
            if "iterations" not in data:
                data["iterations"] = []
            data["iterations"].append({
                "iteration": iteration,
                "date": datetime.now().strftime("%Y-%m-%d"),
                "sources_added": sources_added,
                "type": "source_scout",
            })

            self.save_source_file(data)
            logger.info(f"Source Scout update: +{sources_added} sources (iteration {iteration})")
            return sources_added

        except Exception as e:
            logger.error(f"Source Scout direct update failed: {e}", exc_info=True)
            return 0

    def update_citations_only(
        self,
        extractions: List[Dict[str, Any]],
        iteration: int,
    ) -> int:
        """
        Update webSource.json with extracted citations only (sources, no thesis_points).

        This is a lightweight update that skips the source_summary_agent call.
        Used when running citation extraction in parallel with RD reviews.
        Does NOT generate analyst_summaries or extract thesis_points.
        Thesis points are deferred to synthesis phase.

        Args:
            extractions: List of extraction dicts from CitationExtractor.to_dict()
            iteration: Current pipeline iteration (1-5)

        Returns:
            Number of sources added (0 on error)
        """
        try:
            self.clear_cache()
            data = self.load_source_file()

            # Diagnostic: log initial state
            initial_source_count = len(data.get("sources", []))

            # Track existing URLs for deduplication
            existing_urls = {
                self._normalize_url(s.get("url", ""))
                for s in data.get("sources", [])
            }

            # Find max source ID
            max_id = 0
            for src in data.get("sources", []):
                if src.get("id", "").startswith("src_"):
                    try:
                        num = int(src["id"].replace("src_", ""))
                        max_id = max(max_id, num)
                    except ValueError:
                        pass

            sources_added = 0
            sources_attempted = 0
            duplicates_skipped = 0

            # Process each analyst's extractions (sources only, thesis deferred to synthesis)
            for extraction in extractions:
                analyst_type = extraction.get("analyst_type", 0)

                # Add sources
                for source in extraction.get("sources", []):
                    url = source.get("url", "")
                    sources_attempted += 1

                    if not url:
                        continue

                    normalized_url = self._normalize_url(url)
                    if normalized_url in existing_urls:
                        duplicates_skipped += 1
                        continue

                    # Add new source
                    max_id += 1
                    source_entry = {
                        "id": f"src_{max_id:03d}",
                        "url": url,
                        "title": source.get("title", "Untitled"),
                        "type": source.get("type", "unknown"),
                        "summary": source.get("summary", ""),
                        "tags": [],
                        "added_at": datetime.now().isoformat(),
                        "cited_by": [f"analyst_{analyst_type}"],
                        "iteration": iteration,
                        "verified": False,  # Analyst citations = unverified (regex-extracted, not fetched)
                    }
                    data.setdefault("sources", []).append(source_entry)
                    existing_urls.add(normalized_url)
                    sources_added += 1

            # Log the iteration (v4 schema uses top-level iterations)
            if "iterations" not in data:
                data["iterations"] = []
            data["iterations"].append({
                "iteration": iteration,
                "date": datetime.now().strftime("%Y-%m-%d"),
                "sources_added": sources_added,
                "type": "citation",
            })

            # Save with validation
            self.save_source_file(data)

            # Diagnostic logging
            logger.info(
                f"Citation update iter {iteration}: "
                f"{len(extractions)} analysts processed, "
                f"{sources_attempted} sources attempted, {sources_added} added, "
                f"{duplicates_skipped} duplicates skipped. "
                f"File: {initial_source_count} -> {len(data.get('sources', []))} sources"
            )

            return sources_added

        except ValueError as e:
            # Validation error from save_source_file - don't corrupt file
            logger.error(
                f"Citation extraction failed for iteration {iteration}: "
                f"Validation error: {e}"
            )
            return 0

        except Exception as e:
            logger.error(
                f"Citation extraction failed for iteration {iteration}: {e}",
                exc_info=True
            )
            return 0
