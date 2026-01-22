#!/usr/bin/env python3
"""
Source Summary Model Benchmark
==============================
Compare Claude Haiku, GPT-4o-mini, and Gemini 2.5 Flash for source summary task.

Metrics:
- JSON validity rate
- Token usage & estimated cost
- Extraction quality (sources, thesis claims)
- Response time
"""

import asyncio
import json
import logging
import os
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

# Load environment variables from .env
from dotenv import load_dotenv
load_dotenv(Path(__file__).parent / ".env")

from providers import ProviderFactory

logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)


@dataclass
class BenchmarkResult:
    """Result of a single benchmark run."""
    provider: str
    model: str
    input_tokens: int
    output_tokens: int
    elapsed_seconds: float
    json_valid: bool
    sources_extracted: int
    thesis_claims_extracted: int
    error: Optional[str] = None

    @property
    def estimated_cost(self) -> float:
        """Estimate cost in dollars."""
        # Pricing per 1M tokens
        COSTS = {
            "haiku": (0.25, 1.25),        # Claude Haiku
            "gpt-4o-mini": (0.15, 0.60),  # GPT-4o-mini
            "gemini-2.5-flash": (0.075, 0.30),  # Gemini Flash
        }
        input_rate, output_rate = COSTS.get(self.model, (1.0, 1.0))
        return (self.input_tokens / 1_000_000 * input_rate +
                self.output_tokens / 1_000_000 * output_rate)


async def run_benchmark(
    factory: ProviderFactory,
    provider_type: str,
    model: str,
    system_prompt: str,
    user_prompt: str,
) -> BenchmarkResult:
    """Run a single benchmark iteration."""
    start_time = time.time()
    error = None
    json_valid = False
    sources_extracted = 0
    thesis_claims_extracted = 0
    input_tokens = 0
    output_tokens = 0

    try:
        response = await factory.generate(
            provider_type=provider_type,
            model=model,
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            max_tokens=8000,
            temperature=0.3,
        )

        input_tokens = response.token_usage.input_tokens
        output_tokens = response.token_usage.output_tokens

        # Check JSON validity
        try:
            content = response.content.strip()
            # Handle markdown code blocks
            if content.startswith("```"):
                lines = content.split("\n")
                content = "\n".join(lines[1:-1] if lines[-1].strip() == "```" else lines[1:])

            parsed = json.loads(content)
            json_valid = True

            # Count extractions
            if "sources" in parsed:
                sources_extracted = len(parsed["sources"])
            if "research_context" in parsed:
                thesis_claims_extracted = len(parsed["research_context"].get("thesis_points", []))

        except json.JSONDecodeError as e:
            json_valid = False
            error = f"JSON parse error: {str(e)[:100]}"

    except Exception as e:
        error = str(e)[:200]

    elapsed = time.time() - start_time

    return BenchmarkResult(
        provider=provider_type,
        model=model,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        elapsed_seconds=elapsed,
        json_valid=json_valid,
        sources_extracted=sources_extracted,
        thesis_claims_extracted=thesis_claims_extracted,
        error=error,
    )


def load_test_data() -> Tuple[str, Dict, str]:
    """Load test data from COIN run."""
    base_path = Path(__file__).parent.parent.parent / "2 - report output" / "COIN_V1_2026-01-21"

    # Load source file
    source_path = base_path / "COIN_webSource.json"
    with open(source_path) as f:
        current_sources = json.load(f)

    # Load an analyst report
    report_path = base_path / "interim" / "analyst_quality_compounder_v1.md"
    with open(report_path) as f:
        analyst_report = f.read()

    # Load prompt
    prompt_path = Path(__file__).parent.parent / "4 - source_summary_agent md prompt" / "source_summary_agent_v2.md"
    with open(prompt_path) as f:
        system_prompt = f.read()

    return system_prompt, current_sources, analyst_report


def build_user_prompt(current_sources: Dict, analyst_report: str) -> str:
    """Build the user prompt with extraction input."""
    # Simulate pre-extracted citations (simplified for benchmark)
    extractions = [{
        "analyst_type": 1,
        "iteration": 1,
        "sources": [
            {
                "url": "https://investor.coinbase.com/news/news-details/2026/Coinbase-Announces-Date-of-Fourth-Quarter-and-Full-Year-2025-Financial-Results/default.aspx",
                "title": "Coinbase Q4 2025 Earnings Announcement",
                "type": "company_ir",
                "summary": "Official Q4 2025 earnings date announcement",
                "context": "Referenced for earnings date"
            },
            {
                "url": "https://www.marketbeat.com/stocks/NASDAQ/COIN/earnings/",
                "title": "MarketBeat Consensus Estimates",
                "type": "sellside",
                "summary": "Analyst consensus: Q4 2025 EPS $1.04, FY2025 EPS $5.23",
                "context": "Earnings expectations"
            }
        ],
        "thesis_claims": [
            {
                "claim": "Coinbase faces regulatory existential risk from SEC enforcement",
                "stance": "bear",
                "evidence": "SEC Chair testimony on crypto regulation",
                "confidence": "high"
            },
            {
                "claim": "Fee compression inevitable as market matures (from 0.5-1.5% to <0.25%)",
                "stance": "bear",
                "evidence": "Comparison to equity trading fee collapse",
                "confidence": "medium"
            }
        ]
    }]

    input_data = {
        "ticker": "COIN",
        "current_sources": current_sources,
        "extractions": extractions,
        "iteration": 1
    }

    return json.dumps(input_data, indent=2)


async def main():
    """Run the benchmark."""
    print("=" * 60)
    print("SOURCE SUMMARY MODEL BENCHMARK")
    print("=" * 60)
    print()

    # Load test data
    print("Loading test data from COIN run...")
    try:
        system_prompt, current_sources, analyst_report = load_test_data()
        user_prompt = build_user_prompt(current_sources, analyst_report)
        print(f"  System prompt: {len(system_prompt):,} chars")
        print(f"  User prompt: {len(user_prompt):,} chars")
        print()
    except Exception as e:
        print(f"Error loading test data: {e}")
        return

    # Initialize providers
    factory = ProviderFactory()

    # Models to test
    models = [
        ("claude", "haiku", "Claude Haiku (current)"),
        ("openai", "gpt-4o-mini", "GPT-4o-mini"),
        ("gemini", "gemini-2.5-flash", "Gemini 2.5 Flash"),
    ]

    results: List[BenchmarkResult] = []

    for provider_type, model, display_name in models:
        print(f"Testing {display_name}...")
        try:
            result = await run_benchmark(
                factory, provider_type, model,
                system_prompt, user_prompt
            )
            results.append(result)

            status = "✓" if result.json_valid else "✗"
            print(f"  {status} JSON valid: {result.json_valid}")
            print(f"  Sources: {result.sources_extracted}, Thesis claims: {result.thesis_claims_extracted}")
            print(f"  Tokens: {result.input_tokens:,} in, {result.output_tokens:,} out")
            print(f"  Time: {result.elapsed_seconds:.1f}s")
            print(f"  Est. cost: ${result.estimated_cost:.4f}")
            if result.error:
                print(f"  Error: {result.error}")
            print()
        except Exception as e:
            print(f"  ERROR: {e}")
            print()

    # Summary
    print("=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print()
    print(f"{'Model':<25} {'Valid':<6} {'Sources':<8} {'Claims':<8} {'Time(s)':<8} {'Cost':>10}")
    print("-" * 70)

    for r in results:
        print(f"{r.model:<25} {'✓' if r.json_valid else '✗':<6} {r.sources_extracted:<8} {r.thesis_claims_extracted:<8} {r.elapsed_seconds:<8.1f} ${r.estimated_cost:>9.4f}")

    print()
    print("RECOMMENDATION:")
    valid_results = [r for r in results if r.json_valid]
    if valid_results:
        best = min(valid_results, key=lambda r: r.estimated_cost)
        print(f"  Winner: {best.model} (${best.estimated_cost:.4f}/call, {best.elapsed_seconds:.1f}s)")
    else:
        print("  No models produced valid JSON!")

    return results


if __name__ == "__main__":
    asyncio.run(main())
