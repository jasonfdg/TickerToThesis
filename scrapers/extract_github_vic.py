"""
Extract VIC ideas from GitHub SQL dump to JSON format.
Parses PostgreSQL dump and outputs JSON files matching the existing structured/ format.
"""

import json
import re
from pathlib import Path
from datetime import datetime

PROJECT_ROOT = Path(__file__).parent.parent
SQL_DUMP = PROJECT_ROOT / "data" / "vic" / "github_dump" / "vic_database_dump.sql"
OUTPUT_DIR = PROJECT_ROOT / "data" / "vic" / "github_dump" / "extracted"
STRUCTURED_DIR = PROJECT_ROOT / "data" / "vic" / "structured"

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def parse_copy_block(sql_content: str, table_name: str) -> list[dict]:
    """Extract data from a COPY block in PostgreSQL dump."""

    # Define column names for each table
    columns = {
        "ideas": ["id", "link", "company_id", "user_id", "date", "is_short", "is_contest_winner"],
        "descriptions": ["idea_id", "description"],
        "catalyst": ["idea_id", "catalysts"],
        "companies": ["ticker", "company_name"],
        "users": ["user_link", "username"],
        "performance": ["idea_id", "nextDayOpen", "nextDayClose", "oneWeekClosePerf",
                       "twoWeekClosePerf", "oneMonthPerf", "threeMonthPerf", "sixMonthPerf",
                       "oneYearPerf", "twoYearPerf", "threeYearPerf", "fiveYearPerf"]
    }

    if table_name not in columns:
        return []

    # Find the COPY block - end marker is \. on its own line
    pattern = rf"COPY public\.{table_name} \([^)]+\) FROM stdin;\n(.*?)\n\\."
    match = re.search(pattern, sql_content, re.DOTALL)

    if not match:
        print(f"  Warning: No data found for table {table_name}")
        return []

    data = []
    lines = match.group(1).strip().split('\n')
    cols = columns[table_name]

    for line in lines:
        if not line or line.startswith('--'):
            continue

        # Split by tab, handling escaped characters
        values = line.split('\t')

        if len(values) != len(cols):
            continue

        row = {}
        for i, col in enumerate(cols):
            val = values[i] if i < len(values) else None
            # Handle NULL values
            if val == '\\N':
                val = None
            # Handle boolean
            elif val == 't':
                val = True
            elif val == 'f':
                val = False
            # Handle escaped newlines
            elif val:
                val = val.replace('\\n', '\n').replace('\\r', '\r')
            row[col] = val

        data.append(row)

    return data


def format_date(date_str: str) -> str:
    """Convert SQL timestamp to human-readable format."""
    if not date_str:
        return None
    try:
        dt = datetime.strptime(date_str, "%Y-%m-%d %H:%M:%S")
        return dt.strftime("%B %d, %Y")
    except:
        return date_str


def extract_username(user_path: str) -> str:
    """Extract username from user path like /member/username/123."""
    if not user_path:
        return None
    match = re.match(r"/member/([^/]+)/", user_path)
    return match.group(1) if match else user_path


def detect_position_type(description: str, catalyst: str = None) -> str:
    """Detect position type from content, as SQL is_short field has errors."""
    if not description:
        return "long"  # Default to long

    text = (description + " " + (catalyst or "")).lower()

    # Strong short indicators (high confidence)
    short_strong = [
        "short position", "recommend a short", "i am short", "shorting",
        "short this", "short recommendation", "recommend shorting",
        "short sell", "short the stock", "going short"
    ]

    # Strong long indicators (high confidence)
    long_strong = [
        "long position", "recommend a long", "i am long", "going long",
        "buy recommendation", "recommend buying", "recommend a buy",
        "long the stock", "bullish on"
    ]

    # Check strong indicators first
    short_strong_count = sum(1 for kw in short_strong if kw in text)
    long_strong_count = sum(1 for kw in long_strong if kw in text)

    if short_strong_count > long_strong_count:
        return "short"
    if long_strong_count > short_strong_count:
        return "long"

    # Weak indicators as tiebreaker
    short_weak = ["overvalued", "worth less", "decline", "downside target"]
    long_weak = ["undervalued", "worth more", "upside", "attractive valuation", "target price"]

    short_weak_count = sum(1 for kw in short_weak if kw in text)
    long_weak_count = sum(1 for kw in long_weak if kw in text)

    if short_weak_count > long_weak_count + 1:  # Need clear margin
        return "short"

    # Default to long (VIC is predominantly long ideas)
    return "long"


def main():
    print("=" * 60)
    print("  VIC GitHub SQL Dump Extractor")
    print("=" * 60)
    print()

    # Load existing IDs to avoid duplicates
    existing_ids = {f.stem for f in STRUCTURED_DIR.glob("*.json")}
    print(f"Found {len(existing_ids)} existing structured files to skip")

    # Read SQL dump
    print(f"Reading SQL dump: {SQL_DUMP}")
    with open(SQL_DUMP, "r", encoding="utf-8", errors="replace") as f:
        sql_content = f.read()
    print(f"  Loaded {len(sql_content):,} bytes")

    # Parse each table
    print("\nParsing tables...")

    ideas = parse_copy_block(sql_content, "ideas")
    print(f"  ideas: {len(ideas):,} rows")

    descriptions = parse_copy_block(sql_content, "descriptions")
    print(f"  descriptions: {len(descriptions):,} rows")

    catalysts = parse_copy_block(sql_content, "catalyst")
    print(f"  catalysts: {len(catalysts):,} rows")

    companies = parse_copy_block(sql_content, "companies")
    print(f"  companies: {len(companies):,} rows")

    users = parse_copy_block(sql_content, "users")
    print(f"  users: {len(users):,} rows")

    performance = parse_copy_block(sql_content, "performance")
    print(f"  performance: {len(performance):,} rows")

    # Build lookup tables
    print("\nBuilding lookup tables...")
    desc_map = {d["idea_id"]: d["description"] for d in descriptions}
    catalyst_map = {c["idea_id"]: c["catalysts"] for c in catalysts}
    company_map = {c["ticker"]: c["company_name"] for c in companies}
    user_map = {u["user_link"]: u["username"] for u in users}
    perf_map = {p["idea_id"]: p for p in performance}

    # Process ideas
    print(f"\nExtracting ideas to {OUTPUT_DIR}")
    extracted = 0
    skipped_duplicate = 0
    skipped_no_content = 0

    for idea in ideas:
        idea_id = idea["id"]

        # Skip if already exists
        if idea_id in existing_ids:
            skipped_duplicate += 1
            continue

        # Get description
        description = desc_map.get(idea_id)
        if not description:
            skipped_no_content += 1
            continue

        # Build JSON structure
        ticker = idea.get("company_id")
        user_path = idea.get("user_id")

        # Get catalyst for position detection
        catalyst = catalyst_map.get(idea_id)

        # Detect position type from content (SQL is_short field has errors)
        position_type = detect_position_type(description, catalyst)

        output = {
            "id": idea_id,
            "url": idea.get("link"),
            "company_name": company_map.get(ticker) if ticker else None,
            "ticker": ticker,
            "extracted_at": datetime.now().isoformat(),
            "author": user_map.get(user_path) or extract_username(user_path),
            "date": format_date(idea.get("date")),
            "position_type": position_type,
            "sql_is_short": idea.get("is_short"),  # Keep original for reference
            "is_contest_winner": idea.get("is_contest_winner", False),
            "description_text": description,
            "catalyst_text": catalyst,
            "has_content": True,
            "source": "github_dschonholtz_vic"
        }

        # Add performance data if available
        perf = perf_map.get(idea_id)
        if perf:
            output["performance"] = {
                "next_day_open": perf.get("nextDayOpen"),
                "next_day_close": perf.get("nextDayClose"),
                "one_week": perf.get("oneWeekClosePerf"),
                "two_week": perf.get("twoWeekClosePerf"),
                "one_month": perf.get("oneMonthPerf"),
                "three_month": perf.get("threeMonthPerf"),
                "six_month": perf.get("sixMonthPerf"),
                "one_year": perf.get("oneYearPerf"),
                "two_year": perf.get("twoYearPerf"),
                "three_year": perf.get("threeYearPerf"),
                "five_year": perf.get("fiveYearPerf"),
            }

        # Write JSON file
        output_path = OUTPUT_DIR / f"{idea_id}.json"
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(output, f, indent=2, ensure_ascii=False)

        extracted += 1

        if extracted % 1000 == 0:
            print(f"  Extracted {extracted:,} ideas...")

    # Summary
    print("\n" + "=" * 60)
    print("  EXTRACTION COMPLETE")
    print("=" * 60)
    print(f"  Extracted: {extracted:,}")
    print(f"  Skipped (duplicate): {skipped_duplicate:,}")
    print(f"  Skipped (no content): {skipped_no_content:,}")
    print(f"  Output: {OUTPUT_DIR}")
    print("=" * 60)


if __name__ == "__main__":
    main()
