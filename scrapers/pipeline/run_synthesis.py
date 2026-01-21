"""
VIC Memo Synthesis Runner
Processes JSON files iteratively to generate the Buyside Memo Engine instruction manual.
"""

import json
import os
import re
from pathlib import Path
from datetime import datetime
from collections import defaultdict

# Paths
PROJECT_ROOT = Path(__file__).parent.parent.parent
DATA_DIR = PROJECT_ROOT / "data" / "vic" / "github_dump" / "extracted"
OUTPUT_DIR = PROJECT_ROOT / "analysis" / "memo_synthesis" / "output"
PROMPT_FILE = PROJECT_ROOT / "analysis" / "memo_synthesis" / "SYNTHESIS_PROMPT.md"

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def load_json_file(filepath: Path) -> dict:
    """Load a single JSON file."""
    with open(filepath, 'r', encoding='utf-8') as f:
        return json.load(f)


def get_all_json_files() -> list:
    """Get all JSON files in the data directory."""
    return list(DATA_DIR.glob("*.json"))


def categorize_files(files: list) -> dict:
    """Categorize files into winners, shorts, and regular by year."""
    categories = {
        "winners": [],
        "shorts": [],
        "by_year": defaultdict(list)
    }

    for f in files:
        try:
            data = load_json_file(f)
            is_winner = data.get("is_contest_winner", False)
            is_short = data.get("position_type", "").lower() == "short"

            # Extract year from date
            date_str = data.get("date", "")
            year_match = re.search(r'\b(20\d{2}|19\d{2})\b', date_str)
            year = int(year_match.group(1)) if year_match else 0

            if is_winner:
                categories["winners"].append((f, year))
            if is_short:
                categories["shorts"].append((f, year))
            if not is_winner and not is_short:
                categories["by_year"][year].append(f)

        except Exception as e:
            print(f"Error processing {f}: {e}")
            continue

    return categories


def get_priority_files(categories: dict) -> list:
    """Get unique list of winner + short files."""
    winner_files = set(f for f, _ in categories["winners"])
    short_files = set(f for f, _ in categories["shorts"])
    return list(winner_files | short_files)


def get_remaining_files_by_year(categories: dict, priority_files: set) -> list:
    """Get remaining files sorted by year, excluding priority files."""
    remaining = []
    for year in sorted(categories["by_year"].keys()):
        for f in categories["by_year"][year]:
            if f not in priority_files:
                remaining.append((f, year))
    return remaining


def batch_files(files: list, batch_size: int) -> list:
    """Split files into batches."""
    return [files[i:i + batch_size] for i in range(0, len(files), batch_size)]


def extract_memo_content(filepath: Path) -> dict:
    """Extract relevant content from a memo JSON file."""
    data = load_json_file(filepath)
    return {
        "id": data.get("id", ""),
        "ticker": data.get("ticker", ""),
        "company_name": data.get("company_name", ""),
        "date": data.get("date", ""),
        "position_type": data.get("position_type", ""),
        "is_contest_winner": data.get("is_contest_winner", False),
        "author": data.get("author", ""),
        "description_text": data.get("description_text", ""),
        "catalyst_text": data.get("catalyst_text", ""),
    }


def analyze_memos(memos: list) -> dict:
    """Analyze a batch of memos to extract patterns."""
    analysis = {
        "total_count": len(memos),
        "winners_count": sum(1 for m in memos if m.get("is_contest_winner")),
        "shorts_count": sum(1 for m in memos if m.get("position_type", "").lower() == "short"),
        "longs_count": sum(1 for m in memos if m.get("position_type", "").lower() == "long"),
        "avg_description_length": 0,
        "years": defaultdict(int),
        "position_types": defaultdict(int),
        "thesis_patterns": [],
        "valuation_methods": [],
        "risk_patterns": [],
        "catalyst_patterns": [],
    }

    total_desc_len = 0
    for m in memos:
        desc = m.get("description_text", "") or ""
        total_desc_len += len(desc)

        # Year distribution
        date_str = m.get("date", "")
        year_match = re.search(r'\b(20\d{2}|19\d{2})\b', date_str)
        if year_match:
            analysis["years"][year_match.group(1)] += 1

        # Position type distribution
        pos = m.get("position_type", "unknown")
        analysis["position_types"][pos] += 1

    if memos:
        analysis["avg_description_length"] = total_desc_len // len(memos)

    return analysis


def generate_iteration_report(iteration: int, batch_info: dict, memos: list) -> str:
    """Generate a detailed report for this iteration."""
    analysis = analyze_memos(memos)

    report = f"""
## Iteration {iteration} Analysis Report

### Batch Information
- Files processed: {batch_info['count']}
- File type: {batch_info['type']}
- Date range: {batch_info.get('date_range', 'N/A')}

### Distribution Summary
- Total memos: {analysis['total_count']}
- Contest winners: {analysis['winners_count']}
- Short positions: {analysis['shorts_count']}
- Long positions: {analysis['longs_count']}
- Average description length: {analysis['avg_description_length']} characters

### Year Distribution
"""
    for year in sorted(analysis['years'].keys()):
        report += f"- {year}: {analysis['years'][year]}\n"

    return report


def main():
    """Main entry point."""
    print("VIC Memo Synthesis Runner")
    print("=" * 60)

    # Get all files
    print("Loading file list...")
    all_files = get_all_json_files()
    print(f"Found {len(all_files)} JSON files")

    # Categorize
    print("Categorizing files...")
    categories = categorize_files(all_files)
    print(f"  Winners: {len(categories['winners'])}")
    print(f"  Shorts: {len(categories['shorts'])}")

    # Get priority files
    priority_files = get_priority_files(categories)
    priority_set = set(priority_files)
    print(f"  Priority (union): {len(priority_files)}")

    # Get remaining by year
    remaining = get_remaining_files_by_year(categories, priority_set)
    print(f"  Remaining: {len(remaining)}")

    # Plan iterations
    print("\n" + "=" * 60)
    print("ITERATION PLAN:")
    print(f"  Iteration 1: {len(priority_files)} priority files (winners + shorts)")

    remaining_batches = batch_files(remaining, 500)
    for i, batch in enumerate(remaining_batches, start=2):
        years = set()
        for f, year in batch:
            years.add(year)
        year_range = f"{min(years)}-{max(years)}" if years else "N/A"
        print(f"  Iteration {i}: {len(batch)} files ({year_range})")

    total_iterations = 1 + len(remaining_batches)
    print(f"\n  TOTAL ITERATIONS: {total_iterations}")

    return {
        "priority_files": priority_files,
        "remaining_batches": remaining_batches,
        "categories": categories,
        "total_iterations": total_iterations
    }


if __name__ == "__main__":
    result = main()
