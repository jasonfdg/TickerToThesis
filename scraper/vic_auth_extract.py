"""
VIC Authenticated Extractor
Uses exported browser cookies to access full report content.
"""

import json
import base64
import re
import time
from pathlib import Path
from datetime import datetime
from playwright.sync_api import sync_playwright

# Project paths
PROJECT_ROOT = Path(__file__).parent.parent
RAW_DIR = PROJECT_ROOT / "data" / "raw"
PARSED_DIR = PROJECT_ROOT / "data" / "parsed"
INDEX_FILE = PROJECT_ROOT / "data" / "reports_index.json"
COOKIES_FILE = PROJECT_ROOT / "cookies.json"

RAW_DIR.mkdir(parents=True, exist_ok=True)
PARSED_DIR.mkdir(parents=True, exist_ok=True)


def load_cookies() -> list:
    """Load cookies from exported file."""
    if COOKIES_FILE.exists():
        with open(COOKIES_FILE, "r") as f:
            return json.load(f)
    return []


def extract_content_images(page, idea_id: str) -> list:
    """Extract base64 content images from current page."""
    image_paths = []

    images = page.evaluate('''() => {
        const imgs = document.querySelectorAll('img[src^="data:image"]');
        return Array.from(imgs).map((img, idx) => ({
            src: img.src,
            width: img.width,
            height: img.height,
            index: idx
        })).filter(img => img.width > 200);
    }''')

    for img_data in images:
        match = re.match(r"data:image/(\w+);base64,(.+)", img_data["src"])
        if match:
            img_format, b64_data = match.groups()
            img_bytes = base64.b64decode(b64_data)

            img_filename = f"{idea_id}_content_{img_data['index']}.{img_format}"
            img_path = RAW_DIR / img_filename
            with open(img_path, "wb") as f:
                f.write(img_bytes)

            image_paths.append({
                "path": str(img_path),
                "filename": img_filename,
                "width": img_data["width"],
                "height": img_data["height"],
            })

    return image_paths


def extract_metadata(page) -> dict:
    """Extract metadata from current page."""
    return page.evaluate('''() => {
        const body = document.body.innerText;
        const data = {};

        // Date
        const dateMatch = body.match(/([A-Z][a-z]+ \\d{1,2}, \\d{4})/);
        if (dateMatch) data.date = dateMatch[1];

        // Financial data
        const priceMatch = body.match(/Price:\\s*([\\d.]+)/);
        if (priceMatch) data.price = priceMatch[1];

        const mcapMatch = body.match(/Market Cap.*?:\\s*([\\d,]+)/);
        if (mcapMatch) data.market_cap = mcapMatch[1];

        return data;
    }''')


def run_authenticated_extraction(max_ideas: int = 250, delay: float = 2.5):
    """
    Run extraction with authenticated session.
    """
    # Load cookies
    cookies = load_cookies()
    if not cookies:
        print("No cookies found! Export cookies from browser first.")
        return

    print(f"Loaded {len(cookies)} cookies")

    # Load index
    if not INDEX_FILE.exists():
        print("No index file found. Run crawler first.")
        return

    with open(INDEX_FILE, "r") as f:
        index_data = json.load(f)

    ideas = index_data.get("ideas", [])[:max_ideas]
    print(f"Processing {len(ideas)} ideas with authenticated session...")

    results = []

    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
            args=['--disable-blink-features=AutomationControlled']
        )

        context = browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        )

        # Add cookies to context
        context.add_cookies(cookies)
        print("Cookies loaded into browser context")

        page = context.new_page()
        page.set_default_timeout(45000)

        # Verify authentication by visiting homepage
        print("Verifying authentication...")
        page.goto("https://www.valueinvestorsclub.com/ideas", wait_until="domcontentloaded")
        page.wait_for_timeout(3000)

        # Check if logged in
        page_content = page.content()
        if "Login" in page_content and "Logout" not in page_content:
            print("WARNING: May not be authenticated. Cookies might be expired.")
        else:
            print("Authentication verified!")

        # Process each idea
        for i, idea in enumerate(ideas):
            idea_id = idea.get("id", f"unknown_{i}")
            url = idea.get("url", "")

            print(f"[{i+1}/{len(ideas)}] {idea.get('company_name', 'Unknown')}...", end=" ", flush=True)

            try:
                page.goto(url, wait_until="domcontentloaded")
                page.wait_for_timeout(4000)

                # Extract metadata
                metadata = extract_metadata(page)
                metadata["id"] = idea_id
                metadata["url"] = url
                metadata["company_name"] = idea.get("company_name", "")
                metadata["ticker"] = idea.get("ticker", "")

                # Extract content images
                content_images = extract_content_images(page, idea_id)
                metadata["content_images"] = content_images
                metadata["has_content"] = len(content_images) > 0

                # Save individual result
                result_path = PARSED_DIR / f"{idea_id}.json"
                with open(result_path, "w") as f:
                    json.dump(metadata, f, indent=2)

                results.append(metadata)
                print(f"OK ({len(content_images)} images)")

            except Exception as e:
                print(f"ERROR: {str(e)[:50]}")
                results.append({
                    "id": idea_id,
                    "url": url,
                    "error": str(e)[:200],
                    "has_content": False
                })

            # Rate limiting
            if i < len(ideas) - 1:
                time.sleep(delay)

        browser.close()

    # Save summary
    summary = {
        "extracted_at": datetime.now().isoformat(),
        "total_processed": len(results),
        "successful": sum(1 for r in results if r.get("has_content")),
        "failed": sum(1 for r in results if "error" in r),
        "ideas": results
    }

    summary_path = PARSED_DIR / "extraction_summary.json"
    with open(summary_path, "w") as f:
        json.dump(summary, f, indent=2)

    print(f"\n{'='*50}")
    print(f"Extraction complete!")
    print(f"  Processed: {len(results)}")
    print(f"  Successful: {summary['successful']}")
    print(f"  Failed: {summary['failed']}")
    print(f"  Summary: {summary_path}")


if __name__ == "__main__":
    run_authenticated_extraction(max_ideas=250, delay=2.5)
