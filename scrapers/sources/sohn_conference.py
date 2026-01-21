"""
Sohn Investment Conference Scraper
Premier annual investment conference with stock pitches from top fund managers.
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


class SohnConferenceSource(BaseSource):
    """Scraper for Sohn Conference investment pitches."""

    SOURCE_NAME = "sohn_conference"
    BASE_URL = "https://www.sohnconference.org"

    # Known presentation archives (many conferences make decks available)
    KNOWN_PRESENTATIONS = [
        # Historical presentations often available via archive sites
        # Sohn conference presentations are frequently shared
    ]

    def discover_documents(self) -> List[Dict]:
        """Discover Sohn Conference pitches and presentations."""
        documents = []

        # Try main site
        pages_to_check = [
            self.BASE_URL,
            f"{self.BASE_URL}/conferences/",
            f"{self.BASE_URL}/presentations/",
            f"{self.BASE_URL}/ideas/",
            f"{self.BASE_URL}/past-conferences/",
        ]

        for page_url in pages_to_check:
            html = self.fetch_html(page_url)
            if not html:
                continue

            soup = BeautifulSoup(html, 'html.parser')

            # Find presentation/pitch links
            for link in soup.find_all('a', href=True):
                href = link['href']

                # Look for presentation pages or PDFs
                if any(x in href.lower() for x in ['/presentation', '/pitch', '/idea', '/speaker', '.pdf']):
                    if href.startswith('/'):
                        url = f"{self.BASE_URL}{href}"
                    elif href.startswith('http'):
                        url = href
                    else:
                        continue

                    title = link.get_text(strip=True)
                    if not title or len(title) < 3:
                        parent = link.find_parent(['article', 'div', 'li', 'section'])
                        if parent:
                            h = parent.find(['h1', 'h2', 'h3', 'h4', 'h5'])
                            if h:
                                title = h.get_text(strip=True)

                    if title and len(title) >= 3:
                        documents.append({
                            'url': url,
                            'title': title,
                        })

        # Also check for embedded YouTube videos with pitch descriptions
        for page_url in pages_to_check[:2]:
            html = self.fetch_html(page_url)
            if not html:
                continue

            soup = BeautifulSoup(html, 'html.parser')

            # Find video sections that might have pitch transcripts
            for article in soup.find_all(['article', 'section', 'div'], class_=re.compile(r'pitch|idea|presentation')):
                title_elem = article.find(['h1', 'h2', 'h3', 'h4'])
                if title_elem:
                    title = title_elem.get_text(strip=True)

                    # Get link within article
                    link = article.find('a', href=True)
                    if link:
                        href = link['href']
                        if href.startswith('/'):
                            url = f"{self.BASE_URL}{href}"
                        else:
                            url = href

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
        """Extract content from a Sohn Conference presentation."""
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
                    for page in pdf.pages[:50]:
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
                        description_text = ""

                    if not description_text or len(description_text.split()) < 300:
                        content_elem = soup.find('article') or soup.find(class_=re.compile(r'content|entry|presentation'))
                        description_text = content_elem.get_text(separator='\n', strip=True) if content_elem else ""
                else:
                    content_elem = soup.find('article') or soup.find(class_=re.compile(r'content|entry|presentation'))
                    description_text = content_elem.get_text(separator='\n', strip=True) if content_elem else ""
            else:
                content_elem = soup.find('article') or soup.find(class_=re.compile(r'content|entry|presentation'))
                if not content_elem:
                    content_elem = soup.find('main') or soup.find('body')
                description_text = content_elem.get_text(separator='\n', strip=True) if content_elem else ""

        if not description_text or len(description_text.split()) < 300:
            return None

        if not quick_quality_check(description_text):
            return None

        quality = score_memo(description_text, quality_threshold=5.0, min_word_count=300)
        if not quality['passes_quality_bar']:
            print(f"            Quality score {quality['weighted_total']:.1f} < 5.0")
            return None

        title = doc_info.get('title', '')

        # Extract ticker and company from title
        ticker_match = re.search(r'\(([A-Z]{1,5})\)', title) or re.search(r':?\s*([A-Z]{2,5})$', title)
        ticker = ticker_match.group(1) if ticker_match else None

        company_name = re.sub(r'\s*[\(\:].*$', '', title).strip() or "Sohn Conference Pitch"

        # Extract presenter name if present
        author_match = re.search(r'([\w\s]+)\s*[-\u2014:]\s*', title)
        author = author_match.group(1).strip() if author_match else "Sohn Conference Presenter"

        record = self.create_extracted_record(
            doc_id=doc_id,
            url=url,
            company_name=company_name,
            ticker=ticker,
            author=author,
            date="",
            position_type="long",  # Most Sohn pitches are longs
            description_text=description_text,
            quality_score=quality,
            raw_path=raw_path,
        )

        self.save_extracted(record, doc_id)
        return record


if __name__ == "__main__":
    scraper = SohnConferenceSource(delay=3.0)
    scraper.run(max_docs=30)
