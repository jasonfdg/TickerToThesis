#!/usr/bin/env python3
"""
Short Seller Research Scraper
Scrapes high-quality short seller reports from Tier 1 sources:
- Kerrisdale Capital
- Grizzly Research
- Spruce Point Capital
- Muddy Waters Research
"""

import json
import hashlib
import re
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path
from typing import Optional
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup
from tqdm import tqdm


# ============================================================================
# Configuration
# ============================================================================

BASE_DIR = Path(__file__).parent.parent
DATA_DIR = BASE_DIR / "data" / "short_seller_research"
RAW_DIR = DATA_DIR / "raw"
STRUCTURED_DIR = DATA_DIR / "structured"
MANIFEST_DIR = DATA_DIR / "manifests"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
}

REQUEST_DELAY = 1.5  # seconds between requests


# ============================================================================
# Data Models
# ============================================================================

@dataclass
class ReportMetadata:
    """Metadata discovered from archive pages."""
    id: str
    source: str
    url: str
    title: str
    ticker: Optional[str] = None
    company_name: Optional[str] = None
    date: Optional[str] = None
    position_type: str = "short"
    pdf_url: Optional[str] = None


@dataclass
class ExtractedReport:
    """Fully extracted and scored report."""
    id: str
    source: str
    url: str
    pdf_url: Optional[str]
    company_name: str
    ticker: str
    author: str
    date: str
    position_type: str
    thesis_summary: str
    description_text: str
    quality_score: float
    quality_notes: str
    has_valuation_scenarios: bool
    has_kill_conditions: bool
    expert_quotes_count: int
    evidence_sources: list
    insider_signals: dict
    competitive_benchmarks: dict
    raw_html_path: str
    extracted_at: str


# ============================================================================
# Base Scraper Class
# ============================================================================

class BaseScraper(ABC):
    """Abstract base class for source-specific scrapers."""

    source_name: str = ""
    base_url: str = ""

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update(HEADERS)
        self._ensure_dirs()

    def _ensure_dirs(self):
        """Create necessary directories."""
        (RAW_DIR / self.source_name).mkdir(parents=True, exist_ok=True)
        STRUCTURED_DIR.mkdir(parents=True, exist_ok=True)
        MANIFEST_DIR.mkdir(parents=True, exist_ok=True)

    def _generate_id(self, url: str) -> str:
        """Generate unique ID from URL."""
        hash_str = hashlib.md5(url.encode()).hexdigest()[:12]
        return f"{self.source_name}_{hash_str}"

    def _fetch(self, url: str) -> Optional[str]:
        """Fetch URL with rate limiting."""
        try:
            time.sleep(REQUEST_DELAY)
            response = self.session.get(url, timeout=30)
            response.raise_for_status()
            return response.text
        except requests.RequestException as e:
            print(f"  [ERROR] Failed to fetch {url}: {e}")
            return None

    def _fetch_binary(self, url: str) -> Optional[bytes]:
        """Fetch binary content (PDFs)."""
        try:
            time.sleep(REQUEST_DELAY)
            response = self.session.get(url, timeout=60)
            response.raise_for_status()
            return response.content
        except requests.RequestException as e:
            print(f"  [ERROR] Failed to fetch PDF {url}: {e}")
            return None

    def _save_html(self, report_id: str, html: str) -> Path:
        """Save raw HTML."""
        path = RAW_DIR / self.source_name / f"{report_id}.html"
        path.write_text(html, encoding="utf-8")
        return path

    def _save_pdf(self, report_id: str, content: bytes) -> Path:
        """Save PDF."""
        path = RAW_DIR / self.source_name / f"{report_id}.pdf"
        path.write_bytes(content)
        return path

    def _save_manifest(self, reports: list[ReportMetadata]):
        """Save discovery manifest."""
        path = MANIFEST_DIR / f"{self.source_name}_manifest.json"
        data = [asdict(r) for r in reports]
        path.write_text(json.dumps(data, indent=2), encoding="utf-8")
        print(f"  [SAVED] Manifest: {path} ({len(reports)} reports)")

    def _save_structured(self, report: ExtractedReport):
        """Save structured JSON."""
        path = STRUCTURED_DIR / f"{report.id}.json"
        path.write_text(json.dumps(asdict(report), indent=2), encoding="utf-8")
        return path

    @abstractmethod
    def discover(self) -> list[ReportMetadata]:
        """Discover all reports from archive pages."""
        pass

    @abstractmethod
    def extract(self, metadata: ReportMetadata, html: str) -> Optional[ExtractedReport]:
        """Extract structured data from report HTML."""
        pass

    def download_and_extract(self, metadata: ReportMetadata) -> Optional[ExtractedReport]:
        """Download report and extract structured data."""
        print(f"  [FETCH] {metadata.title[:50]}...")

        html = self._fetch(metadata.url)
        if not html:
            return None

        # Save raw HTML
        html_path = self._save_html(metadata.id, html)

        # Download PDF if available
        if metadata.pdf_url:
            pdf_content = self._fetch_binary(metadata.pdf_url)
            if pdf_content:
                self._save_pdf(metadata.id, pdf_content)

        # Extract structured data
        report = self.extract(metadata, html)
        if report:
            report.raw_html_path = str(html_path)

        return report

    def run(self, min_score: float = 6.0):
        """Run full pipeline: discover -> download -> extract -> score -> save."""
        print(f"\n{'='*60}")
        print(f"[{self.source_name.upper()}] Starting scrape")
        print(f"{'='*60}")

        # Phase 1: Discovery
        print("\n[PHASE 1] Discovering reports...")
        reports = self.discover()
        self._save_manifest(reports)
        print(f"  [FOUND] {len(reports)} reports")

        # Phase 2-4: Download, Extract, Score
        print(f"\n[PHASE 2-4] Processing reports...")
        qualified = []

        for metadata in tqdm(reports, desc=f"Processing {self.source_name}"):
            report = self.download_and_extract(metadata)
            if report and report.quality_score >= min_score:
                self._save_structured(report)
                qualified.append(report)

        print(f"\n[COMPLETE] {len(qualified)}/{len(reports)} reports qualified (score >= {min_score})")
        return qualified


# ============================================================================
# Kerrisdale Capital Scraper
# ============================================================================

class KerrisdaleScraper(BaseScraper):
    """Scraper for Kerrisdale Capital reports."""

    source_name = "kerrisdale"
    base_url = "https://www.kerrisdalecap.com"

    def discover(self) -> list[ReportMetadata]:
        """Discover reports from paginated archive."""
        reports = []

        # Scrape both long and short categories
        categories = [
            ("/investments_categories/short/", "short"),
            ("/investments_categories/long/", "long"),
        ]

        for cat_path, position_type in categories:
            page = 1
            while True:
                if page == 1:
                    url = f"{self.base_url}{cat_path}"
                else:
                    url = f"{self.base_url}{cat_path}page/{page}/"

                print(f"  [SCAN] {url}")
                html = self._fetch(url)
                if not html:
                    break

                soup = BeautifulSoup(html, "lxml")
                articles = soup.select("article.post")

                if not articles:
                    break

                for article in articles:
                    link = article.select_one("h2 a, .entry-title a")
                    if not link:
                        continue

                    report_url = link.get("href", "")
                    title = link.get_text(strip=True)

                    # Extract date
                    date_elem = article.select_one(".entry-date, time")
                    date_str = date_elem.get_text(strip=True) if date_elem else None

                    # Try to extract ticker from title (often in parentheses)
                    ticker_match = re.search(r'\(([A-Z]{1,5})\)', title)
                    ticker = ticker_match.group(1) if ticker_match else None

                    report_id = self._generate_id(report_url)

                    reports.append(ReportMetadata(
                        id=report_id,
                        source=self.source_name,
                        url=report_url,
                        title=title,
                        ticker=ticker,
                        date=date_str,
                        position_type=position_type,
                    ))

                page += 1
                if page > 20:  # Safety limit
                    break

        return reports

    def extract(self, metadata: ReportMetadata, html: str) -> Optional[ExtractedReport]:
        """Extract structured data from Kerrisdale report."""
        soup = BeautifulSoup(html, "lxml")

        # Get main content
        content = soup.select_one(".entry-content, article")
        if not content:
            return None

        text = content.get_text(separator="\n", strip=True)

        # Look for PDF link
        pdf_link = soup.select_one('a[href*=".pdf"]')
        pdf_url = pdf_link.get("href") if pdf_link else None
        if pdf_url and not pdf_url.startswith("http"):
            pdf_url = urljoin(self.base_url, pdf_url)

        # Extract company name from title
        company_name = re.sub(r'\([A-Z]{1,5}\)', '', metadata.title).strip()
        company_name = re.sub(r'\s*[-–]\s*.*$', '', company_name).strip()

        # Generate thesis summary (first meaningful paragraph)
        paragraphs = [p.strip() for p in text.split("\n\n") if len(p.strip()) > 100]
        thesis_summary = paragraphs[0] if paragraphs else ""

        # Score the report
        score, notes = self._score_report(text, metadata.position_type)

        return ExtractedReport(
            id=metadata.id,
            source=self.source_name,
            url=metadata.url,
            pdf_url=pdf_url,
            company_name=company_name or metadata.title,
            ticker=metadata.ticker or "UNKNOWN",
            author="Kerrisdale Capital",
            date=metadata.date or "",
            position_type=metadata.position_type,
            thesis_summary=thesis_summary[:500],
            description_text=text,
            quality_score=score,
            quality_notes=notes,
            has_valuation_scenarios=self._has_valuation(text),
            has_kill_conditions=self._has_kill_conditions(text),
            expert_quotes_count=self._count_quotes(text),
            evidence_sources=self._extract_sources(text),
            insider_signals=self._extract_insider_signals(text),
            competitive_benchmarks={},
            raw_html_path="",
            extracted_at=datetime.now().isoformat(),
        )

    def _score_report(self, text: str, position_type: str) -> tuple[float, str]:
        """Score report quality based on memo engine criteria."""
        score = 5.0
        notes = []

        word_count = len(text.split())

        # Length bonus
        if word_count > 3000:
            score += 0.5
            notes.append("Substantial length")

        # Quantification
        if re.search(r'\$\d+[MBmb]|\d+%|\d+x', text):
            score += 0.5
            notes.append("Quantified claims")

        # Evidence sources
        source_keywords = ["SEC filing", "10-K", "10-Q", "earnings call", "site visit",
                          "former employee", "industry expert", "court filing", "PACER"]
        sources_found = sum(1 for kw in source_keywords if kw.lower() in text.lower())
        if sources_found >= 3:
            score += 1.0
            notes.append(f"{sources_found} evidence sources")
        elif sources_found >= 1:
            score += 0.5

        # Valuation
        if self._has_valuation(text):
            score += 0.5
            notes.append("Valuation analysis")

        # Kill conditions (for shorts)
        if position_type == "short" and self._has_kill_conditions(text):
            score += 0.5
            notes.append("Clear kill conditions")

        # Peer comparison
        if re.search(r'peer|competitor|industry average|vs\.?\s+[A-Z]{2,5}', text, re.I):
            score += 0.5
            notes.append("Peer comparison")

        return min(score, 10.0), "; ".join(notes) if notes else "Standard report"

    def _has_valuation(self, text: str) -> bool:
        """Check if report has valuation scenarios."""
        patterns = [
            r'price target',
            r'fair value',
            r'upside.{0,20}downside',
            r'bull.{0,20}bear.{0,20}case',
            r'base case',
            r'intrinsic value',
            r'\d+x.{0,10}(EBITDA|earnings|revenue)',
        ]
        return any(re.search(p, text, re.I) for p in patterns)

    def _has_kill_conditions(self, text: str) -> bool:
        """Check if report has clear kill conditions."""
        patterns = [
            r'we would exit',
            r'close.{0,10}position',
            r'stop.{0,10}loss',
            r'catalyst',
            r'timeline',
            r'we expect.{0,30}(months|years)',
        ]
        return any(re.search(p, text, re.I) for p in patterns)

    def _count_quotes(self, text: str) -> int:
        """Count expert/source quotes."""
        quote_patterns = [
            r'"[^"]{20,}"',
            r'according to',
            r'stated that',
            r'told us',
        ]
        return sum(len(re.findall(p, text, re.I)) for p in quote_patterns)

    def _extract_sources(self, text: str) -> list[str]:
        """Extract evidence source types."""
        sources = []
        source_map = {
            "SEC filings": r"10-[KQ]|SEC filing|EDGAR",
            "earnings calls": r"earnings call|conference call|management.{0,10}said",
            "site visits": r"site visit|visited.{0,20}facility",
            "former employees": r"former employee|ex-employee",
            "court filings": r"court filing|lawsuit|PACER|litigation",
            "industry experts": r"industry expert|channel check",
        }
        for source, pattern in source_map.items():
            if re.search(pattern, text, re.I):
                sources.append(source)
        return sources

    def _extract_insider_signals(self, text: str) -> dict:
        """Extract insider trading signals."""
        return {
            "form4_sales": bool(re.search(r"Form 4|insider.{0,20}(sold|sale)", text, re.I)),
            "margin_loans": bool(re.search(r"margin loan|pledged shares", text, re.I)),
            "stock_pledges": bool(re.search(r"stock pledge|collateral", text, re.I)),
        }


# ============================================================================
# Grizzly Research Scraper
# ============================================================================

class GrizzlyScraper(BaseScraper):
    """Scraper for Grizzly Research reports."""

    source_name = "grizzly"
    base_url = "https://grizzlyreports.com"

    def discover(self) -> list[ReportMetadata]:
        """Discover reports from archive."""
        reports = []
        page = 1

        while True:
            if page == 1:
                url = f"{self.base_url}/category/reports/"
            else:
                url = f"{self.base_url}/category/reports/page/{page}/"

            print(f"  [SCAN] {url}")
            html = self._fetch(url)
            if not html:
                break

            soup = BeautifulSoup(html, "lxml")
            articles = soup.select("article, .post")

            if not articles:
                break

            for article in articles:
                link = article.select_one("h2 a, .entry-title a, a.post-title")
                if not link:
                    continue

                report_url = link.get("href", "")
                if not report_url.startswith("http"):
                    report_url = urljoin(self.base_url, report_url)

                title = link.get_text(strip=True)

                # Extract ticker from title
                ticker_match = re.search(r'\((?:NASDAQ|NYSE|AMEX)?:?\s*([A-Z]{1,5})\)', title)
                ticker = ticker_match.group(1) if ticker_match else None

                # Extract date
                date_elem = article.select_one("time, .entry-date, .post-date")
                date_str = date_elem.get_text(strip=True) if date_elem else None

                report_id = self._generate_id(report_url)

                reports.append(ReportMetadata(
                    id=report_id,
                    source=self.source_name,
                    url=report_url,
                    title=title,
                    ticker=ticker,
                    date=date_str,
                    position_type="short",
                ))

            page += 1
            if page > 15:
                break

        return reports

    def extract(self, metadata: ReportMetadata, html: str) -> Optional[ExtractedReport]:
        """Extract structured data from Grizzly report."""
        soup = BeautifulSoup(html, "lxml")

        content = soup.select_one(".entry-content, .post-content, article")
        if not content:
            return None

        text = content.get_text(separator="\n", strip=True)

        # Look for PDF link
        pdf_link = soup.select_one('a[href*=".pdf"]')
        pdf_url = pdf_link.get("href") if pdf_link else None
        if pdf_url and not pdf_url.startswith("http"):
            pdf_url = urljoin(self.base_url, pdf_url)

        # Company name
        company_name = re.sub(r'\([^)]+\)', '', metadata.title).strip()
        company_name = re.sub(r'\s*[-–:]\s*.*$', '', company_name).strip()

        # Thesis summary
        paragraphs = [p.strip() for p in text.split("\n\n") if len(p.strip()) > 100]
        thesis_summary = paragraphs[0] if paragraphs else ""

        # Use Kerrisdale's scoring (similar methodology)
        kerrisdale = KerrisdaleScraper()
        score, notes = kerrisdale._score_report(text, "short")

        return ExtractedReport(
            id=metadata.id,
            source=self.source_name,
            url=metadata.url,
            pdf_url=pdf_url,
            company_name=company_name or metadata.title,
            ticker=metadata.ticker or "UNKNOWN",
            author="Grizzly Research",
            date=metadata.date or "",
            position_type="short",
            thesis_summary=thesis_summary[:500],
            description_text=text,
            quality_score=score,
            quality_notes=notes,
            has_valuation_scenarios=kerrisdale._has_valuation(text),
            has_kill_conditions=kerrisdale._has_kill_conditions(text),
            expert_quotes_count=kerrisdale._count_quotes(text),
            evidence_sources=kerrisdale._extract_sources(text),
            insider_signals=kerrisdale._extract_insider_signals(text),
            competitive_benchmarks={},
            raw_html_path="",
            extracted_at=datetime.now().isoformat(),
        )


# ============================================================================
# Spruce Point Capital Scraper
# ============================================================================

class SprucePointScraper(BaseScraper):
    """Scraper for Spruce Point Capital reports."""

    source_name = "spruce_point"
    base_url = "https://www.sprucepointcap.com"

    def discover(self) -> list[ReportMetadata]:
        """Discover reports from research page."""
        reports = []
        url = f"{self.base_url}/research"

        print(f"  [SCAN] {url}")
        html = self._fetch(url)
        if not html:
            return reports

        soup = BeautifulSoup(html, "lxml")

        # Look for report cards/items
        items = soup.select(".research-item, .report-card, article, .post")

        for item in items:
            link = item.select_one("a[href]")
            if not link:
                continue

            report_url = link.get("href", "")
            if not report_url.startswith("http"):
                report_url = urljoin(self.base_url, report_url)

            # Skip non-report links
            if "/research" not in report_url and "/report" not in report_url.lower():
                continue

            title = link.get_text(strip=True) or item.get_text(strip=True)[:100]

            # Extract ticker
            ticker_match = re.search(r'\((?:NASDAQ|NYSE)?:?\s*([A-Z]{1,5})\)', title)
            ticker = ticker_match.group(1) if ticker_match else None

            report_id = self._generate_id(report_url)

            reports.append(ReportMetadata(
                id=report_id,
                source=self.source_name,
                url=report_url,
                title=title,
                ticker=ticker,
                position_type="short",
            ))

        return reports

    def extract(self, metadata: ReportMetadata, html: str) -> Optional[ExtractedReport]:
        """Extract structured data from Spruce Point report."""
        soup = BeautifulSoup(html, "lxml")

        content = soup.select_one(".entry-content, .post-content, article, main")
        if not content:
            return None

        text = content.get_text(separator="\n", strip=True)

        # PDF link
        pdf_link = soup.select_one('a[href*=".pdf"]')
        pdf_url = pdf_link.get("href") if pdf_link else None
        if pdf_url and not pdf_url.startswith("http"):
            pdf_url = urljoin(self.base_url, pdf_url)

        company_name = re.sub(r'\([^)]+\)', '', metadata.title).strip()

        paragraphs = [p.strip() for p in text.split("\n\n") if len(p.strip()) > 100]
        thesis_summary = paragraphs[0] if paragraphs else ""

        kerrisdale = KerrisdaleScraper()
        score, notes = kerrisdale._score_report(text, "short")

        return ExtractedReport(
            id=metadata.id,
            source=self.source_name,
            url=metadata.url,
            pdf_url=pdf_url,
            company_name=company_name or metadata.title,
            ticker=metadata.ticker or "UNKNOWN",
            author="Spruce Point Capital",
            date=metadata.date or "",
            position_type="short",
            thesis_summary=thesis_summary[:500],
            description_text=text,
            quality_score=score,
            quality_notes=notes,
            has_valuation_scenarios=kerrisdale._has_valuation(text),
            has_kill_conditions=kerrisdale._has_kill_conditions(text),
            expert_quotes_count=kerrisdale._count_quotes(text),
            evidence_sources=kerrisdale._extract_sources(text),
            insider_signals=kerrisdale._extract_insider_signals(text),
            competitive_benchmarks={},
            raw_html_path="",
            extracted_at=datetime.now().isoformat(),
        )


# ============================================================================
# Muddy Waters Scraper
# ============================================================================

class MuddyWatersScraper(BaseScraper):
    """Scraper for Muddy Waters Research reports."""

    source_name = "muddy_waters"
    base_url = "https://muddywatersresearch.com"

    def discover(self) -> list[ReportMetadata]:
        """Discover reports from research archive."""
        reports = []
        url = f"{self.base_url}/research/"

        print(f"  [SCAN] {url}")
        html = self._fetch(url)
        if not html:
            return reports

        soup = BeautifulSoup(html, "lxml")

        # Look for company links in research section
        links = soup.select('a[href*="/research/"]')

        seen_urls = set()
        for link in links:
            report_url = link.get("href", "")
            if not report_url.startswith("http"):
                report_url = urljoin(self.base_url, report_url)

            # Skip duplicates and main research page
            if report_url in seen_urls or report_url.rstrip("/") == f"{self.base_url}/research":
                continue
            seen_urls.add(report_url)

            title = link.get_text(strip=True)
            if not title or len(title) < 3:
                continue

            report_id = self._generate_id(report_url)

            reports.append(ReportMetadata(
                id=report_id,
                source=self.source_name,
                url=report_url,
                title=title,
                position_type="short",
            ))

        return reports

    def extract(self, metadata: ReportMetadata, html: str) -> Optional[ExtractedReport]:
        """Extract structured data from Muddy Waters report."""
        soup = BeautifulSoup(html, "lxml")

        content = soup.select_one(".entry-content, .post-content, article, main")
        if not content:
            return None

        text = content.get_text(separator="\n", strip=True)

        # PDF link
        pdf_link = soup.select_one('a[href*=".pdf"]')
        pdf_url = pdf_link.get("href") if pdf_link else None
        if pdf_url and not pdf_url.startswith("http"):
            pdf_url = urljoin(self.base_url, pdf_url)

        company_name = metadata.title

        # Try to extract ticker from page
        ticker_match = re.search(r'\(([A-Z]{1,5})\)', text[:500])
        ticker = ticker_match.group(1) if ticker_match else metadata.ticker

        paragraphs = [p.strip() for p in text.split("\n\n") if len(p.strip()) > 100]
        thesis_summary = paragraphs[0] if paragraphs else ""

        kerrisdale = KerrisdaleScraper()
        score, notes = kerrisdale._score_report(text, "short")

        return ExtractedReport(
            id=metadata.id,
            source=self.source_name,
            url=metadata.url,
            pdf_url=pdf_url,
            company_name=company_name,
            ticker=ticker or "UNKNOWN",
            author="Muddy Waters Research",
            date=metadata.date or "",
            position_type="short",
            thesis_summary=thesis_summary[:500],
            description_text=text,
            quality_score=score,
            quality_notes=notes,
            has_valuation_scenarios=kerrisdale._has_valuation(text),
            has_kill_conditions=kerrisdale._has_kill_conditions(text),
            expert_quotes_count=kerrisdale._count_quotes(text),
            evidence_sources=kerrisdale._extract_sources(text),
            insider_signals=kerrisdale._extract_insider_signals(text),
            competitive_benchmarks={},
            raw_html_path="",
            extracted_at=datetime.now().isoformat(),
        )


# ============================================================================
# Main Entry Point
# ============================================================================

def main():
    """Run all scrapers."""
    print("=" * 60)
    print("SHORT SELLER RESEARCH SCRAPER")
    print("=" * 60)
    print(f"Output directory: {DATA_DIR}")

    scrapers = [
        KerrisdaleScraper(),
        GrizzlyScraper(),
        SprucePointScraper(),
        MuddyWatersScraper(),
    ]

    all_qualified = []

    for scraper in scrapers:
        try:
            qualified = scraper.run(min_score=6.0)
            all_qualified.extend(qualified)
        except Exception as e:
            print(f"[ERROR] {scraper.source_name} failed: {e}")
            import traceback
            traceback.print_exc()

    print("\n" + "=" * 60)
    print("FINAL SUMMARY")
    print("=" * 60)
    print(f"Total qualified reports: {len(all_qualified)}")
    print(f"Output location: {STRUCTURED_DIR}")

    # Save summary
    summary = {
        "scraped_at": datetime.now().isoformat(),
        "total_qualified": len(all_qualified),
        "by_source": {},
    }
    for scraper in scrapers:
        count = len([r for r in all_qualified if r.source == scraper.source_name])
        summary["by_source"][scraper.source_name] = count

    summary_path = DATA_DIR / "scrape_summary.json"
    summary_path.write_text(json.dumps(summary, indent=2))
    print(f"Summary saved: {summary_path}")


if __name__ == "__main__":
    main()
