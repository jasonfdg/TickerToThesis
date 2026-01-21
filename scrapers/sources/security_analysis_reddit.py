"""
r/SecurityAnalysis Reddit Scraper
Community-sourced investment analysis and stock pitches.
Uses Reddit's old.reddit.com for easier parsing (no JavaScript required).
"""

import re
from typing import Dict, List, Optional
from bs4 import BeautifulSoup
from pathlib import Path
import json

PROJECT_ROOT = Path(__file__).parent.parent.parent
import sys
sys.path.insert(0, str(PROJECT_ROOT))

from scraper.sources.base_source import BaseSource
from scraper.quality_scorer import score_memo, quick_quality_check


class SecurityAnalysisRedditSource(BaseSource):
    """Scraper for r/SecurityAnalysis stock analyses."""

    SOURCE_NAME = "security_analysis_reddit"
    BASE_URL = "https://old.reddit.com/r/SecurityAnalysis"

    # Reddit API-style JSON endpoint
    JSON_URL = "https://www.reddit.com/r/SecurityAnalysis"

    def __init__(self, delay: float = 2.0, jitter: float = 1.0):
        super().__init__(delay, jitter)
        # Reddit requires specific User-Agent
        self.session.headers.update({
            "User-Agent": "BuysideResearchBot/1.0 (educational research)",
        })

    def discover_documents(self) -> List[Dict]:
        """Discover investment analyses from r/SecurityAnalysis."""
        documents = []

        # Fetch top posts (old reddit for stability)
        pages = [
            f"{self.BASE_URL}/top/?t=all",
            f"{self.BASE_URL}/top/?t=year",
            f"{self.BASE_URL}/new/",
        ]

        for page_url in pages:
            html = self.fetch_html(page_url)
            if not html:
                continue

            soup = BeautifulSoup(html, 'html.parser')

            # Find all post links
            for thing in soup.find_all('div', class_='thing'):
                # Get title and URL
                title_elem = thing.find('a', class_='title')
                if not title_elem:
                    continue

                title = title_elem.get_text(strip=True)
                href = title_elem.get('href', '')

                # Skip external links (not self posts or discussions)
                if 'reddit.com' not in href and href.startswith('http'):
                    # This links to external content - could be valuable
                    pass

                # Get the comments URL for self posts
                comments_link = thing.find('a', class_='comments')
                if comments_link:
                    comments_url = comments_link.get('href', '')
                    if comments_url.startswith('/'):
                        comments_url = f"https://old.reddit.com{comments_url}"

                    # Only include posts that look like analyses
                    title_lower = title.lower()
                    if any(x in title_lower for x in ['thesis', 'analysis', 'dd', 'pitch', 'valuation', 'research', 'long', 'short', 'buy', 'sell', 'undervalued']):
                        documents.append({
                            'url': comments_url,
                            'title': title,
                            'external_url': href if href.startswith('http') and 'reddit.com' not in href else None,
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
        """Extract content from a Reddit post."""
        url = doc_info['url']
        doc_id = self._generate_id(url)

        if self._is_already_extracted(doc_id):
            return None

        html = self.fetch_html(url)
        if not html:
            return None

        soup = BeautifulSoup(html, 'html.parser')
        raw_path = self.save_raw(html, doc_id, "html")

        # Find the self-text (main post content)
        selftext_elem = soup.find('div', class_='usertext-body')
        if not selftext_elem:
            # Try finding the expando
            expando = soup.find('div', class_='expando')
            if expando:
                selftext_elem = expando.find('div', class_='md')

        if not selftext_elem:
            # This might be a link post - check external_url
            external_url = doc_info.get('external_url')
            if external_url:
                # Try to fetch external content
                external_html = self.fetch_html(external_url)
                if external_html:
                    external_soup = BeautifulSoup(external_html, 'html.parser')
                    content_elem = external_soup.find('article') or external_soup.find(class_=re.compile(r'content|entry|post'))
                    if content_elem:
                        description_text = content_elem.get_text(separator='\n', strip=True)
                    else:
                        return None
                else:
                    return None
            else:
                return None
        else:
            description_text = selftext_elem.get_text(separator='\n', strip=True)

        if not description_text or len(description_text.split()) < 300:
            return None

        if not quick_quality_check(description_text):
            return None

        quality = score_memo(description_text, quality_threshold=5.0, min_word_count=300)
        if not quality['passes_quality_bar']:
            print(f"            Quality score {quality['weighted_total']:.1f} < 5.0")
            return None

        title = doc_info.get('title', '')

        # Extract ticker from title (common formats: $TICK, (TICK), TICK:)
        ticker_match = re.search(r'\$([A-Z]{1,5})\b', title) or re.search(r'\(([A-Z]{1,5})\)', title) or re.search(r'\b([A-Z]{2,5})[:|\s]', title)
        ticker = ticker_match.group(1) if ticker_match else None

        company_name = re.sub(r'\s*[\$\(\:].*$', '', title).strip() or "Reddit Analysis"

        # Determine position type from title
        title_lower = title.lower()
        if any(x in title_lower for x in ['short', 'sell', 'bearish', 'overvalued']):
            position_type = "short"
        else:
            position_type = "long"

        # Get author from page
        author_elem = soup.find('a', class_='author')
        reddit_author = author_elem.get_text(strip=True) if author_elem else "Anonymous"

        record = self.create_extracted_record(
            doc_id=doc_id,
            url=url,
            company_name=company_name,
            ticker=ticker,
            author=f"r/SecurityAnalysis ({reddit_author})",
            date="",
            position_type=position_type,
            description_text=description_text,
            quality_score=quality,
            raw_path=raw_path,
        )

        self.save_extracted(record, doc_id)
        return record


if __name__ == "__main__":
    scraper = SecurityAnalysisRedditSource(delay=3.0)
    scraper.run(max_docs=50)
