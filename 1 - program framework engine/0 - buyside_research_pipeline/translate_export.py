#!/usr/bin/env python3
"""
Translate & Export Investment Memos
===================================
Translate investment memos to Chinese and export to PDF.

Usage:
    python translate_export.py AAPL                      # Full pipeline (translate + PDF)
    python translate_export.py AAPL --pdf-only           # PDF only (no translation)
    python translate_export.py AAPL --translate-only     # Translation only (no PDF)
    python translate_export.py path/to/memo.md           # Direct path input
    python translate_export.py AAPL --en-pdf             # Also generate English PDF

Examples:
    # Translate latest GTLB memo to Chinese and generate Chinese PDF
    python translate_export.py GTLB

    # Generate PDFs for both English and Chinese versions
    python translate_export.py GTLB --en-pdf

    # Only translate (for review before PDF)
    python translate_export.py GTLB --translate-only
"""

import argparse
import asyncio
import logging
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional

from config import REPORT_OUTPUT, get_latest_output_dir
from translator import MemoTranslator, TranslationResult
from pdf_generator import MemoPDFGenerator, PDFResult

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)


def find_latest_memo(ticker: str) -> Optional[Path]:
    """Find the latest final memo for a ticker.

    Args:
        ticker: Stock ticker symbol.

    Returns:
        Path to the latest memo file, or None if not found.
    """
    ticker = ticker.upper()

    # Get the latest output directory for this ticker
    try:
        output_dir = get_latest_output_dir(ticker)
    except Exception:
        output_dir = None

    if output_dir is None or not output_dir.exists():
        # Search all output directories
        if not REPORT_OUTPUT.exists():
            return None

        # Find all directories for this ticker
        pattern = re.compile(rf"^{ticker}_V\d+_\d{{4}}-\d{{2}}-\d{{2}}$")
        ticker_dirs = [
            d for d in REPORT_OUTPUT.iterdir()
            if d.is_dir() and pattern.match(d.name)
        ]

        if not ticker_dirs:
            return None

        # Sort by version number (descending)
        ticker_dirs.sort(
            key=lambda d: int(re.search(r"_V(\d+)_", d.name).group(1)),
            reverse=True
        )
        output_dir = ticker_dirs[0]

    # Find final memo in directory
    memo_pattern = re.compile(rf"^{ticker}_memo_vF.*\.md$")
    memos = [f for f in output_dir.iterdir() if memo_pattern.match(f.name)]

    if not memos:
        return None

    # Return the most recent
    memos.sort(key=lambda f: f.stat().st_mtime, reverse=True)
    return memos[0]


async def run_pipeline(
    target: str,
    translate: bool = True,
    pdf_en: bool = False,
    pdf_zh: bool = True,
    output_dir: Optional[Path] = None,
) -> dict:
    """Run the translation and PDF export pipeline.

    Args:
        target: Ticker symbol or path to memo file.
        translate: Whether to translate to Chinese.
        pdf_en: Whether to generate English PDF.
        pdf_zh: Whether to generate Chinese PDF.
        output_dir: Output directory. If None, uses memo's directory.

    Returns:
        Dict with results for each operation.
    """
    results = {
        "source_memo": None,
        "translation": None,
        "pdf_en": None,
        "pdf_zh": None,
        "errors": [],
    }

    # Resolve target to file path
    target_path = Path(target)
    if target_path.exists() and target_path.is_file():
        memo_path = target_path
        logger.info(f"Using direct path: {memo_path}")
    else:
        # Treat as ticker
        memo_path = find_latest_memo(target)
        if memo_path is None:
            error = f"No memo found for ticker: {target}"
            logger.error(error)
            results["errors"].append(error)
            return results
        logger.info(f"Found memo: {memo_path}")

    results["source_memo"] = memo_path

    # Determine output directory
    if output_dir is None:
        output_dir = memo_path.parent

    # Initialize components
    translator = MemoTranslator() if translate else None
    pdf_gen = MemoPDFGenerator()

    # Step 1: Translate to Chinese
    chinese_memo_path = None
    if translate:
        try:
            logger.info("Translating to Chinese...")
            translation_result = await translator.translate_memo(memo_path)
            results["translation"] = translation_result
            chinese_memo_path = translation_result.target_path
            logger.info(f"Translation saved: {chinese_memo_path.name}")
        except Exception as e:
            error = f"Translation failed: {e}"
            logger.error(error)
            results["errors"].append(error)

    # Step 2: Generate English PDF (if requested)
    if pdf_en:
        try:
            logger.info("Generating English PDF...")
            en_pdf_path = output_dir / f"{memo_path.stem}.pdf"
            pdf_result = pdf_gen.generate_pdf(memo_path, en_pdf_path, lang="en")
            results["pdf_en"] = pdf_result
            logger.info(f"English PDF: {pdf_result.output_path.name}")
        except Exception as e:
            error = f"English PDF generation failed: {e}"
            logger.error(error)
            results["errors"].append(error)

    # Step 3: Generate Chinese PDF
    if pdf_zh and chinese_memo_path and chinese_memo_path.exists():
        try:
            logger.info("Generating Chinese PDF...")
            zh_pdf_path = output_dir / f"{chinese_memo_path.stem}.pdf"
            pdf_result = pdf_gen.generate_pdf(chinese_memo_path, zh_pdf_path, lang="zh-CN")
            results["pdf_zh"] = pdf_result
            logger.info(f"Chinese PDF: {pdf_result.output_path.name}")
        except Exception as e:
            error = f"Chinese PDF generation failed: {e}"
            logger.error(error)
            results["errors"].append(error)
    elif pdf_zh and not translate:
        # Look for existing Chinese memo (new naming: _EN -> _CN, or legacy _zh suffix)
        stem = memo_path.stem
        if stem.endswith("_EN"):
            zh_memo_path = memo_path.parent / f"{stem[:-3]}_CN.md"
        else:
            zh_memo_path = memo_path.parent / f"{stem}_zh.md"
        if zh_memo_path.exists():
            try:
                logger.info("Generating Chinese PDF from existing translation...")
                zh_pdf_path = output_dir / f"{zh_memo_path.stem}.pdf"
                pdf_result = pdf_gen.generate_pdf(zh_memo_path, zh_pdf_path, lang="zh-CN")
                results["pdf_zh"] = pdf_result
                logger.info(f"Chinese PDF: {pdf_result.output_path.name}")
            except Exception as e:
                error = f"Chinese PDF generation failed: {e}"
                logger.error(error)
                results["errors"].append(error)

    return results


def print_results(results: dict) -> None:
    """Print pipeline results summary."""
    print(f"\n{'='*60}")
    print("Translation & Export Results")
    print(f"{'='*60}")

    if results["source_memo"]:
        print(f"\nSource: {results['source_memo']}")

    if results["translation"]:
        tr = results["translation"]
        print(f"\nTranslation:")
        print(f"  Output: {tr.target_path}")
        print(f"  Tokens: {tr.input_tokens:,} in / {tr.output_tokens:,} out")

    if results["pdf_en"]:
        pdf = results["pdf_en"]
        print(f"\nEnglish PDF:")
        print(f"  Output: {pdf.output_path}")
        print(f"  Pages: {pdf.page_count}, Size: {pdf.file_size_kb:.1f} KB")

    if results["pdf_zh"]:
        pdf = results["pdf_zh"]
        print(f"\nChinese PDF:")
        print(f"  Output: {pdf.output_path}")
        print(f"  Pages: {pdf.page_count}, Size: {pdf.file_size_kb:.1f} KB")

    if results["errors"]:
        print(f"\nErrors:")
        for err in results["errors"]:
            print(f"  - {err}")

    print(f"\n{'='*60}")


def main():
    parser = argparse.ArgumentParser(
        description="Translate investment memos to Chinese and export to PDF.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "target",
        help="Ticker symbol (e.g., AAPL) or path to memo file",
    )
    parser.add_argument(
        "--translate-only",
        action="store_true",
        help="Only translate, skip PDF generation",
    )
    parser.add_argument(
        "--pdf-only",
        action="store_true",
        help="Only generate PDF, skip translation (uses existing _zh.md)",
    )
    parser.add_argument(
        "--en-pdf",
        action="store_true",
        help="Also generate English PDF",
    )
    parser.add_argument(
        "--output-dir", "-o",
        type=Path,
        help="Output directory (default: same as source memo)",
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Enable verbose logging",
    )

    args = parser.parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    # Determine what to do
    do_translate = not args.pdf_only
    do_pdf_zh = not args.translate_only
    do_pdf_en = args.en_pdf

    if args.pdf_only and args.translate_only:
        print("Error: Cannot use both --pdf-only and --translate-only")
        sys.exit(1)

    # Run pipeline
    try:
        results = asyncio.run(run_pipeline(
            target=args.target,
            translate=do_translate,
            pdf_en=do_pdf_en,
            pdf_zh=do_pdf_zh,
            output_dir=args.output_dir,
        ))
    except KeyboardInterrupt:
        print("\nCancelled.")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Pipeline failed: {e}")
        sys.exit(1)

    # Print results
    print_results(results)

    # Exit with error if any failures
    if results["errors"]:
        sys.exit(1)


if __name__ == "__main__":
    main()
