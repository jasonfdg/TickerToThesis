"""
Parallel extraction - run a specific range of ideas.
Usage: python vic_parallel_extract.py --start 0 --end 5000
"""
import json
import sys
import time
import argparse
from pathlib import Path
from datetime import datetime
from playwright.sync_api import sync_playwright

sys.path.insert(0, str(Path(__file__).parent))
from vic_full_download import (
    load_cookies, load_full_index, extract_full_content,
    STRUCTURED_DIR, RAW_DIR, BASE_URL, print_status, print_progress_bar
)


def run_range_extraction(start: int, end: int, delay: float = 2.0, worker_id: int = 0):
    """Extract a specific range of ideas."""
    print(f"=" * 60)
    print(f"  WORKER {worker_id}: Extracting ideas {start} to {end}")
    print(f"=" * 60)

    cookies = load_cookies()
    if not cookies:
        print("No cookies found!")
        return

    ideas = load_full_index()
    if not ideas:
        print("No index found!")
        return

    # Get the slice
    ideas_slice = ideas[start:end]
    total = len(ideas_slice)
    print_status(f"Worker {worker_id}: Processing {total} ideas ({start}-{end})")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
        )
        context.add_cookies(cookies)

        page = context.new_page()
        page.set_default_timeout(60000)

        # Verify auth
        page.goto(f"{BASE_URL}/ideas", wait_until="domcontentloaded")
        page.wait_for_timeout(2000)
        if "Logout" not in page.content():
            print(f"Worker {worker_id}: WARNING - Not authenticated!")
        else:
            print_status(f"Worker {worker_id}: Authentication verified")

        successful = 0
        failed = 0

        for i, idea in enumerate(ideas_slice):
            # Skip if already extracted
            existing = STRUCTURED_DIR / f"{idea['id']}.json"
            if existing.exists():
                continue

            print_progress_bar(i + 1, total, f"W{worker_id}")

            try:
                result = extract_full_content(page, idea)

                path = STRUCTURED_DIR / f"{idea['id']}.json"
                with open(path, "w") as f:
                    json.dump(result, f, indent=2)

                if result.get("has_content"):
                    successful += 1
                else:
                    failed += 1

            except Exception as e:
                failed += 1

            time.sleep(delay)

        browser.close()

    print(f"\n\nWorker {worker_id} complete: {successful} success, {failed} failed")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--start", type=int, required=True)
    parser.add_argument("--end", type=int, required=True)
    parser.add_argument("--delay", type=float, default=2.0)
    parser.add_argument("--worker", type=int, default=0)
    args = parser.parse_args()

    run_range_extraction(args.start, args.end, args.delay, args.worker)
