#!/usr/bin/env python3
"""
Run comprehensive synthesis on ALL 60 reports + source file.
Generates a 400-600 line final decision document.
"""

import asyncio
import logging
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

# Load .env
_env_path = Path(__file__).parent / ".env"
if _env_path.exists():
    load_dotenv(_env_path)

from agent_runner import AgentCall, AgentRunner
from config import INVESTING_TYPES, PipelineConfig, get_final_memo_path, get_source_file_path
from models import AgentRole
from prompt_loader import PromptLoader
from report_saver import ReportSaver

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)


async def run_comprehensive_synthesis(ticker: str, num_iterations: int = 5):
    """
    Run synthesis on ALL reports (all iterations) + source file.

    Args:
        ticker: Stock ticker
        num_iterations: Number of iterations to include (default 5)
    """
    config = PipelineConfig()
    # Increase max tokens for longer output
    config.max_tokens = 16000

    prompt_loader = PromptLoader()
    agent_runner = AgentRunner(config)
    report_saver = ReportSaver(ticker)

    # Load ALL analyst reports (v1 through v5 for all 6 types)
    logger.info(f"Loading all analyst reports (v1-v{num_iterations} × 6 types)...")
    all_analyst_reports = []
    for iteration in range(1, num_iterations + 1):
        for type_id in range(1, 7):
            content = report_saver.load_analyst_report(type_id, iteration)
            if content:
                type_name = INVESTING_TYPES[type_id]['name']
                all_analyst_reports.append({
                    'type_id': type_id,
                    'type_name': type_name,
                    'iteration': iteration,
                    'content': content
                })

    logger.info(f"Loaded {len(all_analyst_reports)} analyst reports")

    # Load ALL RD reviews (v1 through v5 for all 6 types)
    logger.info(f"Loading all RD reviews (v1-v{num_iterations} × 6 types)...")
    all_rd_reviews = []
    for iteration in range(1, num_iterations + 1):
        for type_id in range(1, 7):
            content = report_saver.load_rd_review(type_id, iteration)
            if content:
                type_name = INVESTING_TYPES[type_id]['name']
                all_rd_reviews.append({
                    'type_id': type_id,
                    'type_name': type_name,
                    'iteration': iteration,
                    'content': content
                })

    logger.info(f"Loaded {len(all_rd_reviews)} RD reviews")

    # Load source file
    source_path = get_source_file_path(ticker)
    source_content = ""
    if source_path.exists():
        source_content = source_path.read_text(encoding='utf-8')
        logger.info(f"Loaded source file: {len(source_content):,} characters")
    else:
        logger.warning("No source file found")

    # Build comprehensive input
    logger.info("Building comprehensive synthesis input...")

    # Group by type for better organization
    synthesis_sections = []

    # Add source data first
    if source_content:
        synthesis_sections.append(f"""
# SOURCE DATA
{source_content[:50000]}  # Truncate if too long
""")

    # Add all analyst reports grouped by type
    for type_id in range(1, 7):
        type_name = INVESTING_TYPES[type_id]['name']
        type_reports = [r for r in all_analyst_reports if r['type_id'] == type_id]

        if type_reports:
            section = f"\n# {type_name.upper()} ANALYST - EVOLUTION ACROSS {len(type_reports)} ITERATIONS\n\n"
            for report in type_reports:
                section += f"## v{report['iteration']}\n{report['content']}\n\n---\n\n"
            synthesis_sections.append(section)

    # Add all RD reviews grouped by type
    for type_id in range(1, 7):
        type_name = INVESTING_TYPES[type_id]['name']
        type_reviews = [r for r in all_rd_reviews if r['type_id'] == type_id]

        if type_reviews:
            section = f"\n# RESEARCH DIRECTOR REVIEWS OF {type_name.upper()} ANALYST\n\n"
            for review in type_reviews:
                section += f"## Review of v{review['iteration']}\n{review['content']}\n\n---\n\n"
            synthesis_sections.append(section)

    combined_input = "\n".join(synthesis_sections)
    logger.info(f"Combined input: {len(combined_input):,} characters")

    # Build system prompt for comprehensive synthesis
    system_prompt = f"""{prompt_loader.rd_synthesis_role}

---

## YOUR FRAMEWORK
{prompt_loader.memo_engine}

---

## SPECIAL INSTRUCTIONS FOR THIS SYNTHESIS

You are receiving the COMPLETE debate history: all 5 iterations of analyst reports from 6 different investing philosophies, plus all 5 rounds of Research Director critiques for each.

This is a comprehensive synthesis task. Your output should be **400-600 lines** covering:

1. **Executive Summary** (20-30 lines)
   - Final investment decision with conviction level
   - Key thesis in 2-3 sentences
   - Primary variant view

2. **Debate Evolution Analysis** (60-80 lines)
   - How each analyst's view evolved across iterations
   - Key points of convergence and persistent disagreements
   - Which critiques drove the most significant thesis changes

3. **Multi-Lens Thesis Synthesis** (80-100 lines)
   - Quality Compounder perspective: key insights and blind spots
   - Imaginative Growth perspective: key insights and blind spots
   - Fundamental L/S perspective: key insights and blind spots
   - Deep Value perspective: key insights and blind spots
   - Event-Driven perspective: key insights and blind spots
   - Macro-Tactical perspective: key insights and blind spots

4. **Evidence Assessment** (60-80 lines)
   - What we know with high confidence (primary sources)
   - What we infer with medium confidence (logical deduction)
   - What remains speculation (assumptions requiring validation)
   - Key data gaps that would change the thesis

5. **Valuation Synthesis** (50-70 lines)
   - Range of valuations across methodologies
   - Key assumptions driving differences
   - Probability-weighted fair value
   - Entry/exit price discipline

6. **Risk Framework** (50-70 lines)
   - Risks by probability and impact
   - Kill conditions with specific triggers
   - Hedging considerations
   - Scenario analysis (bull/base/bear)

7. **Catalyst Timeline** (30-40 lines)
   - Observable catalysts with timing
   - Information triggers for position changes
   - Monitoring checklist

8. **Final Decision Framework** (40-50 lines)
   - Position recommendation with sizing
   - Entry/scaling/exit rules
   - Conviction assessment
   - What would change our mind

Be thorough, analytical, and evidence-based. Reference specific points from the debate where analysts disagreed or evolved their views.
"""

    user_prompt = f"""## COMPREHENSIVE SYNTHESIS REQUEST FOR {ticker}

You have the complete 5-iteration debate history below. Synthesize ALL perspectives into a definitive Research Director view.

Remember: Output should be 400-600 lines covering all sections specified in your instructions.

---

{combined_input}

---

Please provide your comprehensive synthesis following the framework above.
"""

    # Run synthesis
    logger.info("Running comprehensive synthesis (this may take a while)...")
    call = AgentCall(
        role=AgentRole.RD_SYNTHESIS,
        system_prompt=system_prompt,
        user_prompt=user_prompt,
        iteration=1,
        identifier="comprehensive_synthesis",
    )

    synthesis_report = await agent_runner.run_single(call)

    if not synthesis_report.is_success:
        raise RuntimeError(f"Synthesis failed: {synthesis_report.error}")

    # Save raw synthesis
    synthesis_path = report_saver.output_dir / f"{ticker}_comprehensive_synthesis_raw.md"
    synthesis_path.write_text(synthesis_report.content, encoding='utf-8')
    logger.info(f"Saved comprehensive synthesis: {synthesis_path}")
    logger.info(f"Synthesis complete: {synthesis_report.token_usage.total_tokens:,} tokens")

    # Count lines
    line_count = len(synthesis_report.content.split('\n'))
    logger.info(f"Synthesis output: {line_count} lines")

    # Run human-readable polish
    logger.info("Running human-readable polish...")
    polish_call = AgentCall(
        role=AgentRole.RD_SYNTHESIS,
        system_prompt=f"""{prompt_loader.human_readable_engine}

## SPECIAL INSTRUCTIONS

You are polishing a comprehensive 400-600 line investment synthesis.
Maintain the full depth and detail - do NOT summarize or shorten significantly.
Focus on:
- Clear section headers and formatting
- Readable prose while preserving analytical depth
- Professional buyside memo style
- Preserving all key insights, numbers, and recommendations

The output should remain comprehensive (350-500 lines minimum).
""",
        user_prompt=f"""## COMPREHENSIVE SYNTHESIS TO POLISH

{synthesis_report.content}

---

Please transform this into a polished, human-readable investment memo while preserving its comprehensive depth.
""",
        iteration=1,
        identifier="comprehensive_polish",
    )

    polish_report = await agent_runner.run_single(polish_call)

    if not polish_report.is_success:
        raise RuntimeError(f"Polish failed: {polish_report.error}")

    # Save final memo
    final_path = report_saver.output_dir / f"{ticker}_comprehensive_memo_vF.md"
    final_path.write_text(polish_report.content, encoding='utf-8')
    logger.info(f"Final comprehensive memo saved: {final_path}")
    logger.info(f"Polish complete: {polish_report.token_usage.total_tokens:,} tokens")

    # Count lines
    final_line_count = len(polish_report.content.split('\n'))
    logger.info(f"Final output: {final_line_count} lines")

    return final_path


if __name__ == "__main__":
    ticker = sys.argv[1] if len(sys.argv) > 1 else "WU"
    iterations = int(sys.argv[2]) if len(sys.argv) > 2 else 5

    result = asyncio.run(run_comprehensive_synthesis(ticker, iterations))
    print(f"\nSuccess! Comprehensive memo: {result}")
