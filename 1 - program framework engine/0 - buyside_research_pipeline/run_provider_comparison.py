#!/usr/bin/env python3
"""
Provider Comparison Test
========================
Run a single iteration with all analysts using the same provider.
Useful for comparing output quality between Claude, OpenAI, and Gemini.

Usage:
    python run_provider_comparison.py TICKER PROVIDER [PRELIMINARY_THINKING]

    PROVIDER: sonnet | gemini | gpt4o

Examples:
    python run_provider_comparison.py GLXY sonnet "AI platform play"
    python run_provider_comparison.py GLXY gemini "AI platform play"
"""

import asyncio
import sys
import logging
from datetime import datetime
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)

# Provider configurations
PROVIDER_CONFIGS = {
    "sonnet": {"provider": "claude", "model": "sonnet"},
    "gemini": {"provider": "gemini", "model": "gemini-2.5-pro"},
    "gpt4o": {"provider": "openai", "model": "gpt-4o"},
}


def patch_config_for_provider(provider_key: str):
    """Patch the config module to use a single provider for all analysts."""
    import config

    if provider_key not in PROVIDER_CONFIGS:
        raise ValueError(f"Unknown provider: {provider_key}. Use: {list(PROVIDER_CONFIGS.keys())}")

    provider_config = PROVIDER_CONFIGS[provider_key]

    # Override all analyst providers
    for type_id in range(1, 7):
        config.ANALYST_PROVIDER_CONFIG[type_id] = provider_config.copy()

    # Also use same provider for RD review (for consistency)
    config.ROLE_PROVIDER_CONFIG["rd_review"] = provider_config.copy()

    logger.info(f"Patched config: All analysts using {provider_key} ({provider_config})")


def get_comparison_output_dir(ticker: str, provider_key: str) -> Path:
    """Get output directory for comparison test."""
    from config import REPORT_OUTPUT

    comparison_dir = REPORT_OUTPUT / f"{ticker}_comparison_{provider_key}"
    comparison_dir.mkdir(parents=True, exist_ok=True)
    (comparison_dir / "interim").mkdir(parents=True, exist_ok=True)
    return comparison_dir


async def run_single_iteration(ticker: str, provider_key: str, preliminary_thinking: str):
    """Run a single iteration comparison test."""
    from TickerToThesis import TickerToThesisPipeline
    from config import PipelineConfig
    import config

    # Patch config for this provider
    patch_config_for_provider(provider_key)

    # Create pipeline with 1 iteration
    pipeline_config = PipelineConfig(
        num_iterations=1,  # Only 1 iteration for comparison
        multi_provider=True,
        parallel_execution=False,  # Sequential for rate limit safety
    )

    # Override output paths to use comparison directory
    comparison_dir = get_comparison_output_dir(ticker, provider_key)

    # Monkey-patch the config functions to use comparison directory
    original_get_output_dir = config.get_output_dir
    original_get_interim_dir = config.get_interim_dir
    original_get_source_file_path = config.get_source_file_path
    original_get_synthesis_raw_path = config.get_synthesis_raw_path
    original_get_final_memo_path = config.get_final_memo_path

    config.get_output_dir = lambda t: comparison_dir
    config.get_interim_dir = lambda t: comparison_dir / "interim"
    config.get_source_file_path = lambda t: comparison_dir / f"{t}_webSource.json"
    config.get_synthesis_raw_path = lambda t: comparison_dir / f"{t}_synthesis_raw.md"
    config.get_final_memo_path = lambda t: comparison_dir / f"{t}_memo_vF.md"

    try:
        logger.info(f"=" * 60)
        logger.info(f"PROVIDER COMPARISON: {ticker} with {provider_key.upper()}")
        logger.info(f"Output: {comparison_dir}")
        logger.info(f"=" * 60)

        pipeline = TickerToThesisPipeline(
            ticker=ticker,
            preliminary_thinking=preliminary_thinking,
            config=pipeline_config,
        )

        start_time = datetime.now()
        await pipeline.run()
        duration = (datetime.now() - start_time).total_seconds()

        logger.info(f"=" * 60)
        logger.info(f"COMPARISON COMPLETE: {provider_key.upper()}")
        logger.info(f"Duration: {duration:.1f}s")
        logger.info(f"Output: {comparison_dir}")
        logger.info(f"=" * 60)

        return comparison_dir

    finally:
        # Restore original functions
        config.get_output_dir = original_get_output_dir
        config.get_interim_dir = original_get_interim_dir
        config.get_source_file_path = original_get_source_file_path
        config.get_synthesis_raw_path = original_get_synthesis_raw_path
        config.get_final_memo_path = original_get_final_memo_path


def main():
    if len(sys.argv) < 3:
        print(__doc__)
        sys.exit(1)

    ticker = sys.argv[1].upper()
    provider = sys.argv[2].lower()
    preliminary_thinking = sys.argv[3] if len(sys.argv) > 3 else "Evaluate this company."

    if provider not in PROVIDER_CONFIGS:
        print(f"Error: Unknown provider '{provider}'")
        print(f"Available: {list(PROVIDER_CONFIGS.keys())}")
        sys.exit(1)

    asyncio.run(run_single_iteration(ticker, provider, preliminary_thinking))

    print(f"\nSuccess! Output: {get_comparison_output_dir(ticker, provider)}")


if __name__ == "__main__":
    main()
