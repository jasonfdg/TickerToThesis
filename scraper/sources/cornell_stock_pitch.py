"""
Cornell Stock Pitch Competition Scraper
Student stock pitches from Cornell's Parker Center and similar competitions.
Often high quality with rigorous analysis.
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


class CornellStockPitchSource(BaseSource):
    """Scraper for Cornell Stock Pitch Competition and similar university pitches."""

    SOURCE_NAME = "cornell_stock_pitch"
    BASE_URL = "https://www.johnson.cornell.edu"

    # Try multiple university sources for stock pitches
    UNIVERSITY_PITCH_SOURCES = [
        # Cornell Parker Center
        "https://www.johnson.cornell.edu/parker-center/stock-pitch/",
        "https://www.johnson.cornell.edu/parker-center/competitions/",
        # Other known pitch competition archives
        "https://www.stern.nyu.edu/experience-stern/about/departments-centers-initiatives/centers-of-research/salomon-center/student-resources/global-stock-pitch-competition",
        "https://www.wharton.upenn.edu/mba/finance/student-clubs-activities/wharton-investment-competition/",
    ]

    def discover_documents(self) -> List[Dict]:
        """Discover stock pitches from university competitions."""
        documents = []

        for source_url in self.UNIVERSITY_PITCH_SOURCES:
            html = self.fetch_html(source_url)
            if not html:
                continue

            soup = BeautifulSoup(html, 'html.parser')
            base = source_url.rsplit('/', 2)[0]  # Get base URL for relative links

            # Find pitch links
            for link in soup.find_all('a', href=True):
                href = link['href']

                # Look for pitch pages or PDFs
                if any(x in href.lower() for x in ['pitch', 'presentation', 'competition', '.pdf']):
                    if href.startswith('/'):
                        url = f"{base}{href}"
                    elif href.startswith('http'):
                        url = href
                    else:
                        continue

                    title = link.get_text(strip=True)
                    if not title or len(title) < 3:
                        parent = link.find_parent(['article', 'div', 'li', 'tr'])
                        if parent:
                            text = parent.get_text(strip=True)[:100]
                            title = text if len(text) >= 3 else None

                    if title and len(title) >= 3:
                        documents.append({
                            'url': url,
                            'title': title,
                            'source_base': base,
                        })

            # Also look for embedded PDFs or documents
            for embed in soup.find_all(['embed', 'iframe', 'object']):
                src = embed.get('src') or embed.get('data')
                if src and '.pdf' in src.lower():
                    if src.startswith('/'):
                        url = f"{base}{src}"
                    elif src.startswith('http'):
                        url = src
                    else:
                        continue

                    documents.append({
                        'url': url,
                        'title': f"Stock Pitch - {len(documents)+1}",
                        'source_base': base,
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
        """Extract content from a stock pitch document."""
        url = doc_info['url']
        doc_id = self._generate_id(url)
        source_base = doc_info.get('source_base', self.BASE_URL)

        if self._is_already_extracted(doc_id):
            return None

        if '.pdf' in url.lower():
            pdf_content = self.fetch_pdf(url)
            if not pdf_content:
                return None

            raw_path = self.save_raw(pdf_content, doc_id, "pdf")

            try:
                import pdfplumber

                description_text = ""
                with pdfplumber.open(io.BytesIO(pdf_content)) as pdf:
                    for page in pdf.pages[:40]:
                        text = page.extract_text()
                        if text:
                            description_text += text + "\n"

            except ImportError:
                print("            pdfplumber not installed")
                return None
            except Exception as e:
                print(f"            PDF error: {e}")
                return None
        else:
            html = self.fetch_html(url)
            if not html:
                return None

            soup = BeautifulSoup(html, 'html.parser')
            raw_path = self.save_raw(html, doc_id, "html")

            # Check for PDF link first
            pdf_link = soup.find('a', href=re.compile(r'\.pdf$', re.I))
            if pdf_link:
                pdf_href = pdf_link['href']
                if not pdf_href.startswith('http'):
                    pdf_href = f"{source_base}{pdf_href}"

                pdf_content = self.fetch_pdf(pdf_href)
                if pdf_content:
                    raw_path = self.save_raw(pdf_content, doc_id, "pdf")

                    try:
                        import pdfplumber

                        description_text = ""
                        with pdfplumber.open(io.BytesIO(pdf_content)) as pdf:
                            for page in pdf.pages[:40]:
                                text = page.extract_text()
                                if text:
                                    description_text += text + "\n"
                    except Exception:
                        description_text = ""

                    if not description_text or len(description_text.split()) < 300:
                        content_elem = soup.find('article') or soup.find(class_=re.compile(r'content|entry|main'))
                        description_text = content_elem.get_text(separator='\n', strip=True) if content_elem else ""
                else:
                    content_elem = soup.find('article') or soup.find(class_=re.compile(r'content|entry|main'))
                    description_text = content_elem.get_text(separator='\n', strip=True) if content_elem else ""
            else:
                content_elem = soup.find('article') or soup.find(class_=re.compile(r'content|entry|main'))
                if not content_elem:
                    content_elem = soup.find('main') or soup.find('body')
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

        # Extract ticker from title
        ticker_match = re.search(r'\(([A-Z]{1,5})\)', title) or re.search(r'([A-Z]{2,5})\s*[-\u2014:]', title)
        ticker = ticker_match.group(1) if ticker_match else None

        company_name = re.sub(r'\s*[\(\:].*$', '', title).strip() or "Stock Pitch"

        # Determine university source
        author = "University Stock Pitch Competition"
        if "cornell" in source_base.lower():
            author = "Cornell Stock Pitch Competition"
        elif "stern" in source_base.lower() or "nyu" in source_base.lower():
            author = "NYU Stern Stock Pitch Competition"
        elif "wharton" in source_base.lower():
            author = "Wharton Investment Competition"

        record = self.create_extracted_record(
            doc_id=doc_id,
            url=url,
            company_name=company_name,
            ticker=ticker,
            author=author,
            date="",
            position_type="long",
            description_text=description_text,
            quality_score=quality,
            raw_path=raw_path,
        )

        self.save_extracted(record, doc_id)
        return record


if __name__ == "__main__":
    scraper = CornellStockPitchSource(delay=3.0)
    scraper.run(max_docs=30)
