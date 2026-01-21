"""
Image Analyzer for VIC Research Reports
Uses Claude's vision to analyze report content images and extract patterns.

This script will:
1. Load extracted report images
2. Send each to Claude for analysis
3. Extract structural patterns, quality indicators, and content themes
4. Aggregate findings for instruction document generation
"""

import json
import base64
from pathlib import Path
from datetime import datetime

# Project paths
PROJECT_ROOT = Path(__file__).parent.parent
RAW_DIR = PROJECT_ROOT / "data" / "raw"
PARSED_DIR = PROJECT_ROOT / "data" / "parsed"
ANALYSIS_DIR = PROJECT_ROOT / "analysis" / "results"

ANALYSIS_DIR.mkdir(parents=True, exist_ok=True)


def load_extraction_summary() -> dict:
    """Load the extraction summary."""
    summary_path = PARSED_DIR / "extraction_summary.json"
    if summary_path.exists():
        with open(summary_path, "r") as f:
            return json.load(f)
    return {}


def get_reports_with_content() -> list:
    """Get list of reports that have content images."""
    summary = load_extraction_summary()
    ideas = summary.get("ideas", [])
    return [i for i in ideas if i.get("has_content") and i.get("content_images")]


def load_image_as_base64(image_path: str) -> str:
    """Load an image file and return base64 encoded string."""
    with open(image_path, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")


def create_analysis_prompt() -> str:
    """Create the prompt for analyzing a research report image."""
    return """Analyze this investment research report image and extract the following information in JSON format:

1. **structure**: Identify the sections present (e.g., "investment thesis", "company description", "valuation", "catalysts", "risks", "industry analysis")

2. **thesis_clarity**: Rate 1-10 how clearly the investment thesis is stated. Quote the main thesis if visible.

3. **variant_perception**: Does the report identify what the market is missing? What is it?

4. **financial_analysis**: What valuation methods or financial metrics are discussed?

5. **catalysts**: List any specific catalysts or timeline mentioned

6. **risks**: What risks are identified?

7. **quality_indicators**: Note any signs of high-quality analysis (primary research, differentiated data, etc.)

8. **writing_style**: Describe the tone and writing style (formal, conversational, data-heavy, etc.)

9. **key_quotes**: Extract 2-3 notable sentences that exemplify the writing quality

Return your analysis as valid JSON."""


def analyze_single_report(image_path: str, idea_metadata: dict) -> dict:
    """
    Analyze a single report image.

    Note: This function prepares the data for Claude analysis.
    The actual API call would be made by the calling script.
    """
    analysis_data = {
        "idea_id": idea_metadata.get("id"),
        "company": idea_metadata.get("company_name"),
        "ticker": idea_metadata.get("ticker"),
        "image_path": image_path,
        "image_base64": load_image_as_base64(image_path),
        "prompt": create_analysis_prompt(),
        "analyzed_at": datetime.now().isoformat(),
    }
    return analysis_data


def prepare_batch_analysis(max_reports: int = 50) -> list:
    """
    Prepare a batch of reports for Claude vision analysis.
    Returns list of analysis data objects ready for API calls.
    """
    reports = get_reports_with_content()[:max_reports]
    batch = []

    for report in reports:
        content_images = report.get("content_images", [])
        if content_images:
            # Use the first/main content image
            image_info = content_images[0]
            image_path = image_info.get("path")

            if Path(image_path).exists():
                analysis_data = analyze_single_report(image_path, report)
                batch.append(analysis_data)

    return batch


def save_analysis_batch(batch: list, batch_name: str = "batch") -> str:
    """Save prepared batch for later analysis."""
    output_path = ANALYSIS_DIR / f"{batch_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"

    # Don't include base64 in saved file (too large)
    batch_summary = []
    for item in batch:
        summary = {k: v for k, v in item.items() if k != "image_base64"}
        batch_summary.append(summary)

    with open(output_path, "w") as f:
        json.dump({
            "prepared_at": datetime.now().isoformat(),
            "total_reports": len(batch),
            "reports": batch_summary
        }, f, indent=2)

    return str(output_path)


def aggregate_analysis_results(results: list) -> dict:
    """
    Aggregate analysis results across multiple reports.
    Identifies common patterns, quality indicators, and structure.
    """
    aggregated = {
        "total_analyzed": len(results),
        "common_sections": {},
        "thesis_clarity_scores": [],
        "common_quality_indicators": [],
        "writing_style_patterns": [],
        "key_themes": [],
    }

    for result in results:
        if not result.get("analysis"):
            continue

        analysis = result["analysis"]

        # Count section occurrences
        for section in analysis.get("structure", []):
            aggregated["common_sections"][section] = \
                aggregated["common_sections"].get(section, 0) + 1

        # Collect thesis clarity scores
        if analysis.get("thesis_clarity"):
            aggregated["thesis_clarity_scores"].append(analysis["thesis_clarity"])

        # Collect quality indicators
        if analysis.get("quality_indicators"):
            aggregated["common_quality_indicators"].extend(
                analysis["quality_indicators"]
            )

        # Collect writing styles
        if analysis.get("writing_style"):
            aggregated["writing_style_patterns"].append(analysis["writing_style"])

    return aggregated


def main():
    """Main analysis preparation function."""
    print("VIC Report Analysis Preparation")
    print("=" * 50)

    # Check available reports
    reports = get_reports_with_content()
    print(f"Found {len(reports)} reports with content images")

    if not reports:
        print("No reports with content found. Run extraction first.")
        return

    # Prepare batch for analysis
    print(f"\nPreparing batch for Claude vision analysis...")
    batch = prepare_batch_analysis(max_reports=50)

    print(f"Prepared {len(batch)} reports for analysis")

    # Save batch metadata (without images)
    output_path = save_analysis_batch(batch)
    print(f"Batch metadata saved to: {output_path}")

    print("\nNext steps:")
    print("1. Use Claude's vision API to analyze each report image")
    print("2. Run aggregate_analysis_results() on the results")
    print("3. Generate instruction document from aggregated patterns")


if __name__ == "__main__":
    main()
