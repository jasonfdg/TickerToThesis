"""
Base class for buyside research source scrapers.
"""

import json
import time
import random
import hashlib
from pathlib import Path
from datetime import datetime
from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Tuple

import requests
from bs4 import BeautifulSoup

# Project paths
PROJECT_ROOT = Path(__file__).parent.parent.parent
RAW_DIR = PROJECT_ROOT / "data" / "buyside_research" / "raw"
EXTRACTED_DIR = PROJECT_ROOT / "data" / "buyside_research" / "extracted"

# Ensure directories exist
RAW_DIR.mkdir(parents=True, exist_ok=True)
EXTRACTED_DIR.mkdir(parents=True, exist_ok=True)


class BaseSource(ABC):
    """Base class for all buyside research scrapers."""

    SOURCE_NAME = "base"
    BASE_URL = ""

    def __init__(self, delay: float = 2.0, jitter: float = 1.0):
        self.delay = delay
        self.jitter = jitter
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
        })

    def _wait(self):
        """Wait with jitter between requests."""
        wait_time = self.delay + random.uniform(0, self.jitter)
        time.sleep(wait_time)

    def _generate_id(self, url: str) -> str:
        """Generate a unique ID from URL."""
        return hashlib.md5(url.encode()).hexdigest()[:12]

    def _get_raw_path(self, doc_id: str, extension: str = "html") -> Path:
        """Get path for raw file."""
        return RAW_DIR / f"{self.SOURCE_NAME}_{doc_id}.{extension}"

    def _get_extracted_path(self, doc_id: str) -> Path:
        """Get path for extracted JSON."""
        return EXTRACTED_DIR / f"{self.SOURCE_NAME}_{doc_id}.json"

    def _is_already_extracted(self, doc_id: str) -> bool:
        """Check if document is already extracted."""
        return self._get_extracted_path(doc_id).exists()

    def fetch_html(self, url: str) -> Optional[str]:
        """Fetch HTML content from URL."""
        try:
            self._wait()
            response = self.session.get(url, timeout=30)
            response.raise_for_status()
            return response.text
        except Exception as e:
            print(f"    Error fetching {url}: {e}")
            return None

    def fetch_pdf(self, url: str) -> Optional[bytes]:
        """Fetch PDF content from URL."""
        try:
            self._wait()
            response = self.session.get(url, timeout=60)
            response.raise_for_status()
            if 'pdf' in response.headers.get('content-type', '').lower() or url.endswith('.pdf'):
                return response.content
            return None
        except Exception as e:
            print(f"    Error fetching PDF {url}: {e}")
            return None

    def save_raw(self, content: bytes | str, doc_id: str, extension: str = "html") -> Path:
        """Save raw content to file."""
        path = self._get_raw_path(doc_id, extension)
        if isinstance(content, str):
            path.write_text(content, encoding='utf-8')
        else:
            path.write_bytes(content)
        return path

    def save_extracted(self, data: Dict, doc_id: str) -> Path:
        """Save extracted JSON."""
        path = self._get_extracted_path(doc_id)
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        return path

    def create_extracted_record(
        self,
        doc_id: str,
        url: str,
        company_name: str,
        ticker: Optional[str],
        author: str,
        date: str,
        position_type: str,
        description_text: str,
        quality_score: Dict,
        raw_path: Path,
    ) -> Dict:
        """Create a VIC-compatible extracted record."""
        # Derive additional quality attributes from scores
        valuation_rigor = quality_score.get("valuation_rigor", 0)
        risk_honesty = quality_score.get("risk_honesty", 0)
        evidence_quality = quality_score.get("evidence_quality", 0)

        # Estimate expert quotes based on evidence score (elite avg is 2.3)
        expert_quotes_count = max(0, int(evidence_quality / 3))

        # Generate quality notes
        notes = []
        if valuation_rigor >= 6:
            notes.append("Strong valuation framework")
        if risk_honesty >= 5:
            notes.append("Clear kill conditions defined")
        if evidence_quality >= 7:
            notes.append("Primary research with expert quotes")
        quality_notes = "; ".join(notes) if notes else "Meets quality threshold"

        return {
            "id": doc_id,
            "source": self.SOURCE_NAME,
            "url": url,
            "company_name": company_name,
            "ticker": ticker,
            "author": author,
            "date": date,
            "position_type": position_type,
            "thesis_summary": description_text[:500] + "..." if len(description_text) > 500 else description_text,
            "description_text": description_text,
            "price": None,
            "shares_out": None,
            "market_cap": None,
            "net_debt": None,
            "quality_score": quality_score.get("weighted_total"),
            "quality_notes": quality_notes,
            "quality_votes": None,
            "quality_breakdown": {
                "variant_view_clarity": quality_score.get("variant_view_clarity"),
                "evidence_quality": quality_score.get("evidence_quality"),
                "valuation_rigor": quality_score.get("valuation_rigor"),
                "risk_honesty": quality_score.get("risk_honesty"),
                "decision_readiness": quality_score.get("decision_readiness"),
            },
            "has_valuation_scenarios": valuation_rigor >= 4,
            "has_kill_conditions": risk_honesty >= 3,
            "expert_quotes_count": expert_quotes_count,
            "performance_score": None,
            "performance_votes": None,
            "performance_breakdown": None,
            "comments": [],
            "comment_count": 0,
            "has_content": True,
            "raw_file_path": str(raw_path),
            "extracted_at": datetime.now().isoformat(),
            "word_count": quality_score.get("word_count"),
        }

    @abstractmethod
    def discover_documents(self) -> List[Dict]:
        """
        Discover available documents from the source.
        Returns list of dicts with at least 'url' and 'title' keys.
        """
        pass

    @abstractmethod
    def extract_document(self, doc_info: Dict) -> Optional[Dict]:
        """
        Extract content from a single document.
        Returns extracted record dict or None if extraction fails.
        """
        pass

    def run(self, max_docs: int = 100) -> Tuple[int, int]:
        """
        Run the full scrape pipeline.
        Returns (successful_count, failed_count).
        """
        print(f"\n{'='*60}")
        print(f"  {self.SOURCE_NAME.upper()} SCRAPER")
        print(f"{'='*60}")

        # Discover documents
        print(f"\n[1/3] Discovering documents...")
        documents = self.discover_documents()
        print(f"      Found {len(documents)} documents")

        # Filter already extracted
        new_docs = []
        for doc in documents:
            doc_id = self._generate_id(doc['url'])
            if not self._is_already_extracted(doc_id):
                new_docs.append(doc)

        print(f"      {len(new_docs)} new documents to process")

        if not new_docs:
            return 0, 0

        # Limit to max_docs
        docs_to_process = new_docs[:max_docs]

        # Extract documents
        print(f"\n[2/3] Extracting documents...")
        successful = 0
        failed = 0

        for i, doc in enumerate(docs_to_process, 1):
            print(f"      [{i}/{len(docs_to_process)}] {doc.get('title', doc['url'])[:50]}...")

            try:
                result = self.extract_document(doc)
                if result:
                    successful += 1
                    print(f"            ✓ Extracted (score: {result.get('quality_score', 'N/A')})")
                else:
                    failed += 1
                    print(f"            ✗ Failed quality check or extraction")
            except Exception as e:
                failed += 1
                print(f"            ✗ Error: {e}")

        print(f"\n[3/3] Summary: {successful} extracted, {failed} failed")
        return successful, failed
