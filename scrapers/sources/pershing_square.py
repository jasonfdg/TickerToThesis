"""
Pershing Square Holdings Scraper
Bill Ackman's annual presentations and activist pitch PDFs.
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


class PershingSquareSource(BaseSource):
    """Scraper for Pershing Square Holdings presentations."""

    SOURCE_NAME = "pershing_square"
    BASE_URL = "https://pershingsquareholdings.com"
    ASSETS_URL = "https://assets.pershingsquareholdings.com"

    # Known high-quality presentations (direct PDF links)
    KNOWN_PRESENTATIONS = [
        {
            "url": "https://assets.pershingsquareholdings.com/2025/03/03171547/2025-Annual-Investor-Presentation_PSH_vDF.pdf",
            "title": "2025 Annual Investor Presentation",
            "date": "March 2025"
        },
        {
            "url": "https://assets.pershingsquareholdings.com/2024/02/12093015/2024-Annual-Investor-Presentation_PSH.pdf",
            "title": "2024 Annual Investor Presentation",
            "date": "February 2024"
        },
        {
            "url": "https://assets.pershingsquareholdings.com/2023/02/09104816/2023-Annual-Investor-Presentation.pdf",
            "title": "2023 Annual Investor Presentation",
            "date": "February 2023"
        },
        {
            "url": "https://assets.pershingsquareholdings.com/2022/02/10095033/Pershing-Square-2022-Annual-Investor-Presentation.pdf",
            "title": "2022 Annual Investor Presentation",
            "date": "February 2022"
        },
        {
            "url": "https://assets.pershingsquareholdings.com/2021/02/25085658/Pershing-Square-2021-Investor-Presentation.pdf",
            "title": "2021 Annual Investor Presentation",
            "date": "February 2021"
        },
        {
            "url": "https://assets.pershingsquareholdings.com/2020/02/27110739/Pershing-Square-2020-Investor-Presentation.pdf",
            "title": "2020 Annual Investor Presentation",
            "date": "February 2020"
        },
    ]

    def discover_documents(self) -> List[Dict]:
        """Return known Pershing Square presentations."""
        # Start with known presentations
        documents = list(self.KNOWN_PRESENTATIONS)

        # Try to discover more from the website
        try:
            html = self.fetch_html(self.BASE_URL)
            if html:
                soup = BeautifulSoup(html, 'html.parser')

                # Find PDF links
                for link in soup.find_all('a', href=re.compile(r'\.pdf$', re.I)):
                    href = link['href']
                    if not href.startswith('http'):
                        href = f"{self.ASSETS_URL}{href}"

                    title = link.get_text(strip=True) or "Pershing Square Report"

                    if href not in [d['url'] for d in documents]:
                        documents.append({
                            'url': href,
                            'title': title,
                            'date': ""
                        })
        except Exception as e:
            print(f"    Discovery error: {e}")

        return documents

    def extract_document(self, doc_info: Dict) -> Optional[Dict]:
        """Extract content from a Pershing Square PDF."""
        url = doc_info['url']
        doc_id = self._generate_id(url)

        if self._is_already_extracted(doc_id):
            return None

        # Fetch PDF
        pdf_content = self.fetch_pdf(url)
        if not pdf_content:
            return None

        # Save raw PDF
        raw_path = self.save_raw(pdf_content, doc_id, "pdf")

        # Extract text from PDF
        try:
            import pdfplumber

            description_text = ""
            with pdfplumber.open(io.BytesIO(pdf_content)) as pdf:
                for page in pdf.pages[:50]:  # Limit to first 50 pages
                    text = page.extract_text()
                    if text:
                        description_text += text + "\n"

        except ImportError:
            print("            pdfplumber not installed, skipping PDF extraction")
            return None
        except Exception as e:
            print(f"            PDF extraction error: {e}")
            return None

        if not description_text or len(description_text.split()) < 500:
            return None

        # Quality check
        if not quick_quality_check(description_text):
            return None

        quality = score_memo(description_text, quality_threshold=5.0, min_word_count=300)  # Lower threshold for presentations
        if not quality['passes_quality_bar']:
            print(f"            Quality score {quality['weighted_total']:.1f} < 5.0")
            return None

        title = doc_info.get('title', 'Pershing Square Presentation')
        date = doc_info.get('date', '')

        record = self.create_extracted_record(
            doc_id=doc_id,
            url=url,
            company_name="Pershing Square Holdings",
            ticker="PSH",
            author="Bill Ackman / Pershing Square",
            date=date,
            position_type="long",  # PSH is primarily long-biased
            description_text=description_text,
            quality_score=quality,
            raw_path=raw_path,
        )

        self.save_extracted(record, doc_id)
        return record


if __name__ == "__main__":
    scraper = PershingSquareSource(delay=3.0)
    scraper.run(max_docs=20)
