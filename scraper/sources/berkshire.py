"""
Berkshire Hathaway Shareholder Letters Scraper
60 years of Warren Buffett's letters - classic value investing wisdom.
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
from scraper.quality_scorer import score_memo


class BerkshireSource(BaseSource):
    """Scraper for Berkshire Hathaway shareholder letters."""

    SOURCE_NAME = "berkshire"
    BASE_URL = "https://www.berkshirehathaway.com"

    # Known letter URLs (they follow a consistent pattern)
    def discover_documents(self) -> List[Dict]:
        """Discover Berkshire shareholder letters."""
        documents = []

        # Fetch the letters index page
        letters_url = f"{self.BASE_URL}/letters/letters.html"
        html = self.fetch_html(letters_url)
        if not html:
            # Fall back to known URLs
            for year in range(2024, 1976, -1):
                documents.append({
                    'url': f"{self.BASE_URL}/letters/{year}ltr.pdf",
                    'title': f"Berkshire Hathaway {year} Annual Letter",
                    'year': str(year)
                })
            return documents

        soup = BeautifulSoup(html, 'html.parser')

        # Find all PDF links
        for link in soup.find_all('a', href=True):
            href = link['href']
            if '.pdf' in href.lower() or '.htm' in href.lower():
                if href.startswith('/'):
                    url = f"{self.BASE_URL}{href}"
                elif not href.startswith('http'):
                    url = f"{self.BASE_URL}/letters/{href}"
                else:
                    url = href

                # Extract year from URL or link text
                year_match = re.search(r'(19\d{2}|20\d{2})', href) or re.search(r'(19\d{2}|20\d{2})', link.get_text())
                year = year_match.group(1) if year_match else ""

                title = link.get_text(strip=True) or f"Berkshire Letter {year}"

                documents.append({
                    'url': url,
                    'title': title,
                    'year': year
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
        """Extract content from a Berkshire letter."""
        url = doc_info['url']
        doc_id = self._generate_id(url)

        if self._is_already_extracted(doc_id):
            return None

        description_text = ""

        if '.pdf' in url.lower():
            pdf_content = self.fetch_pdf(url)
            if not pdf_content:
                return None

            raw_path = self.save_raw(pdf_content, doc_id, "pdf")

            try:
                import pdfplumber

                with pdfplumber.open(io.BytesIO(pdf_content)) as pdf:
                    for page in pdf.pages:
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
            # HTML letter (older letters)
            html = self.fetch_html(url)
            if not html:
                return None

            soup = BeautifulSoup(html, 'html.parser')
            raw_path = self.save_raw(html, doc_id, "html")

            # Berkshire letters are typically plain HTML
            body = soup.find('body')
            if body:
                description_text = body.get_text(separator='\n', strip=True)

        if not description_text or len(description_text.split()) < 1000:
            return None

        # Buffett letters are philosophical - adjust scoring
        # They may not have explicit buy/sell recommendations
        quality = score_memo(description_text, quality_threshold=5.0, min_word_count=500)

        # Berkshire letters are always high quality - override if reasonable length
        word_count = len(description_text.split())
        if word_count > 2000:
            quality['weighted_total'] = max(quality['weighted_total'], 6.5)
            quality['passes_quality_bar'] = True

        if not quality['passes_quality_bar']:
            print(f"            Quality score {quality['weighted_total']:.1f} < 5.0")
            return None

        year = doc_info.get('year', '')
        title = doc_info.get('title', f'Berkshire Hathaway Letter {year}')

        record = self.create_extracted_record(
            doc_id=doc_id,
            url=url,
            company_name="Berkshire Hathaway",
            ticker="BRK.A",
            author="Warren Buffett",
            date=f"{year}" if year else "",
            position_type="long",
            description_text=description_text,
            quality_score=quality,
            raw_path=raw_path,
        )

        self.save_extracted(record, doc_id)
        return record


if __name__ == "__main__":
    scraper = BerkshireSource(delay=2.0)
    scraper.run(max_docs=50)
