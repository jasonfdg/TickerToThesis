"""
Citation Extractor
==================
Pre-extracts citations and thesis claims from analyst markdown reports.

This preprocessing enables the source_summary_agent to receive structured input
rather than raw markdown, making the task tractable for Haiku.
"""

import re
import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


@dataclass
class ExtractedSource:
    """A source extracted from an analyst report."""
    url: str
    title: str
    source_type: str = "unknown"
    summary: str = ""
    context: str = ""  # Where/how it was cited


@dataclass
class ExtractedThesisClaim:
    """A thesis claim extracted from an analyst report."""
    claim: str
    stance: str = "neutral"  # bull, bear, neutral
    evidence: str = ""
    confidence: str = "medium"  # high, medium, low


@dataclass
class ExtractionResult:
    """Complete extraction result from an analyst report."""
    analyst_type: int
    iteration: int
    sources: List[ExtractedSource] = field(default_factory=list)
    thesis_claims: List[ExtractedThesisClaim] = field(default_factory=list)
    raw_urls: List[str] = field(default_factory=list)
    extraction_notes: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dict for JSON serialization."""
        return {
            "analyst_type": self.analyst_type,
            "iteration": self.iteration,
            "sources": [
                {
                    "url": s.url,
                    "title": s.title,
                    "type": s.source_type,
                    "summary": s.summary,
                    "context": s.context,
                }
                for s in self.sources
            ],
            "thesis_claims": [
                {
                    "claim": t.claim,
                    "stance": t.stance,
                    "evidence": t.evidence,
                    "confidence": t.confidence,
                }
                for t in self.thesis_claims
            ],
            "raw_urls": self.raw_urls,
            "notes": self.extraction_notes,
        }


class CitationExtractor:
    """
    Extracts citations and thesis claims from analyst markdown reports.

    Patterns:
    - Markdown links: [Title](url)
    - Source tables: | # | Source | Type | Date | Summary |
    - Thesis claims: Sentences containing conviction keywords
    """

    # Markdown link pattern: [text](url)
    URL_PATTERN = re.compile(r'\[([^\]]+)\]\(([^)]+)\)')

    # Bare URL pattern (http/https)
    BARE_URL_PATTERN = re.compile(
        r'https?://[^\s<>\[\]"\'`)]+',
        re.IGNORECASE
    )

    # Source table row pattern (markdown table)
    # Matches: | 1 | Source Title | type | 2024-01-15 | Summary text |
    SOURCE_TABLE_PATTERN = re.compile(
        r'\|\s*\d+\s*\|\s*\[?([^\]|]+?)\]?\s*(?:\(([^)]+)\))?\s*\|\s*([^|]+)\s*\|\s*([^|]+)\s*\|\s*([^|]+)\s*\|',
        re.MULTILINE
    )

    # Alternative source table (simpler format)
    SIMPLE_SOURCE_TABLE = re.compile(
        r'\|\s*\[([^\]]+)\]\(([^)]+)\)\s*\|\s*([^|]+)\s*\|',
        re.MULTILINE
    )

    # Thesis claim patterns - sentences with conviction language
    THESIS_PATTERNS = [
        # Explicit thesis statements
        re.compile(r'(?:thesis|conviction|believe|position)[:\s]+([^.]+\.)', re.IGNORECASE),
        # Expectation statements with numbers
        re.compile(r'(?:expect|forecast|project|estimate)[s]?\s+(?:that\s+)?([^.]*\d+[^.]*\.)', re.IGNORECASE),
        # Bull/bear signals
        re.compile(r'(?:bullish|bearish|long|short)\s+(?:on|because)[:\s]+([^.]+\.)', re.IGNORECASE),
        # Quantified claims
        re.compile(r'(?:will|should)\s+(?:reach|achieve|generate|grow)[:\s]+([^.]*\d+[^.]*\.)', re.IGNORECASE),
    ]

    # Stance detection keywords
    BULL_KEYWORDS = ['bullish', 'upside', 'growth', 'opportunity', 'undervalued', 'buy', 'long']
    BEAR_KEYWORDS = ['bearish', 'downside', 'risk', 'overvalued', 'sell', 'short', 'caution']

    # Source type inference from URL/content
    SOURCE_TYPE_PATTERNS = {
        'sec_filing': [r'sec\.gov', r'edgar', r'10-[kq]', r'8-k', r'def14a', r'13[fd]'],
        'earnings': [r'earnings', r'transcript', r'q[1-4]\s*\d{4}', r'conference\s*call'],
        'company_ir': [r'investor', r'shareholder', r'ir\.', r'investor-relations'],
        'sellside': [r'research', r'initiation', r'upgrade', r'downgrade', r'rating'],
        'news': [r'reuters', r'bloomberg', r'wsj', r'cnbc', r'yahoo', r'news'],
        'industry': [r'idc', r'gartner', r'forrester', r'market\s*research'],
        'alternative': [r'glassdoor', r'indeed', r'linkedin', r'github', r'app\s*store'],
        'academic': [r'arxiv', r'ssrn', r'nber', r'paper', r'study'],
    }

    def extract_from_report(
        self,
        content: str,
        analyst_type_id: int,
        iteration: int = 1,
    ) -> ExtractionResult:
        """
        Extract structured citations and thesis claims from analyst markdown.

        Args:
            content: Raw markdown report content
            analyst_type_id: Analyst type (1-6)
            iteration: Pipeline iteration number

        Returns:
            ExtractionResult with sources and thesis claims
        """
        result = ExtractionResult(
            analyst_type=analyst_type_id,
            iteration=iteration,
        )

        # Extract sources from markdown links
        self._extract_markdown_links(content, result)

        # Extract sources from tables
        self._extract_source_tables(content, result)

        # Extract bare URLs
        self._extract_bare_urls(content, result)

        # Extract thesis claims
        self._extract_thesis_claims(content, result)

        # Deduplicate sources by URL
        self._deduplicate_sources(result)

        logger.info(
            f"Extracted from analyst {analyst_type_id} iter {iteration}: "
            f"{len(result.sources)} sources, {len(result.thesis_claims)} thesis claims"
        )

        return result

    def _extract_markdown_links(self, content: str, result: ExtractionResult) -> None:
        """Extract [Title](URL) markdown links."""
        for match in self.URL_PATTERN.finditer(content):
            title = match.group(1).strip()
            url = match.group(2).strip()

            # Skip internal anchors and non-http links
            if not url.startswith('http'):
                continue

            # Find surrounding context (50 chars before and after)
            start = max(0, match.start() - 50)
            end = min(len(content), match.end() + 50)
            context = content[start:end].replace('\n', ' ').strip()

            source = ExtractedSource(
                url=url,
                title=title,
                source_type=self._infer_source_type(url, title),
                context=context,
            )
            result.sources.append(source)

    def _extract_source_tables(self, content: str, result: ExtractionResult) -> None:
        """Extract sources from markdown tables."""
        # Try full table pattern
        for match in self.SOURCE_TABLE_PATTERN.finditer(content):
            title = match.group(1).strip()
            url = match.group(2) or ""
            src_type = match.group(3).strip().lower() if match.group(3) else "unknown"
            date = match.group(4).strip() if match.group(4) else ""
            summary = match.group(5).strip() if match.group(5) else ""

            if url:
                source = ExtractedSource(
                    url=url.strip(),
                    title=title,
                    source_type=src_type if src_type else self._infer_source_type(url, title),
                    summary=summary,
                    context=f"Table entry, date: {date}",
                )
                result.sources.append(source)

        # Try simple table pattern
        for match in self.SIMPLE_SOURCE_TABLE.finditer(content):
            title = match.group(1).strip()
            url = match.group(2).strip()
            extra = match.group(3).strip() if match.group(3) else ""

            source = ExtractedSource(
                url=url,
                title=title,
                source_type=self._infer_source_type(url, title),
                context=f"Table: {extra}",
            )
            result.sources.append(source)

    def _extract_bare_urls(self, content: str, result: ExtractionResult) -> None:
        """Extract bare URLs not in markdown syntax."""
        existing_urls = {s.url.lower() for s in result.sources}

        for match in self.BARE_URL_PATTERN.finditer(content):
            url = match.group(0).rstrip('.,;:!?')

            # Skip if already captured via markdown link
            if url.lower() in existing_urls:
                continue

            result.raw_urls.append(url)

            # Only add as source if it looks like a real reference
            if self._is_likely_source(url):
                source = ExtractedSource(
                    url=url,
                    title=self._extract_title_from_url(url),
                    source_type=self._infer_source_type(url, ""),
                )
                result.sources.append(source)
                existing_urls.add(url.lower())

    def _extract_thesis_claims(self, content: str, result: ExtractionResult) -> None:
        """Extract thesis claims using conviction language patterns."""
        seen_claims = set()

        for pattern in self.THESIS_PATTERNS:
            for match in pattern.finditer(content):
                claim_text = match.group(1).strip()

                # Skip short claims (40 char minimum reduces false positives)
                # or duplicate claims
                if len(claim_text) < 40 or claim_text.lower() in seen_claims:
                    continue

                seen_claims.add(claim_text.lower())

                # Determine stance
                stance = self._determine_stance(claim_text)

                # Find evidence (next sentence or context)
                claim_end = match.end()
                evidence_end = min(len(content), claim_end + 200)
                potential_evidence = content[claim_end:evidence_end]
                evidence = self._extract_evidence(potential_evidence)

                claim = ExtractedThesisClaim(
                    claim=claim_text,
                    stance=stance,
                    evidence=evidence,
                    confidence=self._estimate_confidence(claim_text),
                )
                result.thesis_claims.append(claim)

    def _infer_source_type(self, url: str, title: str) -> str:
        """Infer source type from URL and title."""
        combined = f"{url} {title}".lower()

        for src_type, patterns in self.SOURCE_TYPE_PATTERNS.items():
            for pattern in patterns:
                if re.search(pattern, combined, re.IGNORECASE):
                    return src_type

        return "unknown"

    def _determine_stance(self, text: str) -> str:
        """Determine bull/bear/neutral stance from text."""
        text_lower = text.lower()

        bull_score = sum(1 for kw in self.BULL_KEYWORDS if kw in text_lower)
        bear_score = sum(1 for kw in self.BEAR_KEYWORDS if kw in text_lower)

        if bull_score > bear_score:
            return "bull"
        elif bear_score > bull_score:
            return "bear"
        return "neutral"

    def _estimate_confidence(self, claim: str) -> str:
        """Estimate confidence level from claim language."""
        claim_lower = claim.lower()

        # High confidence indicators
        if any(kw in claim_lower for kw in ['will', 'certain', 'confident', 'clear']):
            return "high"

        # Low confidence indicators
        if any(kw in claim_lower for kw in ['may', 'might', 'could', 'uncertain', 'possible']):
            return "low"

        return "medium"

    def _extract_evidence(self, text: str) -> str:
        """Extract supporting evidence from text following a claim."""
        # Look for the next sentence that contains data
        sentences = text.split('.')
        for sentence in sentences[:2]:  # Check first two sentences
            sentence = sentence.strip()
            # Has numbers = likely evidence
            if re.search(r'\d+', sentence) and len(sentence) > 20:
                return sentence + "."
        return ""

    def _is_likely_source(self, url: str) -> bool:
        """Determine if URL is likely a research source vs internal link."""
        # Skip common non-source patterns
        skip_patterns = [
            r'localhost', r'127\.0\.0\.1', r'example\.com',
            r'\.png$', r'\.jpg$', r'\.gif$', r'\.svg$',
        ]
        for pattern in skip_patterns:
            if re.search(pattern, url, re.IGNORECASE):
                return False
        return True

    def _extract_title_from_url(self, url: str) -> str:
        """Extract a reasonable title from URL path."""
        from urllib.parse import urlparse, unquote

        try:
            parsed = urlparse(url)
            path = unquote(parsed.path)

            # Get last meaningful path segment
            segments = [s for s in path.split('/') if s]
            if segments:
                title = segments[-1]
                # Clean up common patterns
                title = re.sub(r'[-_]', ' ', title)
                title = re.sub(r'\.[a-z]+$', '', title)  # Remove extension
                return title.title()

            return parsed.netloc
        except Exception:
            return "Untitled Source"

    def _deduplicate_sources(self, result: ExtractionResult) -> None:
        """Remove duplicate sources by normalized URL."""
        seen_urls = set()
        unique_sources = []

        for source in result.sources:
            normalized = self._normalize_url(source.url)
            if normalized not in seen_urls:
                seen_urls.add(normalized)
                unique_sources.append(source)

        result.sources = unique_sources

    def _normalize_url(self, url: str) -> str:
        """Normalize URL for deduplication."""
        if not url:
            return ""
        url = url.lower().strip().rstrip('/')
        url = re.sub(r'[?&](utm_\w+|ref|source)=[^&]*', '', url)
        url = re.sub(r'^https?://(www\.)?', '', url)
        return url


def extract_citations_from_reports(
    reports: Dict[int, str],
    iteration: int,
) -> List[ExtractionResult]:
    """
    Convenience function to extract citations from multiple analyst reports.

    Args:
        reports: Dict of analyst_type_id -> report content
        iteration: Pipeline iteration number

    Returns:
        List of ExtractionResult objects
    """
    extractor = CitationExtractor()
    results = []

    for analyst_type, content in reports.items():
        if content:
            result = extractor.extract_from_report(content, analyst_type, iteration)
            results.append(result)

    return results
