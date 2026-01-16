"""
VIC Extractor Module
Extracts full report content (as images) and comments from individual idea pages.
"""

import json
import base64
import re
import time
from pathlib import Path
from datetime import datetime
from tqdm import tqdm

from playwright.sync_api import sync_playwright
from scraper.vic_auth import VICSession, load_cookies, COOKIES_FILE

# Project paths
PROJECT_ROOT = Path(__file__).parent.parent
RAW_DIR = PROJECT_ROOT / "data" / "vic" / "raw"
PARSED_DIR = PROJECT_ROOT / "data" / "vic" / "parsed"
INDEX_FILE = PROJECT_ROOT / "data" / "vic" / "index" / "reports_index.json"


def ensure_dirs():
    """Create necessary directories."""
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    PARSED_DIR.mkdir(parents=True, exist_ok=True)


def extract_metadata(page) -> dict:
    """Extract idea metadata from page."""
    metadata = {}

    # Title and ticker
    title_el = page.query_selector("h1, .idea-title, [class*='title']")
    if title_el:
        title_text = title_el.inner_text().strip()
        metadata["title"] = title_text

    # Date
    date_text = page.evaluate('''() => {
        const body = document.body.innerText;
        const match = body.match(/([A-Z][a-z]+ \\d{1,2}, \\d{4})/);
        return match ? match[1] : null;
    }''')
    metadata["date"] = date_text

    # Financial data table
    financials = page.evaluate('''() => {
        const body = document.body.innerText;
        const data = {};

        // Extract price
        const priceMatch = body.match(/Price:\\s*([\\d.]+)/);
        if (priceMatch) data.price = priceMatch[1];

        // Market cap
        const mcapMatch = body.match(/Market Cap.*?:\\s*([\\d,]+)/);
        if (mcapMatch) data.market_cap = mcapMatch[1];

        // P/E
        const peMatch = body.match(/P\\/E\\s+([\\d.]+)/);
        if (peMatch) data.pe_ratio = peMatch[1];

        // EPS
        const epsMatch = body.match(/EPS\\s+([\\d.]+)/);
        if (epsMatch) data.eps = epsMatch[1];

        return data;
    }''')
    metadata["financials"] = financials

    return metadata


def extract_content_images(page, idea_id: str) -> list:
    """
    Extract all content images from the description section.
    Returns list of saved image paths.
    """
    image_paths = []

    # Get all base64 images from description
    images = page.evaluate('''() => {
        const container = document.querySelector('#description') || document.body;
        const imgs = container.querySelectorAll('img[src^="data:image"]');
        return Array.from(imgs).map((img, idx) => ({
            src: img.src,
            width: img.width,
            height: img.height,
            index: idx
        }));
    }''')

    for img_data in images:
        if img_data["src"].startswith("data:image"):
            # Extract base64 data
            match = re.match(r"data:image/(\w+);base64,(.+)", img_data["src"])
            if match:
                img_format, b64_data = match.groups()
                img_bytes = base64.b64decode(b64_data)

                # Save image
                img_filename = f"{idea_id}_content_{img_data['index']}.{img_format}"
                img_path = RAW_DIR / img_filename
                with open(img_path, "wb") as f:
                    f.write(img_bytes)

                image_paths.append({
                    "path": str(img_path),
                    "filename": img_filename,
                    "width": img_data["width"],
                    "height": img_data["height"],
                    "format": img_format,
                })

    return image_paths


def extract_comments(page) -> list:
    """
    Extract comments/messages from the idea page.
    Note: Comments may also be images or protected.
    """
    comments = []

    # Click on Messages tab if present
    try:
        msgs_tab = page.query_selector('a[href="#messages"]')
        if msgs_tab:
            msgs_tab.click()
            page.wait_for_timeout(2000)
    except:
        pass

    # Try to extract message content
    # Note: VIC may protect these too
    msg_elements = page.query_selector_all(".message, .comment, [class*='msg']")

    for msg in msg_elements[:50]:  # Limit to avoid too many
        try:
            text = msg.inner_text().strip()
            if text and len(text) > 20:
                comments.append({
                    "text": text[:1000],  # Truncate long comments
                    "type": "text"
                })
        except:
            continue

    # Also check for comment images
    comment_images = page.evaluate('''() => {
        const msgs = document.querySelector('#messages');
        if (!msgs) return [];
        const imgs = msgs.querySelectorAll('img[src^="data:image"]');
        return Array.from(imgs).map(img => img.src);
    }''')

    for i, img_src in enumerate(comment_images[:20]):
        comments.append({
            "type": "image",
            "index": i,
            "data": img_src[:100] + "..."  # Store reference, not full data
        })

    return comments


def extract_idea(page, idea_url: str, idea_id: str) -> dict:
    """
    Extract full content from a single idea page.
    """
    print(f"  Extracting: {idea_url}")

    page.goto(idea_url, wait_until="domcontentloaded", timeout=60000)
    page.wait_for_timeout(5000)  # Wait for content to render

    # Extract metadata
    metadata = extract_metadata(page)
    metadata["id"] = idea_id
    metadata["url"] = idea_url
    metadata["extracted_at"] = datetime.now().isoformat()

    # Extract content images
    content_images = extract_content_images(page, idea_id)
    metadata["content_images"] = content_images
    metadata["has_content"] = len(content_images) > 0

    # Extract comments
    comments = extract_comments(page)
    metadata["comments"] = comments
    metadata["comment_count"] = len(comments)

    # Take full page screenshot as backup
    screenshot_path = RAW_DIR / f"{idea_id}_full.png"
    try:
        page.screenshot(path=str(screenshot_path), full_page=True)
        metadata["screenshot"] = str(screenshot_path)
    except:
        pass

    return metadata


def extract_all_ideas(ideas: list, max_ideas: int = None, delay: float = 2.0) -> list:
    """
    Extract content from all ideas in the list.

    Args:
        ideas: List of idea dicts with 'url' and 'id' keys
        max_ideas: Maximum number to process (None for all)
        delay: Delay between requests in seconds

    Returns:
        List of extracted idea data
    """
    ensure_dirs()
    extracted = []

    if max_ideas:
        ideas = ideas[:max_ideas]

    with VICSession(headless=True) as (browser, page):
        for i, idea in enumerate(tqdm(ideas, desc="Extracting ideas")):
            try:
                idea_data = extract_idea(page, idea["url"], idea["id"])
                extracted.append(idea_data)

                # Save individual result
                result_path = PARSED_DIR / f"{idea['id']}.json"
                with open(result_path, "w") as f:
                    json.dump(idea_data, f, indent=2)

                # Rate limiting
                if i < len(ideas) - 1:
                    time.sleep(delay)

            except Exception as e:
                print(f"  Error extracting {idea.get('url', 'unknown')}: {e}")
                continue

    return extracted


def load_ideas_index() -> list:
    """Load the ideas index file."""
    if INDEX_FILE.exists():
        with open(INDEX_FILE, "r") as f:
            data = json.load(f)
        return data.get("ideas", [])
    return []


def save_extraction_results(extracted: list) -> None:
    """Save all extraction results to a summary file."""
    summary_path = PARSED_DIR / "extraction_summary.json"

    summary = {
        "extracted_at": datetime.now().isoformat(),
        "total_extracted": len(extracted),
        "with_content": sum(1 for e in extracted if e.get("has_content")),
        "ideas": extracted
    }

    with open(summary_path, "w") as f:
        json.dump(summary, f, indent=2)

    print(f"Summary saved to {summary_path}")


def main():
    """Main extraction function."""
    print("VIC Content Extractor")
    print("=" * 50)

    # Load ideas index
    ideas = load_ideas_index()
    if not ideas:
        print("No ideas found in index. Run crawler first.")
        return

    print(f"Found {len(ideas)} ideas in index")

    # Extract content
    extracted = extract_all_ideas(ideas, max_ideas=10, delay=2.0)  # Start with 10

    # Save results
    save_extraction_results(extracted)

    print("\n" + "=" * 50)
    print(f"Extraction complete! Processed {len(extracted)} ideas")
    print(f"Content saved to: {PARSED_DIR}")


if __name__ == "__main__":
    main()
