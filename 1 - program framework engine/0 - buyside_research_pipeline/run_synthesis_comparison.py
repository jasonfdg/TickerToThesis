#!/usr/bin/env python3
"""
Compare synthesis quality between Opus and Gemini.
Uses the same analyst reports, runs synthesis with different providers.
"""

import asyncio
import logging
import sys
from pathlib import Path
from datetime import datetime

from dotenv import load_dotenv

_env_path = Path(__file__).parent / ".env"
if _env_path.exists():
    load_dotenv(_env_path)

from config import INVESTING_TYPES, PipelineConfig, REPORT_OUTPUT
from models import AgentRole, TokenUsage
from prompt_loader import PromptLoader
from agent_runner import AgentCall, MultiProviderRunner

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)


SYNTHESIS_PROVIDERS = {
    "opus": {"provider": "claude", "model": "opus"},
    "gemini": {"provider": "gemini", "model": "gemini-2.5-pro"},
}


def load_analyst_reports(source_dir: Path, iteration: int = 1) -> dict:
    """Load analyst reports from a comparison directory."""
    reports = {}
    interim_dir = source_dir / "interim"

    name_to_type = {
        "quality_compounder": 1,
        "imaginative_growth": 2,
        "fundamental_ls": 3,
        "deep_value": 4,
        "event_driven": 5,
        "macro_tactical": 6,
    }

    for name, type_id in name_to_type.items():
        file_path = interim_dir / f"analyst_{name}_v{iteration}.md"
        if file_path.exists():
            content = file_path.read_text(encoding="utf-8")
            # Strip YAML frontmatter
            if content.startswith("---"):
                parts = content.split("---", 2)
                if len(parts) >= 3:
                    content = parts[2].strip()
            reports[type_id] = content
            logger.info(f"  Loaded: {file_path.name}")

    return reports


async def run_synthesis_with_provider(
    ticker: str,
    reports: dict,
    provider_key: str,
    output_dir: Path,
) -> tuple[str, int, float]:
    """Run synthesis with a specific provider."""

    provider_config = SYNTHESIS_PROVIDERS[provider_key]
    prompt_loader = PromptLoader()
    config = PipelineConfig(multi_provider=True)
    runner = MultiProviderRunner(config)

    # Build prompts
    system_prompt = f"""{prompt_loader.rd_synthesis_role}

---

## YOUR FRAMEWORK
{prompt_loader.memo_engine}
"""

    combined_reports = "\n\n".join([
        f"## {INVESTING_TYPES[type_id]['name']} Analyst (v1)\n\n{content}"
        for type_id, content in sorted(reports.items())
    ])

    user_prompt = f"""## ANALYST REPORTS TO SYNTHESIZE

{combined_reports}

---

Please synthesize these 6 analyst perspectives into a unified, publication-ready Research Director memo following your framework.
"""

    logger.info(f"Running synthesis with {provider_key.upper()}...")
    start_time = datetime.now()

    # Create AgentCall with explicit provider/model
    call = AgentCall(
        role=AgentRole.RD_SYNTHESIS,
        system_prompt=system_prompt,
        user_prompt=user_prompt,
        iteration=1,
        identifier=f"synthesis_{provider_key}",
        provider=provider_config["provider"],
        model=provider_config["model"],
    )

    result = await runner.run_single(call)

    duration = (datetime.now() - start_time).total_seconds()

    if result.error:
        raise RuntimeError(f"Synthesis failed: {result.error}")

    content = result.content
    tokens = result.token_usage.total_tokens

    # Save output
    output_path = output_dir / f"synthesis_{provider_key}.md"
    output_path.write_text(content, encoding="utf-8")
    logger.info(f"  Saved: {output_path}")
    logger.info(f"  Tokens: {tokens:,}, Duration: {duration:.1f}s")

    return content, tokens, duration


async def main(ticker: str, source_provider: str = "sonnet"):
    """Compare synthesis between Opus and Gemini."""

    # Use Sonnet reports as source (factually correct)
    source_dir = REPORT_OUTPUT / f"{ticker}_comparison_{source_provider}"

    if not source_dir.exists():
        logger.error(f"Source directory not found: {source_dir}")
        logger.error(f"Run comparison test first: python run_provider_comparison.py {ticker} {source_provider}")
        return

    logger.info(f"Loading analyst reports from: {source_dir}")
    reports = load_analyst_reports(source_dir)

    if len(reports) < 6:
        logger.error(f"Expected 6 reports, got {len(reports)}")
        return

    # Create output directory
    output_dir = REPORT_OUTPUT / f"{ticker}_synthesis_comparison"
    output_dir.mkdir(parents=True, exist_ok=True)

    logger.info("=" * 60)
    logger.info(f"SYNTHESIS COMPARISON: {ticker}")
    logger.info(f"Source: {source_provider} analyst reports")
    logger.info(f"Output: {output_dir}")
    logger.info("=" * 60)

    results = {}

    for provider_key in ["opus", "gemini"]:
        try:
            content, tokens, duration = await run_synthesis_with_provider(
                ticker, reports, provider_key, output_dir
            )
            results[provider_key] = {
                "tokens": tokens,
                "duration": duration,
                "length": len(content),
            }
        except Exception as e:
            logger.error(f"{provider_key.upper()} failed: {e}")
            results[provider_key] = {"error": str(e)}

    # Summary
    logger.info("=" * 60)
    logger.info("COMPARISON SUMMARY")
    logger.info("=" * 60)
    for provider_key, data in results.items():
        if "error" in data:
            logger.info(f"  {provider_key.upper()}: FAILED - {data['error']}")
        else:
            logger.info(f"  {provider_key.upper()}: {data['tokens']:,} tokens, {data['duration']:.1f}s, {data['length']:,} chars")

    logger.info(f"\nOutputs saved to: {output_dir}")
    return output_dir


if __name__ == "__main__":
    ticker = sys.argv[1].upper() if len(sys.argv) > 1 else "GLXY"
    source = sys.argv[2].lower() if len(sys.argv) > 2 else "sonnet"

    asyncio.run(main(ticker, source))
