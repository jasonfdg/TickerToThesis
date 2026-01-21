#!/usr/bin/env python3
"""
Buyside Research Aggregator
Downloads and extracts high-quality buyside research from multiple sources.

Target: >100 extracted files with >50kb each
Quality gate: Score 6+ (top 25% quartile per memo engine v0.2.0)
"""

import sys
import argparse
from pathlib import Path
from datetime import datetime

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from scraper.sources.hindenburg import HindenburgSource
from scraper.sources.kerrisdale import KerrrisdaleSource
from scraper.sources.pershing_square import PershingSquareSource
from scraper.sources.tenx_ebitda import TenXEbitdaSource
from scraper.sources.berkshire import BerkshireSource
from scraper.sources.icahn import IcahnSource
from scraper.sources.buyside_digest import BuySideDigestSource
from scraper.sources.hedge_fund_alpha import HedgeFundAlphaSource
from scraper.sources.muddy_waters import MuddyWatersSource
from scraper.sources.sohn_conference import SohnConferenceSource
from scraper.sources.cornell_stock_pitch import CornellStockPitchSource
from scraper.sources.security_analysis_reddit import SecurityAnalysisRedditSource

EXTRACTED_DIR = PROJECT_ROOT / "data" / "buyside_research" / "extracted"


def check_progress():
    """Check current progress against target."""
    if not EXTRACTED_DIR.exists():
        return 0, 0

    files = list(EXTRACTED_DIR.glob("*.json"))
    total_files = len(files)

    # Count files > 50kb
    large_files = sum(1 for f in files if f.stat().st_size > 50 * 1024)

    return total_files, large_files


def print_status():
    """Print current status."""
    total, large = check_progress()
    print(f"\n{'='*60}")
    print(f"  PROGRESS STATUS")
    print(f"{'='*60}")
    print(f"  Total extracted files: {total}")
    print(f"  Files > 50kb: {large}")
    print(f"  Target: >100 files with >50kb")
    print(f"  Progress: {large}/100 ({large}%)")
    print(f"{'='*60}\n")
    return large >= 100


def run_all_sources(max_per_source: int = 30):
    """Run all source scrapers."""
    sources = [
        ("Hindenburg Research", HindenburgSource, 3.0),
        ("Kerrisdale Capital", KerrrisdaleSource, 3.0),
        ("Pershing Square", PershingSquareSource, 4.0),
        ("10x EBITDA", TenXEbitdaSource, 3.0),
        ("Berkshire Hathaway", BerkshireSource, 2.0),
        ("Carl Icahn", IcahnSource, 3.0),
        ("BuySide Digest", BuySideDigestSource, 3.0),
        ("Hedge Fund Alpha", HedgeFundAlphaSource, 3.0),
        ("Muddy Waters Research", MuddyWatersSource, 3.0),
        ("Sohn Conference", SohnConferenceSource, 3.0),
        ("Cornell Stock Pitch", CornellStockPitchSource, 3.0),
        ("r/SecurityAnalysis", SecurityAnalysisRedditSource, 3.0),
    ]

    total_success = 0
    total_failed = 0

    for name, source_class, delay in sources:
        print(f"\n{'#'*60}")
        print(f"  RUNNING: {name}")
        print(f"{'#'*60}")

        # Check if we've hit target
        _, large = check_progress()
        if large >= 100:
            print(f"\n  Target reached! Stopping early.")
            break

        try:
            scraper = source_class(delay=delay)
            success, failed = scraper.run(max_docs=max_per_source)
            total_success += success
            total_failed += failed
        except Exception as e:
            print(f"  ERROR running {name}: {e}")
            total_failed += 1

    return total_success, total_failed


def main():
    parser = argparse.ArgumentParser(description="Buyside Research Aggregator")
    parser.add_argument("--source", type=str, help="Run specific source only")
    parser.add_argument("--max", type=int, default=30, help="Max docs per source")
    parser.add_argument("--status", action="store_true", help="Show status only")
    parser.add_argument("--all", action="store_true", help="Run all sources")
    args = parser.parse_args()

    print(f"\n{'='*60}")
    print(f"  BUYSIDE RESEARCH AGGREGATOR")
    print(f"  Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*60}")

    if args.status:
        print_status()
        return

    # Show initial status
    print_status()

    if args.source:
        # Run specific source
        source_map = {
            "hindenburg": HindenburgSource,
            "kerrisdale": KerrrisdaleSource,
            "pershing": PershingSquareSource,
            "10xebitda": TenXEbitdaSource,
            "berkshire": BerkshireSource,
            "icahn": IcahnSource,
            "buyside_digest": BuySideDigestSource,
            "hedge_fund_alpha": HedgeFundAlphaSource,
            "muddy_waters": MuddyWatersSource,
            "sohn": SohnConferenceSource,
            "cornell": CornellStockPitchSource,
            "reddit": SecurityAnalysisRedditSource,
        }

        if args.source.lower() in source_map:
            source_class = source_map[args.source.lower()]
            scraper = source_class(delay=3.0)
            scraper.run(max_docs=args.max)
        else:
            print(f"Unknown source: {args.source}")
            print(f"Available: {', '.join(source_map.keys())}")
    else:
        # Run all sources
        success, failed = run_all_sources(max_per_source=args.max)

        print(f"\n{'='*60}")
        print(f"  FINAL RESULTS")
        print(f"{'='*60}")
        print(f"  Total extracted: {success}")
        print(f"  Total failed: {failed}")

    # Final status
    target_met = print_status()

    if target_met:
        print("\n  ✓ TARGET MET! >100 files with >50kb extracted.")
    else:
        print("\n  ✗ Target not yet met. Run again to continue.")


if __name__ == "__main__":
    main()
