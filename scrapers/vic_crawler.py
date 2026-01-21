"""
VIC Crawler Module
Discovers and indexes all investment ideas from Value Investors Club.
"""

import json
import re
import time
from pathlib import Path
from datetime import datetime
from tqdm import tqdm

from scraper.vic_auth import VICSession

# Project paths
PROJECT_ROOT = Path(__file__).parent.parent
INDEX_FILE = PROJECT_ROOT / "data" / "reports_index.json"
BASE_URL = "https://www.valueinvestorsclub.com"


def extract_idea_data(page, link_element) -> dict:
    """
    Extract metadata from an idea card/link element.
    """
    href = link_element.get_attribute("href")

    # Parse company name and ID from URL
    # Format: /idea/Company_Name/1234567890
    match = re.match(r"/idea/([^/]+)/(\d+)", href)
    if not match:
        return None

    company_slug, idea_id = match.groups()
    company_name = company_slug.replace("_", " ").replace("andamp%3B", "&")

    # Try to get the ticker from nearby elements
    ticker = None
    title = link_element.get_attribute("title")
    if title:
        company_name = title

    # Look for ticker in the link text (often just the ticker)
    link_text = link_element.inner_text().strip()
    if link_text.isupper() and len(link_text) <= 6:
        ticker = link_text

    return {
        "id": idea_id,
        "url": f"{BASE_URL}{href}",
        "company_name": company_name,
        "ticker": ticker,
        "company_slug": company_slug,
    }


def extract_idea_cards(page) -> list:
    """
    Extract all idea cards from the current page view.
    Returns list of idea metadata dicts.
    """
    ideas = []
    seen_ids = set()

    # Find all "Read more" links which lead to full ideas
    read_more_links = page.query_selector_all("a:has-text('Read more')")

    for link in read_more_links:
        href = link.get_attribute("href")
        if not href or "/idea/" not in href:
            continue

        # Parse URL
        match = re.match(r"/idea/([^/]+)/(\d+)", href)
        if not match:
            continue

        company_slug, idea_id = match.groups()

        if idea_id in seen_ids:
            continue
        seen_ids.add(idea_id)

        # Get parent container to extract more info
        # Navigate up to find the card container
        parent_text = ""
        try:
            parent = link.evaluate("""el => {
                let p = el.parentElement;
                for (let i = 0; i < 5; i++) {
                    if (p && p.innerText && p.innerText.length > 100) {
                        return p.innerText;
                    }
                    p = p?.parentElement;
                }
                return '';
            }""")
            parent_text = parent or ""
        except:
            pass

        # Extract date from parent text
        date_match = re.search(r"(\d{1,2}/\d{1,2}/\d{4})", parent_text)
        date_str = date_match.group(1) if date_match else None

        # Extract ticker - usually in bold/uppercase at start
        ticker_match = re.search(r"\b([A-Z]{1,5})\b", parent_text[:50])
        ticker = ticker_match.group(1) if ticker_match else None

        # Extract price and market cap if present
        price_match = re.search(r"Price:\s*\$?([\d,.]+)", parent_text)
        mcap_match = re.search(r"Market Cap.*?:\s*\$?([\d,.]+)", parent_text)

        company_name = company_slug.replace("_", " ").replace("andamp%3B", "&")

        idea = {
            "id": idea_id,
            "url": f"{BASE_URL}{href}",
            "company_name": company_name,
            "company_slug": company_slug,
            "ticker": ticker,
            "date": date_str,
            "price": price_match.group(1) if price_match else None,
            "market_cap": mcap_match.group(1) if mcap_match else None,
            "snippet": parent_text[:300] if parent_text else None,
        }
        ideas.append(idea)

    return ideas


def click_load_more(page) -> bool:
    """
    Click the 'Load More Ideas' button if present.
    Returns True if button was clicked, False if not found.
    """
    try:
        load_more = page.query_selector("a:has-text('LOAD MORE IDEAS'), a:has-text('Load More')")
        if load_more and load_more.is_visible():
            load_more.click()
            page.wait_for_timeout(2000)  # Wait for content to load
            return True
    except Exception as e:
        print(f"Load more error: {e}")
    return False


def sort_by_highest_rated(page) -> bool:
    """
    Click the 'Highest Rated' sort option.
    Returns True if successful.
    """
    try:
        # Look for the highest rated link
        sort_link = page.query_selector("a:has-text('Highest Rated')")
        if sort_link:
            sort_link.click()
            page.wait_for_timeout(2000)
            return True
    except Exception as e:
        print(f"Sort error: {e}")
    return False


def crawl_ideas(max_ideas: int = 500, sort_by: str = "highest_rated") -> list:
    """
    Crawl all ideas from VIC.

    Args:
        max_ideas: Maximum number of ideas to collect
        sort_by: Sort method - "highest_rated", "most_recent", "most_active"

    Returns:
        List of idea metadata dicts
    """
    all_ideas = []
    seen_ids = set()

    with VICSession(headless=True) as (browser, page):
        print("Navigating to ideas page...")
        page.goto(f"{BASE_URL}/ideas", wait_until="domcontentloaded", timeout=60000)
        page.wait_for_timeout(3000)

        # Apply sorting
        if sort_by == "highest_rated":
            print("Sorting by highest rated...")
            sort_by_highest_rated(page)

        page_num = 1
        consecutive_empty = 0

        while len(all_ideas) < max_ideas:
            print(f"\n=== Page {page_num} ===")

            # Extract ideas from current view
            ideas = extract_idea_cards(page)

            # Filter duplicates
            new_ideas = []
            for idea in ideas:
                if idea["id"] not in seen_ids:
                    seen_ids.add(idea["id"])
                    new_ideas.append(idea)

            if new_ideas:
                all_ideas.extend(new_ideas)
                print(f"Found {len(new_ideas)} new ideas (total: {len(all_ideas)})")
                consecutive_empty = 0
            else:
                consecutive_empty += 1
                print(f"No new ideas found (consecutive empty: {consecutive_empty})")

            # Stop if we've hit empty pages multiple times
            if consecutive_empty >= 3:
                print("Stopping - no more new ideas")
                break

            # Try to load more
            if not click_load_more(page):
                print("No more 'Load More' button - reached end")
                break

            page_num += 1

            # Progress update
            if len(all_ideas) >= max_ideas:
                print(f"Reached target of {max_ideas} ideas")
                break

    return all_ideas


def save_index(ideas: list) -> None:
    """Save ideas index to JSON file."""
    INDEX_FILE.parent.mkdir(parents=True, exist_ok=True)

    index_data = {
        "crawl_date": datetime.now().isoformat(),
        "total_ideas": len(ideas),
        "ideas": ideas
    }

    with open(INDEX_FILE, "w") as f:
        json.dump(index_data, f, indent=2)

    print(f"Saved {len(ideas)} ideas to {INDEX_FILE}")


def load_index() -> list:
    """Load ideas index from JSON file."""
    if INDEX_FILE.exists():
        with open(INDEX_FILE, "r") as f:
            data = json.load(f)
        return data.get("ideas", [])
    return []


def main():
    """Main crawl function."""
    print("Starting VIC idea crawl...")
    print("=" * 50)

    # Crawl ideas sorted by highest rated
    ideas = crawl_ideas(max_ideas=300, sort_by="highest_rated")

    # Save index
    save_index(ideas)

    print("\n" + "=" * 50)
    print(f"Crawl complete! Found {len(ideas)} ideas")
    print(f"Index saved to: {INDEX_FILE}")


if __name__ == "__main__":
    main()
