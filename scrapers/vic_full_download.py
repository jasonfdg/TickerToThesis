"""
VIC Full Database Downloader
Downloads the entire VIC database using Year x Alphabet matrix discovery.
Extracts full content including ratings, comments, and description text.
"""

import json
import re
import sys
import time
from pathlib import Path
from datetime import datetime
from playwright.sync_api import sync_playwright

# Project paths
PROJECT_ROOT = Path(__file__).parent.parent
RAW_DIR = PROJECT_ROOT / "data" / "vic" / "raw"
STRUCTURED_DIR = PROJECT_ROOT / "data" / "vic" / "structured"
FULL_INDEX_FILE = PROJECT_ROOT / "data" / "vic" / "index" / "full_index.json"
WINNERS_INDEX_FILE = PROJECT_ROOT / "data" / "vic" / "index" / "winners_index.json"
COOKIES_FILE = PROJECT_ROOT / "cookies.json"  # Root cookies file

RAW_DIR.mkdir(parents=True, exist_ok=True)
STRUCTURED_DIR.mkdir(parents=True, exist_ok=True)

BASE_URL = "https://www.valueinvestorsclub.com"

# Discovery configuration
LETTER_GROUPS = ['0-9', 'A-C', 'D-F', 'G-J', 'K-N', 'O-R', 'S-V', 'W-Z']
YEARS = [str(y) for y in range(2000, 2027)]  # 2000-2026


def print_status(message: str):
    """Print status message with timestamp."""
    timestamp = datetime.now().strftime("%H:%M:%S")
    print(f"[{timestamp}] {message}")


def print_progress_bar(current: int, total: int, prefix: str = "Progress", width: int = 40):
    """Print a progress bar."""
    if total == 0:
        return
    filled = int(width * current / total)
    bar = "█" * filled + "░" * (width - filled)
    percent = current / total * 100
    sys.stdout.write(f"\r{prefix}: [{bar}] {current:,}/{total:,} ({percent:.1f}%)")
    sys.stdout.flush()


def load_cookies() -> list:
    """Load cookies from root cookies.json file."""
    if COOKIES_FILE.exists():
        with open(COOKIES_FILE, "r") as f:
            return json.load(f)
    return []


def verify_authentication(page) -> bool:
    """Verify that we're logged in."""
    page.goto(f"{BASE_URL}/ideas", wait_until="domcontentloaded", timeout=60000)
    page.wait_for_timeout(3000)
    content = page.content()

    if "Logout" in content:
        print_status("✓ Authentication verified - logged in")
        return True
    else:
        print_status("✗ WARNING: Not authenticated - cookies may be expired")
        return False


def discover_ideas_year_alphabet(page) -> list:
    """
    Discover all ideas using Year × Alphabet matrix.
    Iterates through each letter group and year combination.
    """
    print_status("Starting Year × Alphabet discovery...")
    print("=" * 70)

    all_ideas = []
    seen_ids = set()

    total_combinations = len(LETTER_GROUPS) * len(YEARS)
    current_combo = 0

    for group_idx, group in enumerate(LETTER_GROUPS):
        print_status(f"\n📁 Letter Group: {group} ({group_idx + 1}/{len(LETTER_GROUPS)})")

        # Navigate to letter group page
        url = f"{BASE_URL}/ideas/atoz/{group}/last10"
        try:
            page.goto(url, wait_until="domcontentloaded", timeout=60000)
            page.wait_for_timeout(3000)
        except Exception as e:
            print_status(f"  ✗ Failed to load {group}: {e}")
            continue

        for year_idx, year in enumerate(YEARS):
            current_combo += 1

            try:
                # Click the "Show:" dropdown
                dropdown = page.query_selector('button.dropdown-toggle:has-text("Show:")')
                if dropdown:
                    dropdown.click()
                    page.wait_for_timeout(1500)

                    # Click the year option
                    year_link = page.query_selector(f'a:text-is("{year}")')
                    if year_link:
                        year_link.click()
                        page.wait_for_timeout(4000)  # Wait for content to load
                    else:
                        # Year not available, skip
                        continue
                else:
                    continue

                # Extract ideas from page
                links = page.query_selector_all("a[href*='/idea/']")
                new_in_this_batch = 0

                for link in links:
                    href = link.get_attribute("href")
                    if not href or "/idea/" not in href:
                        continue

                    match = re.match(r"/idea/([^/]+)/(\d+)", href)
                    if not match:
                        continue

                    company_slug, idea_id = match.groups()

                    if idea_id in seen_ids:
                        continue

                    seen_ids.add(idea_id)
                    new_in_this_batch += 1

                    # Get metadata from parent element
                    parent_text = ""
                    try:
                        parent_text = link.evaluate("""el => {
                            let p = el.parentElement;
                            for (let i = 0; i < 5; i++) {
                                if (p && p.innerText && p.innerText.length > 50) {
                                    return p.innerText.substring(0, 500);
                                }
                                p = p?.parentElement;
                            }
                            return '';
                        }""") or ""
                    except:
                        pass

                    # Extract date and ticker
                    date_match = re.search(r"(\d{1,2}/\d{1,2}/\d{2,4})", parent_text)
                    ticker_match = re.search(r"\b([A-Z]{1,5})\b", parent_text[:50])

                    idea = {
                        "id": idea_id,
                        "url": f"{BASE_URL}{href}",
                        "company_name": company_slug.replace("_", " "),
                        "company_slug": company_slug,
                        "ticker": ticker_match.group(1) if ticker_match else None,
                        "date": date_match.group(1) if date_match else None,
                        "discovered_in": f"{group}/{year}"
                    }
                    all_ideas.append(idea)

                # Progress update
                print_progress_bar(current_combo, total_combinations,
                                   f"  {group}/{year}: +{new_in_this_batch} ideas | Total: {len(all_ideas):,}")

            except Exception as e:
                # Silent skip for missing years
                pass

        print()  # New line after each letter group

    print("\n" + "=" * 70)
    print_status(f"Discovery complete! Found {len(all_ideas):,} unique ideas")

    return all_ideas


def extract_full_content(page, idea: dict) -> dict:
    """
    Extract complete content from an idea page including:
    - Author, date, position type
    - Financial data (price, EPS, P/E, market cap)
    - Quality and performance ratings with vote breakdowns
    - Full description text
    - All comments with full content
    """
    result = {
        "id": idea["id"],
        "url": idea["url"],
        "company_name": idea.get("company_name", ""),
        "ticker": idea.get("ticker"),
        "extracted_at": datetime.now().isoformat()
    }

    try:
        # Use networkidle to wait for all resources to load
        page.goto(idea["url"], wait_until="networkidle", timeout=60000)

        # Wait for critical content elements
        content_loaded = False
        try:
            page.wait_for_selector('#description', timeout=15000)
            content_loaded = True
        except:
            try:
                page.wait_for_selector('.idea_by, .idea_name', timeout=10000)
                content_loaded = True
            except:
                pass

        # Additional wait to ensure JS rendering completes
        if content_loaded:
            page.wait_for_timeout(4000)
        else:
            page.wait_for_timeout(8000)

        # Save raw HTML
        html_content = page.content()
        raw_path = RAW_DIR / f"{idea['id']}.html"
        with open(raw_path, "w", encoding="utf-8") as f:
            f.write(html_content)
        result["raw_html_path"] = str(raw_path)

        # Extract structured data via JavaScript - FIXED for VIC HTML structure
        data = page.evaluate('''() => {
            const result = {};

            // Ticker - extract from the gray span in the title area
            // Pattern: "Company Name <span style="color:#ccc;">TICKER</span>"
            const titleSpan = document.querySelector('.idea_name span[style*="color:#ccc"], .vich1 span[style*="color:#ccc"]');
            if (titleSpan) {
                result.ticker = titleSpan.innerText.trim();
            }

            // Author - from the idea_by section: "by <a>username</a>"
            const authorLink = document.querySelector('.idea_by a.display_name, .idea_by a[href*="/member/"]');
            if (authorLink) {
                result.author = authorLink.innerText.trim();
            }

            // Date - from idea_by section
            const ideaByDiv = document.querySelector('.idea_by');
            if (ideaByDiv) {
                const dateMatch = ideaByDiv.innerText.match(/([A-Z][a-z]+ \\d{1,2}, \\d{4})/);
                if (dateMatch) result.date = dateMatch[1];
            }

            // Position type - check for "short" label
            const positionLabel = document.querySelector('.label-short, [class*="short"]');
            if (positionLabel && positionLabel.innerText.toLowerCase().includes('short')) {
                result.position_type = 'short';
            } else {
                result.position_type = 'long';
            }

            // Financial data from the info table
            const tables = document.querySelectorAll('table');
            for (const table of tables) {
                const rows = table.querySelectorAll('tr');
                for (const row of rows) {
                    const text = row.innerText;

                    // Price
                    if (text.includes('Price:')) {
                        const cells = row.querySelectorAll('td');
                        for (let i = 0; i < cells.length; i++) {
                            if (cells[i].innerText.includes('Price:') && cells[i+2]) {
                                const val = cells[i+2].innerText.trim();
                                if (val && !isNaN(parseFloat(val))) result.price = val;
                            }
                        }
                    }

                    // Market Cap
                    if (text.includes('Market Cap')) {
                        const cells = row.querySelectorAll('td');
                        for (let i = 0; i < cells.length; i++) {
                            if (cells[i].innerText.includes('Market Cap') && cells[i+2]) {
                                const val = cells[i+2].innerText.trim();
                                if (val && val !== '0') result.market_cap = val;
                            }
                        }
                    }

                    // Shares Out
                    if (text.includes('Shares Out')) {
                        const cells = row.querySelectorAll('td');
                        for (let i = 0; i < cells.length; i++) {
                            if (cells[i].innerText.includes('Shares Out') && cells[i+2]) {
                                const val = cells[i+2].innerText.trim();
                                if (val && val !== '0') result.shares_out = val;
                            }
                        }
                    }

                    // Net Debt
                    if (text.includes('Net Debt')) {
                        const cells = row.querySelectorAll('td');
                        for (let i = 0; i < cells.length; i++) {
                            if (cells[i].innerText.includes('Net Debt') && cells[i+2]) {
                                const val = cells[i+2].innerText.trim();
                                if (val && val !== '0') result.net_debt = val;
                            }
                        }
                    }

                    // TEV
                    if (text.includes('TEV') && !text.includes('TEV/')) {
                        const cells = row.querySelectorAll('td');
                        for (let i = 0; i < cells.length; i++) {
                            if (cells[i].innerText.match(/^TEV/) && cells[i+2]) {
                                const val = cells[i+2].innerText.trim();
                                if (val && val !== '0') result.tev = val;
                            }
                        }
                    }
                }
            }

            return result;
        }''')

        result.update(data)

        # Extract ratings - FIXED: Use data-rateit-value attribute and vote breakdown div
        ratings = page.evaluate('''() => {
            const result = {quality: {}, performance: {}};

            // Quality rating - from #ratings_q span
            const qualityRateit = document.querySelector('#ratings_q[data-rateit-value]');
            if (qualityRateit) {
                const score = parseFloat(qualityRateit.getAttribute('data-rateit-value'));
                if (!isNaN(score)) {
                    result.quality.score = score;
                }
            }

            // Quality votes - look for "(X votes)" text near ratings
            const qualitySection = document.querySelector('.col-xs-12.col-sm-3');
            if (qualitySection) {
                const votesMatch = qualitySection.innerText.match(/(\\d+) votes?\\)/);
                if (votesMatch) {
                    result.quality.votes = parseInt(votesMatch[1]);
                }
            }

            // Quality breakdown - from #votes_q_breakdown table
            const qualityBreakdown = document.querySelector('#votes_q_breakdown');
            if (qualityBreakdown) {
                const breakdown = {};
                const rows = qualityBreakdown.querySelectorAll('tr');
                for (const row of rows) {
                    const text = row.innerText;
                    // Pattern: "10 star: (5)" or "10 star:"
                    const match = text.match(/(\\d+) star:.*?\\((\\d+)\\)/);
                    if (match) {
                        const stars = parseInt(match[1]);
                        const count = parseInt(match[2]);
                        breakdown[stars] = count;
                    }
                }
                if (Object.keys(breakdown).length > 0) {
                    result.quality.breakdown = breakdown;
                }
            }

            // Performance rating - from #ratings_p span (if exists)
            const perfRateit = document.querySelector('#ratings_p[data-rateit-value]');
            if (perfRateit) {
                const score = parseFloat(perfRateit.getAttribute('data-rateit-value'));
                if (!isNaN(score)) {
                    result.performance.score = score;
                }
            }

            // Performance breakdown - from #votes_p_breakdown table
            const perfBreakdown = document.querySelector('#votes_p_breakdown');
            if (perfBreakdown) {
                const breakdown = {};
                const rows = perfBreakdown.querySelectorAll('tr');
                for (const row of rows) {
                    const text = row.innerText;
                    const match = text.match(/(\\d+) star:.*?\\((\\d+)\\)/);
                    if (match) {
                        const stars = parseInt(match[1]);
                        const count = parseInt(match[2]);
                        breakdown[stars] = count;
                    }
                }
                if (Object.keys(breakdown).length > 0) {
                    result.performance.breakdown = breakdown;
                }
            }

            return result;
        }''')

        result["quality_score"] = ratings.get("quality", {}).get("score")
        result["quality_votes"] = ratings.get("quality", {}).get("votes")
        result["quality_breakdown"] = ratings.get("quality", {}).get("breakdown")
        result["performance_score"] = ratings.get("performance", {}).get("score")
        result["performance_votes"] = ratings.get("performance", {}).get("votes")
        result["performance_breakdown"] = ratings.get("performance", {}).get("breakdown")

        # Extract full description text - FIXED: Get from #description tab pane
        description = page.evaluate('''() => {
            // Primary: Get from the description tab pane
            const descTab = document.querySelector('#description');
            if (descTab) {
                // Get the content but exclude the catalyst h4 headers
                let text = '';
                const childNodes = descTab.childNodes;
                let isDescription = false;
                let isCatalyst = false;

                for (const node of childNodes) {
                    if (node.nodeType === 1) { // Element node
                        const tagName = node.tagName.toLowerCase();
                        const innerText = node.innerText || '';

                        // Skip h4 headers but track sections
                        if (tagName === 'h4') {
                            if (innerText.trim() === 'Description') {
                                isDescription = true;
                                continue;
                            } else if (innerText.trim() === 'Catalyst') {
                                isCatalyst = true;
                                text += '\\n\\nCATALYST:\\n';
                                continue;
                            }
                        }

                        // Skip empty divs and certain elements
                        if (tagName === 'div' && innerText.trim() === '') continue;
                        if (node.id && node.id.includes('_div')) continue;

                        // Add the text content
                        if (innerText.trim().length > 0) {
                            text += innerText.trim() + '\\n';
                        }
                    } else if (node.nodeType === 3) { // Text node
                        const trimmed = node.textContent.trim();
                        if (trimmed.length > 0) {
                            text += trimmed + '\\n';
                        }
                    }
                }

                return text.trim();
            }

            // Fallback: get text from paragraphs (but avoid modal content)
            let text = '';
            const paragraphs = document.querySelectorAll('#description p, .tab-content p');
            for (const p of paragraphs) {
                const content = p.innerText.trim();
                if (content.length > 50 && !content.includes('By closing position')) {
                    text += content + '\\n\\n';
                }
            }
            return text.trim();
        }''')

        result["description_text"] = description

        # Extract comments - FIXED: Use VIC's specific comment structure
        comments = page.evaluate('''() => {
            const comments = [];

            // Comments are in table rows: tr.comment with id="comment_{id}"
            // The body is in div with id="body_{id}"
            const commentRows = document.querySelectorAll('tr.comment[id^="comment_"]');

            for (const row of commentRows) {
                const id = row.id.replace('comment_', '');
                const bodyDiv = document.querySelector('#body_' + id);

                if (!bodyDiv) continue;

                // Get the body text and clean it
                let bodyText = bodyDiv.innerText.trim();

                // Remove trailing UI elements like "replyview available tags"
                bodyText = bodyText.replace(/\\s*reply\\s*view available tags\\s*$/i, '');
                bodyText = bodyText.replace(/\\s*view available tags\\s*$/i, '');

                if (bodyText.length < 10) continue;

                const comment = {
                    id: id,
                    body_text: bodyText
                };

                // Get author and date from the header row (previous sibling)
                const headerRow = row.previousElementSibling;
                if (headerRow && headerRow.classList.contains('cursor_pointer')) {
                    // Author is in span with title attribute inside displayname1
                    const authorSpan = headerRow.querySelector('.displayname1 span[title]');
                    if (authorSpan) {
                        comment.author = authorSpan.getAttribute('title') || authorSpan.innerText.trim();
                    }

                    // Date is in the second displayname1 div
                    const dateDivs = headerRow.querySelectorAll('.displayname1');
                    if (dateDivs.length >= 2) {
                        comment.date = dateDivs[1].innerText.trim();
                    }

                    // Subject is in vich1 span
                    const subjectSpan = headerRow.querySelector('.vich1');
                    if (subjectSpan) {
                        comment.subject = subjectSpan.innerText.trim();
                    }
                }

                comments.push(comment);
            }

            return comments;
        }''')

        result["comments"] = comments
        result["comment_count"] = len(comments)
        result["has_content"] = True

    except Exception as e:
        result["error"] = str(e)[:200]
        result["has_content"] = False

    return result


def save_full_index(ideas: list):
    """Save the full idea index."""
    index_data = {
        "crawl_date": datetime.now().isoformat(),
        "total_ideas": len(ideas),
        "discovery_method": "year_x_alphabet_matrix",
        "ideas": ideas
    }

    with open(FULL_INDEX_FILE, "w") as f:
        json.dump(index_data, f, indent=2)

    print_status(f"Index saved: {FULL_INDEX_FILE}")


def load_full_index() -> list:
    """Load existing index if available."""
    if FULL_INDEX_FILE.exists():
        with open(FULL_INDEX_FILE, "r") as f:
            data = json.load(f)
        return data.get("ideas", [])
    return []


def load_winners_index() -> list:
    """Load winners index if available."""
    if WINNERS_INDEX_FILE.exists():
        with open(WINNERS_INDEX_FILE, "r") as f:
            data = json.load(f)
        return data.get("winners", [])
    return []


def is_after_cutoff(date_str: str, cutoff_date: str = "August 1, 2025") -> bool:
    """
    Check if a date string is after the cutoff date.
    VIC uses format like "March 26, 2023" or "August 09, 2007".
    """
    if not date_str:
        return False

    try:
        from datetime import datetime
        # Parse VIC date format: "Month DD, YYYY"
        idea_date = datetime.strptime(date_str, "%B %d, %Y")
        cutoff = datetime.strptime(cutoff_date, "%B %d, %Y")
        return idea_date > cutoff
    except ValueError:
        # If we can't parse the date, allow it through
        return False


def is_rate_limited(result: dict, html_path: Path = None) -> bool:
    """
    Detect if a page was rate-limited by VIC.
    Rate-limited pages have:
    - Empty or very short description_text (< 100 chars)
    - Small HTML file (~28KB)
    """
    desc = result.get("description_text", "")
    if len(desc) < 100:
        return True

    # Also check HTML file size if available
    if html_path and html_path.exists():
        size_kb = html_path.stat().st_size / 1024
        if size_kb < 35:  # Rate-limited pages are ~28KB
            return True

    return False


def run_full_download(rediscover: bool = True, delay: float = 5.0, winners_only: bool = False):
    """
    Run the full VIC database download.

    Args:
        rediscover: If True, re-run Year × Alphabet discovery
        delay: Delay between requests in seconds
        winners_only: If True, only extract contest winners from winners_index.json
    """
    print("=" * 70)
    if winners_only:
        print("  VIC WINNERS DOWNLOADER")
        print("  Contest Winners Extraction")
    else:
        print("  VIC FULL DATABASE DOWNLOADER")
        print("  Year × Alphabet Matrix Discovery + Full Content Extraction")
    print("=" * 70)
    print()

    # Load cookies
    cookies = load_cookies()
    if not cookies:
        print_status("✗ ERROR: No cookies found at cookies.json")
        print_status("  Please export your VIC session cookies first.")
        return

    print_status(f"Loaded {len(cookies)} cookies")

    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
            args=['--disable-blink-features=AutomationControlled']
        )

        context = browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        )

        # Add cookies
        context.add_cookies(cookies)

        page = context.new_page()
        page.set_default_timeout(60000)

        # Verify authentication
        print()
        if not verify_authentication(page):
            print_status("Continuing anyway, but some content may be restricted...")

        # Phase 1: Discovery
        print("\n" + "=" * 70)
        print("  PHASE 1: IDEA DISCOVERY")
        print("=" * 70)

        if winners_only:
            ideas = load_winners_index()
            if not ideas:
                print_status("ERROR: No winners index found at data/winners_index.json")
                print_status("Run winner discovery first.")
                browser.close()
                return
            print_status(f"Using winners index with {len(ideas):,} contest winners")
        else:
            existing_index = load_full_index()
            if existing_index and not rediscover:
                print_status(f"Using existing index with {len(existing_index):,} ideas")
                ideas = existing_index
            else:
                ideas = discover_ideas_year_alphabet(page)
                save_full_index(ideas)

        # Phase 2: Content Extraction
        print("\n" + "=" * 70)
        print("  PHASE 2: FULL CONTENT EXTRACTION")
        print("=" * 70)

        total = len(ideas)
        successful = 0
        failed = 0

        # Skip already extracted ideas
        existing_ids = {f.stem for f in STRUCTURED_DIR.glob("*.json")}
        remaining = [i for i in ideas if i["id"] not in existing_ids]
        skipped = total - len(remaining)

        if skipped > 0:
            print_status(f"Skipping {skipped:,} already extracted ideas")

        print_status(f"Extracting {len(remaining):,} remaining ideas...")
        print_status(f"Raw HTML → data/raw/  |  Structured JSON → data/structured/")
        print()

        rate_limited_count = 0

        for i, idea in enumerate(remaining):
            # Progress bar
            print_progress_bar(i + 1, len(remaining), f"Extracting")

            try:
                result = extract_full_content(page, idea)
                raw_path = RAW_DIR / f"{idea['id']}.html"

                # Check if rate-limited
                if is_rate_limited(result, raw_path):
                    rate_limited_count += 1
                    # Delete bad files
                    if raw_path.exists():
                        raw_path.unlink()
                    structured_path = STRUCTURED_DIR / f"{idea['id']}.json"
                    if structured_path.exists():
                        structured_path.unlink()

                    if rate_limited_count >= 3:
                        print(f"\n\n⚠️  Rate limit detected! ({rate_limited_count} consecutive blocked pages)")
                        print("    Stopping as requested. Re-run with fresh cookies when ready.")
                        browser.close()
                        return
                    continue

                # Reset counter on success
                rate_limited_count = 0

                # Skip ideas after cutoff date (August 1, 2025) to avoid membership content gate
                idea_date = result.get("date", "")
                if is_after_cutoff(idea_date):
                    print(f"\n    Skipping post-cutoff idea: {idea_date}")
                    # Delete raw HTML since we don't want it
                    if raw_path.exists():
                        raw_path.unlink()
                    continue

                # Save structured JSON
                structured_path = STRUCTURED_DIR / f"{idea['id']}.json"
                with open(structured_path, "w", encoding="utf-8") as f:
                    json.dump(result, f, indent=2, ensure_ascii=False)

                if result.get("has_content"):
                    successful += 1
                else:
                    failed += 1

            except Exception as e:
                failed += 1

            # Rate limiting delay
            if i < len(remaining) - 1:
                time.sleep(delay)

        browser.close()

    # Final summary
    print("\n\n" + "=" * 70)
    print("  DOWNLOAD COMPLETE")
    print("=" * 70)
    print_status(f"Total ideas processed: {total:,}")
    print_status(f"Successful extractions: {successful:,}")
    print_status(f"Failed extractions: {failed:,}")
    print_status(f"Raw HTML files: {RAW_DIR}")
    print_status(f"Structured JSON files: {STRUCTURED_DIR}")
    print("=" * 70)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="VIC Full Database Downloader")
    parser.add_argument("--no-rediscover", action="store_true",
                        help="Use existing index instead of rediscovering")
    parser.add_argument("--delay", type=float, default=5.0,
                        help="Delay between requests in seconds (default: 5.0)")
    parser.add_argument("--winners-only", action="store_true",
                        help="Only extract contest winners from winners_index.json")

    args = parser.parse_args()

    run_full_download(rediscover=not args.no_rediscover, delay=args.delay, winners_only=args.winners_only)
