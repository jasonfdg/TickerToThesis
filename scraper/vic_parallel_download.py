"""
VIC Parallel Database Downloader
Async version using Playwright's async API for true concurrency.
Includes jitter, exponential backoff, retry logic, and error rate monitoring.

Usage:
    python vic_parallel_download.py --workers 3 --delay 2.5
"""

import asyncio
import json
import random
import sys
import time
from datetime import datetime
from pathlib import Path

# Add scraper directory to path for direct execution
SCRIPT_DIR = Path(__file__).parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from playwright.async_api import async_playwright

from vic_full_download import (
    PROJECT_ROOT,
    RAW_DIR,
    STRUCTURED_DIR,
    FULL_INDEX_FILE,
    COOKIES_FILE,
    BASE_URL,
    print_status,
    load_cookies,
    load_full_index,
    is_rate_limited,
)

# Progress tracking
progress_state = {"completed": 0, "successful": 0, "failed": 0, "total": 0}


def with_jitter(base_delay: float, jitter: float = 1.0) -> float:
    """Add random jitter to delay to look natural."""
    return base_delay + random.uniform(0, jitter)


def exponential_backoff(attempt: int, base: float = 2.5, max_delay: float = 30.0) -> float:
    """Calculate exponential backoff delay for retries."""
    delay = base * (2 ** attempt) + random.uniform(0, 1)
    return min(delay, max_delay)


def print_progress(prefix: str = "Extracting", width: int = 40):
    """Print progress bar."""
    current = progress_state["completed"]
    total = progress_state["total"]
    successful = progress_state["successful"]
    failed = progress_state["failed"]

    if total == 0:
        return

    filled = int(width * current / total)
    bar = "█" * filled + "░" * (width - filled)
    percent = current / total * 100

    sys.stdout.write(f"\r{prefix}: [{bar}] {current:,}/{total:,} ({percent:.1f}%) | ✓{successful} ✗{failed}")
    sys.stdout.flush()


async def extract_full_content_async(page, idea: dict) -> dict:
    """
    Async version of content extraction.
    Directly extracts data using Playwright's async API.
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
        await page.goto(idea["url"], wait_until="networkidle", timeout=60000)

        # Wait for critical content elements with generous timeout
        content_loaded = False
        try:
            # Wait for the description tab - this is the key content
            await page.wait_for_selector('#description', timeout=15000)
            content_loaded = True
        except:
            # Fallback: try waiting for any idea content
            try:
                await page.wait_for_selector('.idea_by, .idea_name', timeout=10000)
                content_loaded = True
            except:
                pass

        # Additional wait to ensure JS rendering completes
        # Longer wait if content didn't load properly
        if content_loaded:
            await page.wait_for_timeout(4000)
        else:
            # Extra time for slow pages
            await page.wait_for_timeout(8000)

        # Save raw HTML
        html_content = await page.content()
        raw_path = RAW_DIR / f"{idea['id']}.html"
        with open(raw_path, "w", encoding="utf-8") as f:
            f.write(html_content)
        result["raw_html_path"] = str(raw_path)

        # Extract structured data via JavaScript
        data = await page.evaluate('''() => {
            const result = {};

            // Ticker
            const titleSpan = document.querySelector('.idea_name span[style*="color:#ccc"], .vich1 span[style*="color:#ccc"]');
            if (titleSpan) result.ticker = titleSpan.innerText.trim();

            // Author
            const authorLink = document.querySelector('.idea_by a.display_name, .idea_by a[href*="/member/"]');
            if (authorLink) result.author = authorLink.innerText.trim();

            // Date
            const ideaByDiv = document.querySelector('.idea_by');
            if (ideaByDiv) {
                const dateMatch = ideaByDiv.innerText.match(/([A-Z][a-z]+ \\d{1,2}, \\d{4})/);
                if (dateMatch) result.date = dateMatch[1];
            }

            // Position type
            const positionLabel = document.querySelector('.label-short, [class*="short"]');
            if (positionLabel && positionLabel.innerText.toLowerCase().includes('short')) {
                result.position_type = 'short';
            } else {
                result.position_type = 'long';
            }

            // Financial data from tables
            const tables = document.querySelectorAll('table');
            for (const table of tables) {
                const rows = table.querySelectorAll('tr');
                for (const row of rows) {
                    const text = row.innerText;
                    if (text.includes('Price:')) {
                        const cells = row.querySelectorAll('td');
                        for (let i = 0; i < cells.length; i++) {
                            if (cells[i].innerText.includes('Price:') && cells[i+2]) {
                                const val = cells[i+2].innerText.trim();
                                if (val && !isNaN(parseFloat(val))) result.price = val;
                            }
                        }
                    }
                    if (text.includes('Market Cap')) {
                        const cells = row.querySelectorAll('td');
                        for (let i = 0; i < cells.length; i++) {
                            if (cells[i].innerText.includes('Market Cap') && cells[i+2]) {
                                const val = cells[i+2].innerText.trim();
                                if (val && val !== '0') result.market_cap = val;
                            }
                        }
                    }
                }
            }

            return result;
        }''')

        result.update(data)

        # Extract ratings
        ratings = await page.evaluate('''() => {
            const result = {quality: {}, performance: {}};

            const qualityRateit = document.querySelector('#ratings_q[data-rateit-value]');
            if (qualityRateit) {
                const score = parseFloat(qualityRateit.getAttribute('data-rateit-value'));
                if (!isNaN(score)) result.quality.score = score;
            }

            const qualitySection = document.querySelector('.col-xs-12.col-sm-3');
            if (qualitySection) {
                const votesMatch = qualitySection.innerText.match(/(\\d+) votes?\\)/);
                if (votesMatch) result.quality.votes = parseInt(votesMatch[1]);
            }

            const qualityBreakdown = document.querySelector('#votes_q_breakdown');
            if (qualityBreakdown) {
                const breakdown = {};
                const rows = qualityBreakdown.querySelectorAll('tr');
                for (const row of rows) {
                    const text = row.innerText;
                    const match = text.match(/(\\d+) star:.*?\\((\\d+)\\)/);
                    if (match) breakdown[parseInt(match[1])] = parseInt(match[2]);
                }
                if (Object.keys(breakdown).length > 0) result.quality.breakdown = breakdown;
            }

            const perfRateit = document.querySelector('#ratings_p[data-rateit-value]');
            if (perfRateit) {
                const score = parseFloat(perfRateit.getAttribute('data-rateit-value'));
                if (!isNaN(score)) result.performance.score = score;
            }

            return result;
        }''')

        result["quality_score"] = ratings.get("quality", {}).get("score")
        result["quality_votes"] = ratings.get("quality", {}).get("votes")
        result["quality_breakdown"] = ratings.get("quality", {}).get("breakdown")
        result["performance_score"] = ratings.get("performance", {}).get("score")

        # Extract description
        description = await page.evaluate('''() => {
            const descTab = document.querySelector('#description');
            if (descTab) {
                let text = '';
                for (const node of descTab.childNodes) {
                    if (node.nodeType === 1) {
                        const tagName = node.tagName.toLowerCase();
                        const innerText = node.innerText || '';
                        if (tagName === 'h4') {
                            if (innerText.trim() === 'Catalyst') text += '\\n\\nCATALYST:\\n';
                            continue;
                        }
                        if (tagName === 'div' && innerText.trim() === '') continue;
                        if (node.id && node.id.includes('_div')) continue;
                        if (innerText.trim().length > 0) text += innerText.trim() + '\\n';
                    }
                }
                return text.trim();
            }
            return '';
        }''')

        result["description_text"] = description

        # Extract comments
        comments = await page.evaluate('''() => {
            const comments = [];
            const commentRows = document.querySelectorAll('tr.comment[id^="comment_"]');

            for (const row of commentRows) {
                const id = row.id.replace('comment_', '');
                const bodyDiv = document.querySelector('#body_' + id);
                if (!bodyDiv) continue;

                let bodyText = bodyDiv.innerText.trim();
                bodyText = bodyText.replace(/\\s*reply\\s*view available tags\\s*$/i, '');
                bodyText = bodyText.replace(/\\s*view available tags\\s*$/i, '');
                if (bodyText.length < 10) continue;

                const comment = { id: id, body_text: bodyText };

                const headerRow = row.previousElementSibling;
                if (headerRow && headerRow.classList.contains('cursor_pointer')) {
                    const authorSpan = headerRow.querySelector('.displayname1 span[title]');
                    if (authorSpan) comment.author = authorSpan.getAttribute('title') || authorSpan.innerText.trim();

                    const dateDivs = headerRow.querySelectorAll('.displayname1');
                    if (dateDivs.length >= 2) comment.date = dateDivs[1].innerText.trim();

                    const subjectSpan = headerRow.querySelector('.vich1');
                    if (subjectSpan) comment.subject = subjectSpan.innerText.trim();
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


async def worker(semaphore, browser, cookies: list, idea: dict, delay: float, max_retries: int = 3) -> dict:
    """
    Async worker function.
    Uses semaphore to limit concurrency.
    """
    async with semaphore:
        context = None
        result = {"id": idea["id"], "error": None, "has_content": False}

        try:
            context = await browser.new_context(
                viewport={'width': 1920, 'height': 1080},
                user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
            )
            await context.add_cookies(cookies)
            page = await context.new_page()
            page.set_default_timeout(60000)

            for attempt in range(max_retries):
                try:
                    result = await extract_full_content_async(page, idea)
                    if result.get("has_content"):
                        break
                    elif attempt < max_retries - 1:
                        await asyncio.sleep(exponential_backoff(attempt))
                except Exception as e:
                    if attempt < max_retries - 1:
                        await asyncio.sleep(exponential_backoff(attempt))
                    else:
                        result = {
                            "id": idea["id"],
                            "url": idea.get("url", ""),
                            "error": f"Failed after {max_retries} attempts: {str(e)[:100]}",
                            "has_content": False,
                            "extracted_at": datetime.now().isoformat()
                        }

            # Jittered delay
            await asyncio.sleep(with_jitter(delay))

        finally:
            if context:
                try:
                    await context.close()
                except:
                    pass

        return result


async def run_parallel_extraction(browser, ideas: list, cookies: list,
                                   workers: int = 2, delay: float = 5.0):
    """
    Run parallel extraction using async semaphore for concurrency control.
    """
    global progress_state

    # Skip already extracted
    existing_ids = {f.stem for f in STRUCTURED_DIR.glob("*.json")}
    remaining = [i for i in ideas if i["id"] not in existing_ids]

    skipped = len(ideas) - len(remaining)
    if skipped > 0:
        print_status(f"Skipping {skipped:,} already extracted ideas")

    if not remaining:
        print_status("All ideas already extracted!")
        return 0, 0

    print_status(f"Extracting {len(remaining):,} remaining ideas with {workers} workers")
    print_status(f"Base delay: {delay}s + jitter | Max retries: 3")
    print()

    progress_state = {"completed": 0, "successful": 0, "failed": 0, "total": len(remaining)}

    # Semaphore limits concurrent workers
    semaphore = asyncio.Semaphore(workers)

    async def process_idea(idea):
        result = await worker(semaphore, browser, cookies, idea, delay)
        raw_path = RAW_DIR / f"{idea['id']}.html"
        structured_path = STRUCTURED_DIR / f"{idea['id']}.json"

        # Check if rate-limited
        if is_rate_limited(result, raw_path):
            # Delete bad files
            if raw_path.exists():
                raw_path.unlink()
            if structured_path.exists():
                structured_path.unlink()

            # Update progress (count as failed)
            progress_state["completed"] += 1
            progress_state["failed"] += 1
            print_progress()
            return result

        # Save result
        with open(structured_path, "w", encoding="utf-8") as f:
            json.dump(result, f, indent=2, ensure_ascii=False)

        # Update progress
        progress_state["completed"] += 1
        if result.get("has_content"):
            progress_state["successful"] += 1
        else:
            progress_state["failed"] += 1

        print_progress()
        return result

    # Process all ideas concurrently (semaphore limits actual parallelism)
    results = await asyncio.gather(*[process_idea(idea) for idea in remaining], return_exceptions=True)

    print()
    return progress_state["successful"], progress_state["failed"]


async def verify_authentication_async(page) -> bool:
    """Verify VIC login status."""
    await page.goto(f"{BASE_URL}/ideas", wait_until="domcontentloaded", timeout=60000)
    await page.wait_for_timeout(3000)
    content = await page.content()

    if "Logout" in content:
        print_status("✓ Authentication verified - logged in")
        return True
    else:
        print_status("✗ WARNING: Not authenticated - cookies may be expired")
        return False


async def run_parallel_download_async(workers: int = 2, delay: float = 5.0):
    """Main async entry point."""
    print("=" * 70)
    print("  VIC PARALLEL DATABASE DOWNLOADER (Async)")
    print(f"  {workers} Workers | {delay}s Base Delay | Jitter + Backoff Enabled")
    print("=" * 70)
    print()

    cookies = load_cookies()
    if not cookies:
        print_status("✗ ERROR: No cookies found at cookies.json")
        return

    print_status(f"Loaded {len(cookies)} cookies")

    ideas = load_full_index()
    if not ideas:
        print_status("✗ ERROR: No idea index found. Run vic_full_download.py first.")
        return

    print_status(f"Loaded index with {len(ideas):,} ideas")

    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=['--disable-blink-features=AutomationControlled']
        )

        # Quick auth check
        temp_context = await browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
        )
        await temp_context.add_cookies(cookies)
        temp_page = await temp_context.new_page()

        print()
        if not await verify_authentication_async(temp_page):
            print_status("Continuing anyway, but some content may be restricted...")

        await temp_context.close()

        print("\n" + "=" * 70)
        print("  PARALLEL CONTENT EXTRACTION")
        print("=" * 70)

        start_time = time.time()
        successful, failed = await run_parallel_extraction(
            browser, ideas, cookies, workers=workers, delay=delay
        )
        elapsed = time.time() - start_time

        await browser.close()

    print("\n" + "=" * 70)
    print("  DOWNLOAD COMPLETE")
    print("=" * 70)
    print_status(f"Time elapsed: {elapsed/60:.1f} minutes")
    print_status(f"Successful extractions: {successful:,}")
    print_status(f"Failed extractions: {failed:,}")
    print_status(f"Structured JSON files: {STRUCTURED_DIR}")

    if failed > 0:
        print_status(f"Tip: Re-run to retry failed extractions (resume-capable)")

    print("=" * 70)


def run_parallel_download(workers: int = 2, delay: float = 5.0):
    """Sync wrapper for async main."""
    asyncio.run(run_parallel_download_async(workers, delay))


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="VIC Parallel Database Downloader (Async)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python vic_parallel_download.py                    # 2 workers, 5.0s delay (safe)
  python vic_parallel_download.py --workers 3       # 3 workers (faster but riskier)
  python vic_parallel_download.py --delay 7.0       # Slower, safer
  python vic_parallel_download.py --workers 1       # Sequential fallback
        """
    )

    parser.add_argument(
        "--workers", type=int, default=2,
        choices=range(1, 6),
        metavar="N",
        help="Number of parallel workers (1-5, default: 2)"
    )

    parser.add_argument(
        "--delay", type=float, default=5.0,
        help="Base delay between requests per worker in seconds (default: 5.0)"
    )

    args = parser.parse_args()

    run_parallel_download(workers=args.workers, delay=args.delay)
