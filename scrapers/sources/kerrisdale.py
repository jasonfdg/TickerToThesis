"""
Kerrisdale Capital Scraper
Detailed long/short research reports - 100% free, ungated.
"""

import re
from typing import Dict, List, Optional
from bs4 import BeautifulSoup
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent.parent
import sys
sys.path.insert(0, str(PROJECT_ROOT))

from scraper.sources.base_source import BaseSource
from scraper.quality_scorer import score_memo, quick_quality_check


class KerrrisdaleSource(BaseSource):
    """Scraper for Kerrisdale Capital research reports."""

    SOURCE_NAME = "kerrisdale"
    BASE_URL = "https://www.kerrisdalecap.com"

    def discover_documents(self) -> List[Dict]:
        """Discover all Kerrisdale reports."""
        documents = []

        # Check both short and long archives
        archives = [
            f"{self.BASE_URL}/investments_categories/short/",
            f"{self.BASE_URL}/investments_categories/long/",
            f"{self.BASE_URL}/blog/",
        ]

        for archive_url in archives:
            html = self.fetch_html(archive_url)
            if not html:
                continue

            soup = BeautifulSoup(html, 'html.parser')

            # Find all article/report links
            for link in soup.find_all('a', href=True):
                href = link['href']

                # Look for investment pages or blog posts with reports
                if '/investments/' in href or '/blog/' in href:
                    if href.startswith('/'):
                        url = f"{self.BASE_URL}{href}"
                    elif href.startswith('http'):
                        url = href
                    else:
                        continue

                    title = link.get_text(strip=True)
                    if not title or len(title) < 3:
                        # Try to get title from parent or heading
                        parent = link.find_parent(['article', 'div', 'li'])
                        if parent:
                            h = parent.find(['h1', 'h2', 'h3', 'h4'])
                            if h:
                                title = h.get_text(strip=True)

                    if title and len(title) >= 3:
                        documents.append({
                            'url': url,
                            'title': title,
                            'archive': archive_url,
                        })

        # Deduplicate
        seen = set()
        unique_docs = []
        for doc in documents:
            if doc['url'] not in seen:
                seen.add(doc['url'])
                unique_docs.append(doc)

        return unique_docs

    def extract_document(self, doc_info: Dict) -> Optional[Dict]:
        """Extract content from a Kerrisdale report page."""
        url = doc_info['url']
        doc_id = self._generate_id(url)

        if self._is_already_extracted(doc_id):
            return None

        html = self.fetch_html(url)
        if not html:
            return None

        soup = BeautifulSoup(html, 'html.parser')

        # Extract title
        title_elem = soup.find('h1')
        title = title_elem.get_text(strip=True) if title_elem else doc_info.get('title', '')

        # Extract date
        date_elem = soup.find('time') or soup.find(class_=re.compile(r'date|posted'))
        date = date_elem.get_text(strip=True) if date_elem else ""

        # Determine position type from URL or content
        position_type = "short" if "/short/" in doc_info.get('archive', '') else "long"

        # Check for PDF link - Kerrisdale often has PDF reports
        pdf_link = soup.find('a', href=re.compile(r'\.pdf$', re.I))
        if pdf_link:
            pdf_url = pdf_link['href']
            if not pdf_url.startswith('http'):
                pdf_url = f"{self.BASE_URL}{pdf_url}"

            # Try to fetch and extract PDF
            pdf_content = self.fetch_pdf(pdf_url)
            if pdf_content:
                # Save PDF as raw
                raw_path = self.save_raw(pdf_content, doc_id, "pdf")

                # Try to extract text from PDF
                try:
                    import pdfplumber
                    import io

                    with pdfplumber.open(io.BytesIO(pdf_content)) as pdf:
                        description_text = ""
                        for page in pdf.pages:
                            text = page.extract_text()
                            if text:
                                description_text += text + "\n"
                except ImportError:
                    # Fallback to page content if pdfplumber not available
                    content_elem = soup.find('article') or soup.find(class_=re.compile(r'content|entry'))
                    description_text = content_elem.get_text(separator='\n', strip=True) if content_elem else ""
                    raw_path = self.save_raw(html, doc_id, "html")
            else:
                # PDF fetch failed, use page content
                content_elem = soup.find('article') or soup.find(class_=re.compile(r'content|entry'))
                description_text = content_elem.get_text(separator='\n', strip=True) if content_elem else ""
                raw_path = self.save_raw(html, doc_id, "html")
        else:
            # No PDF, extract from page
            content_elem = soup.find('article') or soup.find(class_=re.compile(r'content|entry'))
            if not content_elem:
                content_elem = soup.find('main') or soup.find('body')

            description_text = content_elem.get_text(separator='\n', strip=True) if content_elem else ""
            raw_path = self.save_raw(html, doc_id, "html")

        if not description_text or len(description_text) < 500:
            return None

        # Quick quality check
        if not quick_quality_check(description_text):
            return None

        # Full quality score
        quality = score_memo(description_text, quality_threshold=5.0)
        if not quality['passes_quality_bar']:
            print(f"            Quality score {quality['weighted_total']:.1f} < 5.0")
            return None

        # Extract ticker
        ticker_match = re.search(r'\(([A-Z]{1,5})\)', title) or re.search(r'([A-Z]{2,5})$', title)
        ticker = ticker_match.group(1) if ticker_match else None

        company_name = re.sub(r'\s*[\(\:].*$', '', title).strip()

        record = self.create_extracted_record(
            doc_id=doc_id,
            url=url,
            company_name=company_name,
            ticker=ticker,
            author="Kerrisdale Capital",
            date=date,
            position_type=position_type,
            description_text=description_text,
            quality_score=quality,
            raw_path=raw_path,
        )

        self.save_extracted(record, doc_id)
        return record


if __name__ == "__main__":
    scraper = KerrrisdaleSource(delay=2.0)
    scraper.run(max_docs=50)
