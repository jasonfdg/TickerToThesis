"""
10x EBITDA Scraper
Archive of activist investor presentations and fund decks.
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


class TenXEbitdaSource(BaseSource):
    """Scraper for 10x EBITDA activist shareholder letters."""

    SOURCE_NAME = "10xebitda"
    BASE_URL = "https://www.10xebitda.com"

    def discover_documents(self) -> List[Dict]:
        """Discover activist shareholder letters from 10x EBITDA."""
        documents = []

        # Main activist letters page
        letters_url = f"{self.BASE_URL}/activist-shareholder-letters/"
        html = self.fetch_html(letters_url)
        if not html:
            return documents

        soup = BeautifulSoup(html, 'html.parser')

        # Find all links to letters/presentations
        for link in soup.find_all('a', href=True):
            href = link['href']

            # Look for PDF links or letter pages
            if '.pdf' in href.lower() or '/letter/' in href or '/activist' in href:
                if href.startswith('/'):
                    url = f"{self.BASE_URL}{href}"
                elif href.startswith('http'):
                    url = href
                else:
                    continue

                title = link.get_text(strip=True)
                if not title or len(title) < 3:
                    # Try parent element
                    parent = link.find_parent(['li', 'div', 'article'])
                    if parent:
                        title = parent.get_text(strip=True)[:100]

                if title and len(title) >= 3:
                    documents.append({
                        'url': url,
                        'title': title,
                    })

        # Also check for embedded PDFs or document links
        for embed in soup.find_all(['embed', 'iframe', 'object']):
            src = embed.get('src') or embed.get('data')
            if src and '.pdf' in src.lower():
                if src.startswith('/'):
                    url = f"{self.BASE_URL}{src}"
                elif src.startswith('http'):
                    url = src
                else:
                    continue

                documents.append({
                    'url': url,
                    'title': f"Activist Presentation - {len(documents)+1}",
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
        """Extract content from a 10x EBITDA letter/presentation."""
        url = doc_info['url']
        doc_id = self._generate_id(url)

        if self._is_already_extracted(doc_id):
            return None

        # Check if it's a PDF
        if '.pdf' in url.lower():
            pdf_content = self.fetch_pdf(url)
            if not pdf_content:
                return None

            raw_path = self.save_raw(pdf_content, doc_id, "pdf")

            try:
                import pdfplumber

                description_text = ""
                with pdfplumber.open(io.BytesIO(pdf_content)) as pdf:
                    for page in pdf.pages[:30]:
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
            # HTML page
            html = self.fetch_html(url)
            if not html:
                return None

            soup = BeautifulSoup(html, 'html.parser')
            raw_path = self.save_raw(html, doc_id, "html")

            # Check for embedded PDF
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
                            for page in pdf.pages[:30]:
                                text = page.extract_text()
                                if text:
                                    description_text += text + "\n"

                    except Exception:
                        content_elem = soup.find('article') or soup.find(class_=re.compile(r'content|entry'))
                        description_text = content_elem.get_text(separator='\n', strip=True) if content_elem else ""
                else:
                    content_elem = soup.find('article') or soup.find(class_=re.compile(r'content|entry'))
                    description_text = content_elem.get_text(separator='\n', strip=True) if content_elem else ""
            else:
                content_elem = soup.find('article') or soup.find(class_=re.compile(r'content|entry'))
                description_text = content_elem.get_text(separator='\n', strip=True) if content_elem else ""

        if not description_text or len(description_text.split()) < 300:
            return None

        # Quality check
        if not quick_quality_check(description_text):
            return None

        quality = score_memo(description_text, quality_threshold=5.0, min_word_count=300)
        if not quality['passes_quality_bar']:
            print(f"            Quality score {quality['weighted_total']:.1f} < 5.0")
            return None

        title = doc_info.get('title', '')

        # Try to extract company/ticker from title
        ticker_match = re.search(r'\(([A-Z]{1,5})\)', title)
        ticker = ticker_match.group(1) if ticker_match else None
        company_name = re.sub(r'\s*[\(\:].*$', '', title).strip() or "Activist Letter"

        # Determine position type
        position_type = "long"  # Most activist letters are long-biased

        record = self.create_extracted_record(
            doc_id=doc_id,
            url=url,
            company_name=company_name,
            ticker=ticker,
            author="10x EBITDA Archive",
            date="",
            position_type=position_type,
            description_text=description_text,
            quality_score=quality,
            raw_path=raw_path,
        )

        self.save_extracted(record, doc_id)
        return record


if __name__ == "__main__":
    scraper = TenXEbitdaSource(delay=2.0)
    scraper.run(max_docs=50)
