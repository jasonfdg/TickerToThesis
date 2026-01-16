"""
Carl Icahn Letters Scraper
Activist investor letters - direct from carlicahn.com
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


class IcahnSource(BaseSource):
    """Scraper for Carl Icahn's activist letters."""

    SOURCE_NAME = "icahn"
    BASE_URL = "https://carlicahn.com"

    def discover_documents(self) -> List[Dict]:
        """Discover Carl Icahn letters."""
        documents = []

        # Letters page
        letters_url = f"{self.BASE_URL}/letters/"
        html = self.fetch_html(letters_url)
        if not html:
            return documents

        soup = BeautifulSoup(html, 'html.parser')

        # Find all letter links
        for link in soup.find_all('a', href=True):
            href = link['href']

            # Look for letter pages or PDFs
            if '/letter/' in href or '.pdf' in href.lower():
                if href.startswith('/'):
                    url = f"{self.BASE_URL}{href}"
                elif href.startswith('http'):
                    url = href
                else:
                    url = f"{self.BASE_URL}/letters/{href}"

                title = link.get_text(strip=True)
                if not title or len(title) < 3:
                    parent = link.find_parent(['article', 'div', 'li'])
                    if parent:
                        h = parent.find(['h1', 'h2', 'h3', 'h4'])
                        if h:
                            title = h.get_text(strip=True)

                if title and len(title) >= 3:
                    documents.append({
                        'url': url,
                        'title': title,
                    })

        # Also try the main page
        main_html = self.fetch_html(self.BASE_URL)
        if main_html:
            main_soup = BeautifulSoup(main_html, 'html.parser')
            for link in main_soup.find_all('a', href=True):
                href = link['href']
                if '/letter/' in href:
                    if href.startswith('/'):
                        url = f"{self.BASE_URL}{href}"
                    elif href.startswith('http'):
                        url = href
                    else:
                        continue

                    title = link.get_text(strip=True) or "Icahn Letter"
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
        """Extract content from an Icahn letter."""
        url = doc_info['url']
        doc_id = self._generate_id(url)

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
                    for page in pdf.pages:
                        text = page.extract_text()
                        if text:
                            description_text += text + "\n"

            except ImportError:
                return None
            except Exception:
                return None
        else:
            html = self.fetch_html(url)
            if not html:
                return None

            soup = BeautifulSoup(html, 'html.parser')
            raw_path = self.save_raw(html, doc_id, "html")

            # Check for PDF link
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
                            for page in pdf.pages:
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

        if not quick_quality_check(description_text):
            return None

        quality = score_memo(description_text, quality_threshold=5.0, min_word_count=300)

        # Icahn letters are high quality - boost if reasonable
        if len(description_text.split()) > 1000:
            quality['weighted_total'] = max(quality['weighted_total'], 6.0)
            quality['passes_quality_bar'] = True

        if not quality['passes_quality_bar']:
            print(f"            Quality score {quality['weighted_total']:.1f} < 5.0")
            return None

        title = doc_info.get('title', '')

        # Extract company/ticker from title
        ticker_match = re.search(r'\(([A-Z]{1,5})\)', title)
        ticker = ticker_match.group(1) if ticker_match else None
        company_name = re.sub(r'\s*[\(\:].*$', '', title).strip() or "Icahn Target Company"

        record = self.create_extracted_record(
            doc_id=doc_id,
            url=url,
            company_name=company_name,
            ticker=ticker,
            author="Carl Icahn",
            date="",
            position_type="long",
            description_text=description_text,
            quality_score=quality,
            raw_path=raw_path,
        )

        self.save_extracted(record, doc_id)
        return record


if __name__ == "__main__":
    scraper = IcahnSource(delay=2.0)
    scraper.run(max_docs=30)
