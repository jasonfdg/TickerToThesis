"""
Test extraction for a small batch of ideas to verify quality.
"""
import json
import sys
from pathlib import Path
from playwright.sync_api import sync_playwright

# Import from main module
sys.path.insert(0, str(Path(__file__).parent))
from vic_full_download import (
    load_cookies, load_full_index, extract_full_content,
    STRUCTURED_DIR, BASE_URL, print_status
)


def run_test_batch(count: int = 5):
    """Test extraction on a small batch."""
    print(f"Testing extraction on {count} ideas...")

    cookies = load_cookies()
    if not cookies:
        print("No cookies found!")
        return

    ideas = load_full_index()
    if not ideas:
        print("No index found!")
        return

    # Pick a diverse sample
    test_ideas = ideas[:count]

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
            print("WARNING: Not authenticated!")
        else:
            print("✓ Authentication verified")

        for i, idea in enumerate(test_ideas):
            print(f"\n--- Testing {i+1}/{count}: {idea.get('company_name', 'Unknown')} ---")

            result = extract_full_content(page, idea)

            # Save result
            path = STRUCTURED_DIR / f"{idea['id']}.json"
            with open(path, "w") as f:
                json.dump(result, f, indent=2)

            # Print quality report
            print(f"  ID: {result.get('id')}")
            print(f"  Ticker: {result.get('ticker')} {'✓' if result.get('ticker') else '✗'}")
            print(f"  Author: {result.get('author')} {'✓' if result.get('author') else '✗'}")
            print(f"  Date: {result.get('date')} {'✓' if result.get('date') else '✗'}")
            print(f"  Quality Score: {result.get('quality_score')} {'✓' if result.get('quality_score') else '✗'}")
            print(f"  Quality Votes: {result.get('quality_votes')}")
            print(f"  Quality Breakdown: {result.get('quality_breakdown')}")
            print(f"  Description: {len(result.get('description_text', '')) if result.get('description_text') else 0} chars {'✓' if result.get('description_text') and len(result.get('description_text', '')) > 100 else '✗'}")
            print(f"  Comments: {result.get('comment_count', 0)} {'✓' if result.get('comment_count', 0) > 0 else '○'}")

            # Check for UI noise in description
            desc = result.get('description_text', '')
            if 'By closing position' in desc or 'Flagging an idea' in desc:
                print(f"  ⚠️  WARNING: UI noise in description!")

            page.wait_for_timeout(2000)

        browser.close()

    print("\n" + "=" * 50)
    print("Test complete! Check data/structured/ for results.")


if __name__ == "__main__":
    run_test_batch(5)
