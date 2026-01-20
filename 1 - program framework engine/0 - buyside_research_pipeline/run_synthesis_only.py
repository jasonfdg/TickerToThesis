#!/usr/bin/env python3
"""
Run only the synthesis and polish phases (for when iterations are already complete).
"""

import asyncio
import logging
import os
from pathlib import Path

from dotenv import load_dotenv

# Load .env
_env_path = Path(__file__).parent / ".env"
if _env_path.exists():
    load_dotenv(_env_path)

from agent_runner import AgentCall, AgentRunner
from config import INVESTING_TYPES, PipelineConfig, get_final_memo_path
from models import AgentRole
from prompt_loader import PromptLoader
from report_saver import ReportSaver

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)


async def run_synthesis(ticker: str, iteration: int = 2):
    """Run synthesis and polish for a ticker that has completed iterations."""

    config = PipelineConfig()
    prompt_loader = PromptLoader()
    agent_runner = AgentRunner(config)
    report_saver = ReportSaver(ticker)

    # Load final reports
    logger.info(f"Loading v{iteration} analyst reports...")
    all_final_reports = report_saver.load_all_final_reports(iteration)
    logger.info(f"Loaded {len(all_final_reports)} final analyst reports")

    if len(all_final_reports) < 4:
        raise RuntimeError(f"Need at least 4 final reports, got {len(all_final_reports)}")

    # Build prompts
    system_prompt = f"""{prompt_loader.rd_synthesis_role}

---

## YOUR FRAMEWORK
{prompt_loader.memo_engine}
"""

    combined_reports = "\n\n".join([
        f"## {INVESTING_TYPES[type_id]['name']} Analyst (v{iteration})\n\n{content}"
        for type_id, content in sorted(all_final_reports.items())
    ])

    user_prompt = f"""## ANALYST REPORTS TO SYNTHESIZE

{combined_reports}

---

Please synthesize these 6 analyst perspectives into a unified Research Director view following your framework.
"""

    # Run synthesis
    logger.info("Running synthesis...")
    call = AgentCall(
        role=AgentRole.RD_SYNTHESIS,
        system_prompt=system_prompt,
        user_prompt=user_prompt,
        iteration=1,
    )

    synthesis_report = await agent_runner.run_single(call)

    if not synthesis_report.is_success:
        raise RuntimeError(f"Synthesis failed: {synthesis_report.error}")

    report_saver.save_synthesis(synthesis_report)
    logger.info(f"Synthesis complete: {synthesis_report.token_usage.total_tokens:,} tokens")

    # Run human-readable polish
    logger.info("Running human-readable polish...")
    polish_system_prompt = f"""{prompt_loader.human_readable_engine}"""

    polish_call = AgentCall(
        role=AgentRole.RD_SYNTHESIS,
        system_prompt=polish_system_prompt,
        user_prompt=f"""## RAW SYNTHESIS TO POLISH

{synthesis_report.content}

---

Please transform this raw synthesis into a polished, human-readable investment memo.
""",
        iteration=1,
        identifier="human_readable_polish",
    )

    polish_report = await agent_runner.run_single(polish_call)

    if not polish_report.is_success:
        raise RuntimeError(f"Polish failed: {polish_report.error}")

    # Save final memo
    final_path = get_final_memo_path(ticker)
    final_path.write_text(polish_report.content, encoding="utf-8")
    logger.info(f"Final memo saved: {final_path}")
    logger.info(f"Polish complete: {polish_report.token_usage.total_tokens:,} tokens")

    return final_path


if __name__ == "__main__":
    import sys
    ticker = sys.argv[1] if len(sys.argv) > 1 else "WU"
    iteration = int(sys.argv[2]) if len(sys.argv) > 2 else 2

    result = asyncio.run(run_synthesis(ticker, iteration))
    print(f"\nSuccess! Final memo: {result}")
