"""
Materials Manager
=================
Handles ingestion of external PDF documents (10-Ks, sell-side research,
earnings transcripts, presentations) dropped into the materials/ folder.

Extracts text, classifies document type, caches as .md, and produces
a formatted prompt block for injection into analyst/RD prompts.
"""

import logging
import os
import re
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


class DocumentType(Enum):
    """Classification of external research documents."""
    SEC_FILING = "SEC Filing"
    MERGER_PROXY = "Merger/Proxy"
    SELLSIDE = "Sell-Side Research"
    TRANSCRIPT = "Earnings Transcript"
    EXPERT_NETWORK = "Expert Network"
    PRESENTATION = "Investor Presentation"
    OTHER = "Other"


# Priority for truncation: lowest priority gets cut first
_DOC_PRIORITY = {
    DocumentType.OTHER: 0,
    DocumentType.PRESENTATION: 1,
    DocumentType.EXPERT_NETWORK: 2,
    DocumentType.TRANSCRIPT: 3,
    DocumentType.SELLSIDE: 4,
    DocumentType.MERGER_PROXY: 5,
    DocumentType.SEC_FILING: 6,
}

# Filename prefix conventions for classification
_PREFIX_MAP = {
    "10k_": DocumentType.SEC_FILING,
    "10-k_": DocumentType.SEC_FILING,
    "sec_": DocumentType.SEC_FILING,
    "proxy_": DocumentType.MERGER_PROXY,
    "merger_": DocumentType.MERGER_PROXY,
    "defm14a_": DocumentType.MERGER_PROXY,
    "def14a_": DocumentType.MERGER_PROXY,
    "sellside_": DocumentType.SELLSIDE,
    "sell_side_": DocumentType.SELLSIDE,
    "broker_": DocumentType.SELLSIDE,
    "transcript_": DocumentType.TRANSCRIPT,
    "earnings_": DocumentType.TRANSCRIPT,
    "call_": DocumentType.TRANSCRIPT,
    "expert_": DocumentType.EXPERT_NETWORK,
    "alphasense_": DocumentType.EXPERT_NETWORK,
    "tegus_": DocumentType.EXPERT_NETWORK,
    "glg_": DocumentType.EXPERT_NETWORK,
    "presentation_": DocumentType.PRESENTATION,
    "investor_": DocumentType.PRESENTATION,
    "deck_": DocumentType.PRESENTATION,
}

# SEC filing section patterns (Item headings)
_SEC_ITEMS_WANTED = {
    "1": "Business",
    "1a": "Risk Factors",
    "7": "Management's Discussion and Analysis",
    "7a": "Quantitative and Qualitative Disclosures About Market Risk",
}

# Regex for matching Item headings in SEC filings
_ITEM_PATTERN = re.compile(
    r"(?:^|\n)\s*(?:ITEM|Item)\s+(\d+[aAbB]?)[\.\:\s]",
    re.MULTILINE,
)

# Proxy section headings for smart extraction
_PROXY_SECTION_PATTERN = re.compile(
    r"(?:^|\n)\s*((?:Background|Reasons|Opinion|Fairness|Financial (?:Projections|Forecasts)"
    r"|(?:The )?Merger Agreement|Termination|Interests of)"
    r"[^\n]{0,80})\s*\n",
    re.MULTILINE | re.IGNORECASE,
)

# Target proxy sections (for filtering detected headings)
_PROXY_SECTIONS_WANTED = [
    "background",
    "reasons",
    "opinion",
    "fairness",
    "financial projections",
    "financial forecasts",
    "merger agreement",
    "termination",
    "interests of",
]

# Sell-side bias disclaimer
_SELLSIDE_DISCLAIMER = """
> **BIAS NOTICE (Tier 3 — Opinion):** This is sell-side research. The issuing
> firm may have banking relationships, underwriting positions, or trading
> interests that bias their analysis. Extract factual claims and verify
> independently. Do NOT adopt price targets or recommendations uncritically.
"""

# Merger/proxy source disclaimer
_MERGER_PROXY_DISCLAIMER = """
> **SOURCE NOTE (Facts — Legal Filing):** Merger proxy / DEF 14A. Contains
> binding terms, board recommendations, fairness opinions, and financial
> projections. Treat as authoritative on deal structure and valuation.
"""

# Expert network source disclaimer
_EXPERT_NETWORK_DISCLAIMER = """
> **SOURCE NOTE (Primary — Expert Voice):** Expert network transcript.
> High-value primary source with direct industry insight. Cross-reference
> claims against public filings.
"""


class MaterialsManager:
    """Manages external PDF document ingestion for the pipeline.

    Usage:
        mm = MaterialsManager(output_dir)
        if mm.has_materials:
            mm.process_materials()
            block = mm.get_materials_block()
    """

    def __init__(self, output_dir: Path, materials_dir: Path = None):
        self.output_dir = Path(output_dir)
        self.materials_dir = Path(materials_dir) if materials_dir else self.output_dir / "materials"
        self._documents: List[Dict] = []  # [{path, type, md_path, content}]

    @property
    def has_materials(self) -> bool:
        """Check if materials/ exists and contains at least one PDF or HTM."""
        if not self.materials_dir.exists():
            return False
        return any(self.materials_dir.glob("*.pdf")) or any(self.materials_dir.glob("*.htm"))

    def process_materials(self) -> int:
        """Discover, classify, extract, and cache all PDFs and HTMs in materials/.

        Idempotent: uses cached .md if it's newer than the source file.

        Returns:
            Number of documents processed.
        """
        if not self.has_materials:
            return 0

        pdfs = sorted(self.materials_dir.glob("*.pdf"))
        htms = sorted(self.materials_dir.glob("*.htm"))
        all_files = pdfs + htms
        logger.info(f"Found {len(pdfs)} PDF(s) and {len(htms)} HTM(s) in materials/")

        self._documents = []
        for pdf_path in all_files:
            md_path = pdf_path.with_suffix(".md")

            # Check cache validity
            if md_path.exists() and md_path.stat().st_mtime > pdf_path.stat().st_mtime:
                logger.info(f"  Using cached: {md_path.name}")
                content = md_path.read_text(encoding="utf-8")
                doc_type = self._classify_document(pdf_path, content)
            else:
                doc_type = self._classify_document(pdf_path)
                content = self._extract(pdf_path, doc_type)

                if not content.strip():
                    logger.warning(f"  Empty extraction: {pdf_path.name}")
                    continue

                # Cache as .md
                md_path.write_text(content, encoding="utf-8")
                logger.info(f"  Extracted {doc_type.value}: {pdf_path.name} -> {md_path.name} ({len(content):,} chars)")

            self._documents.append({
                "path": pdf_path,
                "type": doc_type,
                "md_path": md_path,
                "content": content,
            })

        logger.info(f"Processed {len(self._documents)} external document(s)")
        return len(self._documents)

    def get_materials_block(
        self,
        analyst_type_id: Optional[int] = None,
        max_chars: int = 80_000,
    ) -> str:
        """Build formatted prompt section with all extracted materials.

        Args:
            analyst_type_id: Optional analyst type (unused for now, reserved for filtering).
            max_chars: Maximum total characters for the materials block (~20K tokens).

        Returns:
            Formatted markdown block ready for prompt injection, or empty string.
        """
        if not self._documents:
            return ""

        # Sort by priority (lowest priority first, so they get truncated first)
        sorted_docs = sorted(
            self._documents,
            key=lambda d: _DOC_PRIORITY.get(d["type"], 0),
        )

        # Build sections, truncating from lowest priority if over budget
        sections: List[Tuple[DocumentType, str, str]] = []
        total_chars = 0

        for doc in reversed(sorted_docs):  # Highest priority first
            doc_type = doc["type"]
            filename = doc["path"].stem
            content = doc["content"]

            # Add disclaimers by type
            if doc_type == DocumentType.SELLSIDE:
                content = _SELLSIDE_DISCLAIMER + "\n" + content
            elif doc_type == DocumentType.MERGER_PROXY:
                content = _MERGER_PROXY_DISCLAIMER + "\n" + content
            elif doc_type == DocumentType.EXPERT_NETWORK:
                content = _EXPERT_NETWORK_DISCLAIMER + "\n" + content

            header = f"### {doc_type.value}: {filename}"
            section_text = f"{header}\n\n{content}"
            sections.append((doc_type, filename, section_text))
            total_chars += len(section_text)

        # Truncate from lowest priority if over budget
        # sections is already highest-priority-first — allocate budget to
        # high-value docs first, low-priority docs get whatever remains
        if total_chars > max_chars:
            trimmed = []
            remaining = max_chars

            for doc_type, filename, text in sections:
                if remaining <= 0:
                    logger.warning(f"  Truncated entirely: {filename}")
                    continue

                if len(text) <= remaining:
                    trimmed.append(text)
                    remaining -= len(text)
                else:
                    # Partial truncation
                    truncated = text[:remaining] + f"\n\n[... truncated, {len(text) - remaining:,} chars omitted ...]"
                    trimmed.append(truncated)
                    remaining = 0
                    logger.warning(f"  Partially truncated: {filename}")

            sections_text = "\n\n---\n\n".join(trimmed)
        else:
            sections_text = "\n\n---\n\n".join(text for _, _, text in sections)

        return f"""
## External Research Materials

The following materials were provided as primary reference documents.
Cite specific passages with attribution. When materials contradict your thesis, address explicitly.

{sections_text}

---
"""

    def _classify_document(self, pdf_path: Path, cached_content: Optional[str] = None) -> DocumentType:
        """Classify a PDF by filename prefix, falling back to content auto-detection.

        Args:
            pdf_path: Path to the PDF file.
            cached_content: Pre-extracted content (if available from cache).

        Returns:
            Detected DocumentType.
        """
        filename_lower = pdf_path.name.lower()

        # 1. Filename prefix matching
        for prefix, doc_type in _PREFIX_MAP.items():
            if filename_lower.startswith(prefix):
                return doc_type

        # 2. Auto-detect from content (extract_pages only works on PDFs)
        if cached_content:
            content = cached_content
        elif pdf_path.suffix.lower() in (".htm", ".html"):
            try:
                content = pdf_path.read_text(encoding="utf-8", errors="replace")[:8000]
            except Exception:
                content = ""
        else:
            content = self._extract_pages(pdf_path, max_pages=2)
        if content:
            content_lower = content.lower()

            # SEC filing indicators
            sec_signals = [
                "united states securities and exchange commission",
                "form 10-k",
                "form 10-q",
                "annual report pursuant to section",
                "commission file number",
            ]
            if any(s in content_lower for s in sec_signals):
                return DocumentType.SEC_FILING

            # Merger/proxy indicators (check before generic SEC)
            proxy_signals = [
                "definitive proxy statement",
                "form def 14a",
                "merger agreement",
                "special meeting of stockholders",
                "defm14a",
            ]
            if any(s in content_lower for s in proxy_signals):
                return DocumentType.MERGER_PROXY

            # Transcript indicators
            transcript_signals = [
                "earnings call",
                "conference call",
                "q&a session",
                "operator:",
                "good morning, and welcome",
                "earnings conference",
            ]
            if any(s in content_lower for s in transcript_signals):
                return DocumentType.TRANSCRIPT

            # Expert network indicators
            expert_signals = [
                "expert call",
                "expert network",
                "alphasense",
                "tegus",
                "third bridge",
            ]
            if any(s in content_lower for s in expert_signals):
                return DocumentType.EXPERT_NETWORK

            # Sell-side indicators
            sellside_signals = [
                "price target",
                "buy rating",
                "sell rating",
                "hold rating",
                "overweight",
                "underweight",
                "disclosures",
                "important disclaimer",
                "equity research",
            ]
            if sum(1 for s in sellside_signals if s in content_lower) >= 2:
                return DocumentType.SELLSIDE

            # Presentation indicators
            presentation_signals = [
                "investor presentation",
                "investor day",
                "capital markets day",
            ]
            if any(s in content_lower for s in presentation_signals):
                return DocumentType.PRESENTATION

        return DocumentType.OTHER

    def _extract(self, pdf_path: Path, doc_type: DocumentType) -> str:
        """Extract text from a PDF or HTM based on its document type.

        Args:
            pdf_path: Path to the PDF or HTM file.
            doc_type: Classified document type.

        Returns:
            Extracted text as markdown-formatted string.
        """
        # HTM files: extract text by stripping HTML tags
        if pdf_path.suffix.lower() in (".htm", ".html"):
            return self._extract_htm(pdf_path, doc_type)
        if doc_type == DocumentType.SEC_FILING:
            return self._extract_sec_filing(pdf_path)
        if doc_type == DocumentType.MERGER_PROXY:
            return self._extract_merger_proxy(pdf_path)
        return self._extract_full(pdf_path)

    def _extract_sec_filing(self, pdf_path: Path) -> str:
        """Extract key sections from a 10-K filing (Items 1, 1A, 7, 7A).

        Uses font metadata to detect section headings, falls back to regex.
        Typically extracts ~15-30 pages from a 200-page filing.
        """
        try:
            import pymupdf
        except ImportError:
            logger.warning("pymupdf not installed, falling back to full extraction")
            return self._extract_full(pdf_path)

        doc = pymupdf.open(str(pdf_path))
        full_text = ""
        for page in doc:
            full_text += page.get_text("text") + "\n"
        doc.close()

        if not full_text.strip():
            return ""

        # Find Item boundaries
        sections = self._find_sec_sections(full_text)

        if sections:
            parts = [f"# SEC Filing: {pdf_path.stem}\n"]
            for item_key, (title, content) in sections.items():
                item_label = _SEC_ITEMS_WANTED.get(item_key, f"Item {item_key}")
                parts.append(f"## Item {item_key}: {item_label}\n\n{content.strip()}\n")
            return "\n\n".join(parts)

        # Fallback: if section detection fails, return full text
        logger.warning(f"  Could not detect Item sections in {pdf_path.name}, using full text")
        return f"# SEC Filing: {pdf_path.stem}\n\n{full_text}"

    def _extract_merger_proxy(self, pdf_path: Path) -> str:
        """Extract investment-relevant sections from a merger proxy / DEF 14A.

        Targets: Background of Merger, Board Recommendation, Fairness Opinion,
        Financial Projections, Merger Agreement terms, Termination fees,
        Interests of Directors. Typically extracts ~20-30pp from a 200+ page filing.
        """
        try:
            import pymupdf
        except ImportError:
            logger.warning("pymupdf not installed, falling back to full extraction")
            return self._extract_full(pdf_path)

        doc = pymupdf.open(str(pdf_path))
        full_text = ""
        for page in doc:
            full_text += page.get_text("text") + "\n"
        doc.close()

        if not full_text.strip():
            return ""

        # Find proxy section boundaries
        sections = self._find_proxy_sections(full_text)

        if sections:
            parts = [f"# Merger Proxy: {pdf_path.stem}\n"]
            for heading, content in sections:
                parts.append(f"## {heading}\n\n{content.strip()}\n")
            extracted = "\n\n".join(parts)
            ratio = len(extracted) / len(full_text) * 100 if full_text else 0
            logger.info(f"  Proxy extraction: {len(full_text):,} → {len(extracted):,} chars ({ratio:.0f}%)")
            return extracted

        # Fallback: full text if section detection fails
        logger.warning(f"  Could not detect proxy sections in {pdf_path.name}, using full text")
        return f"# Merger Proxy: {pdf_path.stem}\n\n{full_text}"

    def _find_proxy_sections(self, text: str) -> List[Tuple[str, str]]:
        """Find and extract investment-relevant sections from proxy text.

        Returns:
            List of (heading, content) tuples for matched sections.
        """
        matches = list(_PROXY_SECTION_PATTERN.finditer(text))
        if not matches:
            return []

        # Build list of (heading, start_pos) for wanted sections
        heading_positions = []
        for m in matches:
            heading = m.group(1).strip()
            heading_lower = heading.lower()
            # Check if this heading matches any wanted proxy section
            if any(wanted in heading_lower for wanted in _PROXY_SECTIONS_WANTED):
                heading_positions.append((heading, m.start()))

        if not heading_positions:
            return []

        # Extract content between consecutive headings
        sections = []
        all_match_starts = sorted(m.start() for m in matches)

        for i, (heading, start) in enumerate(heading_positions):
            # End = next heading in the full match list (not just wanted ones)
            pos_in_all = all_match_starts.index(start)
            if pos_in_all + 1 < len(all_match_starts):
                end = all_match_starts[pos_in_all + 1]
            else:
                end = len(text)

            content = text[start:end]
            sections.append((heading, content))

        return sections

    def _find_sec_sections(self, text: str) -> Dict[str, Tuple[str, str]]:
        """Find and extract SEC filing sections by Item number.

        Returns:
            Dict mapping item key (e.g., "1", "1a", "7") to (title, content).
        """
        # Find all Item headings with their positions
        matches = list(_ITEM_PATTERN.finditer(text))
        if not matches:
            return {}

        # Build index of item positions
        item_positions = []
        for m in matches:
            item_key = m.group(1).lower()
            start = m.start()
            item_positions.append((item_key, start))

        # Extract wanted sections
        sections = {}
        wanted_keys = set(_SEC_ITEMS_WANTED.keys())

        for i, (item_key, start) in enumerate(item_positions):
            if item_key not in wanted_keys:
                continue

            # Find end: next Item heading or end of text
            if i + 1 < len(item_positions):
                end = item_positions[i + 1][1]
            else:
                end = len(text)

            content = text[start:end]

            # Get title from the match line
            title_match = re.match(r".*?(?:ITEM|Item)\s+\S+[\.\:\s]+(.*?)(?:\n|$)", content)
            title = title_match.group(1).strip() if title_match else ""

            sections[item_key] = (title, content)

        return sections

    def _extract_full(self, pdf_path: Path) -> str:
        """Extract full text from a PDF document."""
        try:
            import pymupdf
        except ImportError:
            logger.error("pymupdf not installed. Install with: pip install pymupdf")
            return ""

        doc = pymupdf.open(str(pdf_path))
        parts = [f"# {pdf_path.stem}\n"]
        for i, page in enumerate(doc):
            page_text = page.get_text("text")
            if page_text.strip():
                parts.append(f"<!-- Page {i + 1} -->\n{page_text}")
        doc.close()

        return "\n\n".join(parts)

    def _extract_htm(self, htm_path: Path, doc_type: DocumentType) -> str:
        """Extract text from an HTM/HTML file by stripping tags.

        For SEC filings, applies the same Item-based section extraction
        as PDF SEC filings. For other types, returns full stripped text.
        """
        try:
            raw = htm_path.read_text(encoding="utf-8", errors="replace")
        except Exception as e:
            logger.warning(f"  Failed to read HTM: {htm_path.name}: {e}")
            return ""

        # Strip HTML tags to get plain text
        # Remove script/style blocks first
        text = re.sub(r"<(script|style)[^>]*>.*?</\1>", "", raw, flags=re.DOTALL | re.IGNORECASE)
        # Remove HTML tags
        text = re.sub(r"<[^>]+>", " ", text)
        # Decode HTML entities
        import html
        text = html.unescape(text)
        # Collapse whitespace
        text = re.sub(r"[ \t]+", " ", text)
        text = re.sub(r"\n\s*\n", "\n\n", text)
        text = text.strip()

        if not text:
            return ""

        # For SEC filings, extract key sections
        if doc_type == DocumentType.SEC_FILING:
            sections = self._find_sec_sections(text)
            if sections:
                parts = [f"# SEC Filing: {htm_path.stem}\n"]
                for item_key, (title, content) in sections.items():
                    item_label = _SEC_ITEMS_WANTED.get(item_key, f"Item {item_key}")
                    parts.append(f"## Item {item_key}: {item_label}\n\n{content.strip()}\n")
                return "\n\n".join(parts)

        # For merger/proxy, extract key sections
        if doc_type == DocumentType.MERGER_PROXY:
            sections = self._find_proxy_sections(text)
            if sections:
                parts = [f"# Merger Proxy: {htm_path.stem}\n"]
                for heading, content in sections:
                    parts.append(f"## {heading}\n\n{content.strip()}\n")
                return "\n\n".join(parts)

        return f"# {htm_path.stem}\n\n{text}"

    def _extract_pages(self, pdf_path: Path, max_pages: int = 2) -> str:
        """Extract text from first N pages of a PDF (for classification)."""
        try:
            import pymupdf
        except ImportError:
            return ""

        doc = pymupdf.open(str(pdf_path))
        text = ""
        for i, page in enumerate(doc):
            if i >= max_pages:
                break
            text += page.get_text("text") + "\n"
        doc.close()

        return text
