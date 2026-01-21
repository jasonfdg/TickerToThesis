"""
Hedge Fund Alpha Scraper
Institutional level hedge fund data and investor letters.
"""

import re
from typing import Dict, List, Optional
from bs4 import BeautifulSoup
from pathlib import Path
import io

PROJECT_ROOT = Path(__file__).parent.parent.parent
import sys
sys.path.insert(0, str(PROJECT_ROOT))

from scraper.sources.base_source import BaseSource
from scraper.quality_scorer import score_memo, quick_quality_check


class HedgeFundAlphaSource(BaseSource):
    """Scraper for Hedge Fund Alpha investor letters."""

    SOURCE_NAME = "hedge_fund_alpha"
    BASE_URL = "https://hedgefundalpha.com"

    def discover_documents(self) -> List[Dict]:
        """Discover investor letters from Hedge Fund Alpha."""
        documents = []

        # Investor letters page
        letters_urls = [
            f"{self.BASE_URL}/investor-letters/",
            f"{self.BASE_URL}/letters/",
            f"{self.BASE_URL}/conferences/",
        ]

        for letters_url in letters_urls:
            html = self.fetch_html(letters_url)
            if not html:
                continue

            soup = BeautifulSoup(html, 'html.parser')

            # Find all article/letter links
            for link in soup.find_all('a', href=True):
                href = link['href']

                if '/letter' in href or '/conference' in href or '/pitches' in href:
                    if href.startswith('/'):
                        url = f"{self.BASE_URL}{href}"
                    elif href.startswith('http'):
                        url = href
                    else:
                        continue

                    title = link.get_text(strip=True)
                    if title and len(title) >= 5:
                        documents.append({
                            'url': url,
                            'title': title,
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
        """Extract content from a Hedge Fund Alpha page."""
        url = doc_info['url']
        doc_id = self._generate_id(url)

        if self._is_already_extracted(doc_id):
            return None

        html = self.fetch_html(url)
        if not html:
            return None

        soup = BeautifulSoup(html, 'html.parser')
        raw_path = self.save_raw(html, doc_id, "html")

        # Try to find PDF link
        pdf_link = soup.find('a', href=re.compile(r'\.pdf$', re.I))
        if pdf_link:
            pdf_href = pdf_link['href']
            if not pdf_href.startswith('http'):
                pdf_href = f"{self.BASE_URL}{pdf_href}"

            pdf_content = self.fetch_pdf(pdf_href)
            if pdf_content:
                raw_path = self.save_raw(pdf_content, doc_id, "pdf")

                try:
                    import pdfplumber

                    description_text = ""
                    with pdfplumber.open(io.BytesIO(pdf_content)) as pdf:
                        for page in pdf.pages[:50]:
                            text = page.extract_text()
                            if text:
                                description_text += text + "\n"
                except Exception:
                    pass

                if description_text and len(description_text.split()) >= 500:
                    pass  # Use PDF content
                else:
                    # Fall back to page content
                    content_elem = soup.find('article') or soup.find(class_=re.compile(r'content|entry|post'))
                    description_text = content_elem.get_text(separator='\n', strip=True) if content_elem else ""
            else:
                content_elem = soup.find('article') or soup.find(class_=re.compile(r'content|entry|post'))
                description_text = content_elem.get_text(separator='\n', strip=True) if content_elem else ""
        else:
            content_elem = soup.find('article') or soup.find(class_=re.compile(r'content|entry|post'))
            description_text = content_elem.get_text(separator='\n', strip=True) if content_elem else ""

        if not description_text or len(description_text.split()) < 400:
            return None

        if not quick_quality_check(description_text):
            return None

        quality = score_memo(description_text, quality_threshold=5.0, min_word_count=400)
        if not quality['passes_quality_bar']:
            print(f"            Quality score {quality['weighted_total']:.1f} < 5.0")
            return None

        title = doc_info.get('title', '')

        # Extract date from title if present
        date_match = re.search(r'(Q[1-4]\s*20\d{2}|20\d{2})', title)
        date = date_match.group(1) if date_match else ""

        record = self.create_extracted_record(
            doc_id=doc_id,
            url=url,
            company_name=title or "Hedge Fund Letter",
            ticker=None,
            author="Hedge Fund Alpha",
            date=date,
            position_type="long",
            description_text=description_text,
            quality_score=quality,
            raw_path=raw_path,
        )

        self.save_extracted(record, doc_id)
        return record


if __name__ == "__main__":
    scraper = HedgeFundAlphaSource(delay=2.0)
    scraper.run(max_docs=50)
