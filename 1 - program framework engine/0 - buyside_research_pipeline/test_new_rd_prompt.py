#!/usr/bin/env python3
"""
Test script: Run new RD review prompt on WU analyst v1 reports.
Compares the new symmetric RD feedback against the original asymmetric feedback.
"""

import asyncio
import os
from pathlib import Path
from datetime import datetime
from anthropic import AsyncAnthropic
from dotenv import load_dotenv

# Load environment
load_dotenv()

# Paths
PROJECT_ROOT = Path("/Users/chaukam/developer/Analyst_framework_buildout")
FRAMEWORK_ENGINE = PROJECT_ROOT / "1 - program framework engine"
REPORT_OUTPUT = PROJECT_ROOT / "2 - report output"

# Prompt paths
RD_REVIEW_PATH = FRAMEWORK_ENGINE / "1 - agent_role md prompt" / "rd_review_prompt.md"
MEMO_ENGINE_PATH = FRAMEWORK_ENGINE / "3 - agent synthesis engine md prompt" / "buyside_memo_engine_v1.2.0.md"

# Analyst type mapping
INVESTING_TYPES = {
    1: {"name": "Quality Compounders", "short_name": "quality_compounder"},
    2: {"name": "Imaginative Growth", "short_name": "imaginative_growth"},
    3: {"name": "Fundamental Long-Short", "short_name": "fundamental_ls"},
    4: {"name": "Deep Value", "short_name": "deep_value"},
    5: {"name": "Event-Driven", "short_name": "event_driven"},
    6: {"name": "Macro-Tactical", "short_name": "macro_tactical"},
}


def load_prompt(path: Path) -> str:
    """Load a prompt file."""
    with open(path) as f:
        return f.read()


def load_analyst_report(ticker: str, type_id: int) -> str:
    """Load an analyst v1 report."""
    short_name = INVESTING_TYPES[type_id]["short_name"]
    path = REPORT_OUTPUT / ticker / "interim" / f"analyst_{short_name}_v1.md"
    with open(path) as f:
        return f.read()


def build_rd_system_prompt() -> str:
    """Build RD review system prompt."""
    rd_role = load_prompt(RD_REVIEW_PATH)
    memo_engine = load_prompt(MEMO_ENGINE_PATH)
    return f"""{rd_role}

---

## Memo Engine (Rubric & Standards)

{memo_engine}
"""


def build_rd_user_prompt(ticker: str, type_id: int, analyst_report: str) -> str:
    """Build RD review user prompt."""
    type_name = INVESTING_TYPES[type_id]["name"]
    return f"""## Task: Review {type_name} Analysis of {ticker} (Iteration 1)

### Analyst Report
{analyst_report}

### Instructions
1. Identify the analyst's position (Long/Bullish, Short/Bearish, or Pass)
2. Challenge the position using the direction-dependent framework
3. If passing, push them to take a side - "Pass is not a position"
4. Push on the tails - what's the 90th percentile outcome? The 10th?
5. Be constructive - every critique must include a path forward
6. Score the memo using the rubric dimensions

Your job is to SHARPEN, not to ERODE. A great thesis emerges STRONGER from your critique.
"""


async def run_rd_review(client: AsyncAnthropic, ticker: str, type_id: int) -> str:
    """Run a single RD review."""
    analyst_report = load_analyst_report(ticker, type_id)
    system_prompt = build_rd_system_prompt()
    user_prompt = build_rd_user_prompt(ticker, type_id, analyst_report)

    type_name = INVESTING_TYPES[type_id]["name"]
    print(f"  Running RD review for {type_name}...")

    response = await client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=4000,
        temperature=0.7,
        system=system_prompt,
        messages=[{"role": "user", "content": user_prompt}],
    )

    return response.content[0].text


async def main():
    """Run all 6 RD reviews and save results."""
    client = AsyncAnthropic()
    ticker = "WU"

    print(f"\n{'='*60}")
    print(f"Testing New Symmetric RD Prompt on {ticker} Analyst v1 Reports")
    print(f"{'='*60}\n")

    # Create output directory
    output_dir = REPORT_OUTPUT / ticker / "test_new_rd"
    output_dir.mkdir(parents=True, exist_ok=True)

    # Run all 6 reviews
    results = {}
    for type_id in range(1, 7):
        type_name = INVESTING_TYPES[type_id]["name"]
        short_name = INVESTING_TYPES[type_id]["short_name"]

        try:
            review = await run_rd_review(client, ticker, type_id)
            results[type_id] = review

            # Save individual review
            output_path = output_dir / f"new_rd_review_{short_name}_v1.md"
            with open(output_path, "w") as f:
                f.write(f"---\n")
                f.write(f"ticker: {ticker}\n")
                f.write(f"review_for: {type_name}\n")
                f.write(f"iteration: 1\n")
                f.write(f"prompt_version: symmetric_v1\n")
                f.write(f"timestamp: {datetime.now().isoformat()}\n")
                f.write(f"---\n\n")
                f.write(review)

            print(f"  ✓ Saved {type_name} review")

        except Exception as e:
            print(f"  ✗ Error for {type_name}: {e}")
            results[type_id] = f"ERROR: {e}"

    # Generate comparison summary
    print(f"\n{'='*60}")
    print("GENERATING COMPARISON SUMMARY")
    print(f"{'='*60}\n")

    summary_path = output_dir / "comparison_summary.md"
    with open(summary_path, "w") as f:
        f.write("# New vs Old RD Review Comparison\n\n")
        f.write(f"**Test Date:** {datetime.now().strftime('%Y-%m-%d %H:%M')}\n")
        f.write(f"**Ticker:** {ticker}\n\n")
        f.write("## Key Question: Does the new RD challenge 'Pass' conclusions?\n\n")

        for type_id in range(1, 7):
            type_name = INVESTING_TYPES[type_id]["name"]
            f.write(f"### {type_name}\n\n")

            if type_id in results and not results[type_id].startswith("ERROR"):
                # Extract key phrases
                review = results[type_id]

                # Check for pass-challenging language
                pass_challenges = [
                    "take a side" in review.lower(),
                    "pass is not a position" in review.lower(),
                    "at what price would you act" in review.lower(),
                    "why not" in review.lower() and ("buy" in review.lower() or "long" in review.lower()),
                ]

                if any(pass_challenges):
                    f.write("**✓ NEW: Challenges the 'Pass' conclusion**\n\n")
                else:
                    f.write("**? May not challenge 'Pass' directly**\n\n")

                # First 500 chars of review
                f.write("**Preview:**\n")
                f.write(f"```\n{review[:800]}...\n```\n\n")
            else:
                f.write(f"**Error:** {results.get(type_id, 'Unknown')}\n\n")

    print(f"✓ Summary saved to: {summary_path}")
    print(f"✓ Individual reviews saved to: {output_dir}/")
    print(f"\nDone! Review the files to compare old vs new RD feedback.")


if __name__ == "__main__":
    asyncio.run(main())
