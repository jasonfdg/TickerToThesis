"""
Hindenburg Research Scraper
High-quality forensic short reports - 100% free, ungated.
"""

import re
from typing import Dict, List, Optional
from bs4 import BeautifulSoup
from .base_source import BaseSource
import sys
sys.path.insert(0, str(BaseSource.PROJECT_ROOT if hasattr(BaseSource, 'PROJECT_ROOT') else __file__))

from pathlib import Path
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from scraper.quality_scorer import score_memo, quick_quality_check


class HindenburgSource(BaseSource):
    """Scraper for Hindenburg Research reports."""

    SOURCE_NAME = "hindenburg"
    BASE_URL = "https://hindenburgresearch.com"

    # Known high-quality reports with direct URLs - comprehensive list
    KNOWN_REPORTS = [
        {"url": "https://hindenburgresearch.com/carvana/", "title": "Carvana: A Father-Son Accounting Grift"},
        {"url": "https://hindenburgresearch.com/sezzle/", "title": "Sezzle: Failing Buy Now Pay Later Platform"},
        {"url": "https://hindenburgresearch.com/pacs/", "title": "PACS Group: Scamming Taxpayers"},
        {"url": "https://hindenburgresearch.com/roblox/", "title": "Roblox: Inflated Key Metrics"},
        {"url": "https://hindenburgresearch.com/aile/", "title": "iLearningEngines: Artificial Revenue"},
        {"url": "https://hindenburgresearch.com/smci/", "title": "Super Micro: Accounting Manipulation"},
        {"url": "https://hindenburgresearch.com/axos/", "title": "Axos: Commercial Real Estate Problems"},
        {"url": "https://hindenburgresearch.com/adani/", "title": "Adani Group: Largest Con in Corporate History"},
        {"url": "https://hindenburgresearch.com/icahn/", "title": "Carl Icahn: The Corporate Raider"},
        {"url": "https://hindenburgresearch.com/tether/", "title": "Tether: Crypto's Largest Stablecoin"},
        {"url": "https://hindenburgresearch.com/nikola/", "title": "Nikola: Intricate Fraud"},
        {"url": "https://hindenburgresearch.com/lordstown-motors/", "title": "Lordstown Motors: Fake Orders"},
        {"url": "https://hindenburgresearch.com/clover-health/", "title": "Clover Health: Undisclosed DOJ Investigation"},
        {"url": "https://hindenburgresearch.com/mullen/", "title": "Mullen Automotive: Electric Vehicle Fraud"},
        {"url": "https://hindenburgresearch.com/kandi/", "title": "Kandi: Fictitious Sales"},
        {"url": "https://hindenburgresearch.com/gsx/", "title": "GSX Techedu: Real Business with Fake Students"},
        {"url": "https://hindenburgresearch.com/bloom-energy/", "title": "Bloom Energy: Accounting Issues"},
        {"url": "https://hindenburgresearch.com/loop-industries/", "title": "Loop Industries: Broken Promises"},
        {"url": "https://hindenburgresearch.com/ideanomics/", "title": "Ideanomics: Fake MEG Deal"},
        {"url": "https://hindenburgresearch.com/quantumscape/", "title": "QuantumScape: Solid State Deception"},
        {"url": "https://hindenburgresearch.com/draft-kings/", "title": "DraftKings: Black Market Operations"},
        {"url": "https://hindenburgresearch.com/scopely/", "title": "Scopely: Hidden Related Party"},
        {"url": "https://hindenburgresearch.com/ebang/", "title": "Ebang: Fake Revenue"},
        {"url": "https://hindenburgresearch.com/wins-finance/", "title": "Wins Finance: Zero Revenue"},
        {"url": "https://hindenburgresearch.com/nio/", "title": "NIO: User Growth Questions"},
        {"url": "https://hindenburgresearch.com/sc-worx/", "title": "SCWorx: COVID Scam"},
        {"url": "https://hindenburgresearch.com/genius-brands/", "title": "Genius Brands: Promotion Questions"},
        {"url": "https://hindenburgresearch.com/predictive-oncology/", "title": "Predictive Oncology: Shell Company"},
        {"url": "https://hindenburgresearch.com/stable-road/", "title": "Stable Road SPAC: Lordstown Questions"},
        {"url": "https://hindenburgresearch.com/dropcar/", "title": "DropCar: Implosion"},
    ]

    def discover_documents(self) -> List[Dict]:
        """Discover all Hindenburg reports from their homepage."""
        documents = list(self.KNOWN_REPORTS)

        # Also try to fetch more from the main page
        html = self.fetch_html(self.BASE_URL)
        if html:
            soup = BeautifulSoup(html, 'html.parser')

            # Find all article/report links
            for link in soup.find_all('a', href=True):
                href = link['href']

                # Look for report-like URLs
                if href.startswith('https://hindenburgresearch.com/') and href != self.BASE_URL + '/':
                    # Skip navigation pages
                    if any(x in href for x in ['/gratitude/', '/about/', '/contact/', '/disclaimer/']):
                        continue

                    title = link.get_text(strip=True)
                    if title and len(title) >= 5:
                        documents.append({
                            'url': href,
                            'title': title,
                        })

        # Deduplicate by URL
        seen = set()
        unique_docs = []
        for doc in documents:
            if doc['url'] not in seen:
                seen.add(doc['url'])
                unique_docs.append(doc)

        return unique_docs

    def extract_document(self, doc_info: Dict) -> Optional[Dict]:
        """Extract content from a Hindenburg report."""
        url = doc_info['url']
        doc_id = self._generate_id(url)

        # Skip if already extracted
        if self._is_already_extracted(doc_id):
            return None

        # Fetch the report page
        html = self.fetch_html(url)
        if not html:
            return None

        soup = BeautifulSoup(html, 'html.parser')

        # Extract title
        title_elem = soup.find('h1')
        title = title_elem.get_text(strip=True) if title_elem else doc_info.get('title', '')

        # Extract date
        date_elem = soup.find('time') or soup.find(class_=re.compile(r'date|posted|published'))
        date = date_elem.get_text(strip=True) if date_elem else ""

        # Extract main content
        content_elem = soup.find('article') or soup.find(class_=re.compile(r'content|post|entry'))
        if not content_elem:
            content_elem = soup.find('main') or soup.find('body')

        if not content_elem:
            return None

        # Get text content
        description_text = content_elem.get_text(separator='\n', strip=True)

        # Quick quality check
        if not quick_quality_check(description_text):
            return None

        # Full quality score
        quality = score_memo(description_text, quality_threshold=5.0)
        if not quality['passes_quality_bar']:
            print(f"            Quality score {quality['weighted_total']:.1f} < 5.0")
            return None

        # Extract ticker from title (usually in format "Company: Ticker")
        ticker_match = re.search(r'\(([A-Z]{1,5})\)', title) or re.search(r':?\s*([A-Z]{2,5})$', title)
        ticker = ticker_match.group(1) if ticker_match else None

        # Company name is usually before the colon or ticker
        company_name = re.sub(r'\s*[\(\:].*$', '', title).strip()

        # Save raw HTML
        raw_path = self.save_raw(html, doc_id, "html")

        # Create record
        record = self.create_extracted_record(
            doc_id=doc_id,
            url=url,
            company_name=company_name,
            ticker=ticker,
            author="Hindenburg Research",
            date=date,
            position_type="short",
            description_text=description_text,
            quality_score=quality,
            raw_path=raw_path,
        )

        # Save extracted JSON
        self.save_extracted(record, doc_id)

        return record


if __name__ == "__main__":
    scraper = HindenburgSource(delay=2.0)
    scraper.run(max_docs=50)
