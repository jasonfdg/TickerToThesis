#!/usr/bin/env python3
"""
Resume Pipeline from a specific iteration.
Useful when iterations 1-2 are complete and you want to continue to iteration 5.
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


class ResumablePipeline:
    """Pipeline that can resume from a specific iteration."""

    def __init__(self, ticker: str, preliminary_thinking: str):
        self.ticker = ticker.upper()
        self.preliminary_thinking = preliminary_thinking
        self.config = PipelineConfig()
        self.prompt_loader = PromptLoader()
        self.agent_runner = AgentRunner(self.config)
        self.report_saver = ReportSaver(self.ticker)

    def _build_analyst_system_prompt(self, type_id: int) -> str:
        """Build the system prompt for an analyst agent."""
        return f"""{self.prompt_loader.analyst_role}

---

## YOUR INVESTING PHILOSOPHY
{self.prompt_loader.investing_type(type_id)}

---

## YOUR FRAMEWORK
{self.prompt_loader.memo_engine}
"""

    def _build_analyst_refinement_user_prompt(
        self, type_id: int, iteration: int
    ) -> str:
        """Build user prompt for analyst refinement (iterations 2+)."""
        prev_iteration = iteration - 1

        # Load previous analyst report
        prev_report = self.report_saver.load_analyst_report(type_id, prev_iteration)
        if not prev_report:
            raise RuntimeError(f"Missing analyst report for type {type_id} v{prev_iteration}")

        # Load RD review of that report
        rd_review = self.report_saver.load_rd_review(type_id, prev_iteration)
        if not rd_review:
            raise RuntimeError(f"Missing RD review for type {type_id} v{prev_iteration}")

        return f"""## TICKER: {self.ticker}

## YOUR PREVIOUS ANALYSIS (v{prev_iteration})
{prev_report}

---

## RESEARCH DIRECTOR CRITIQUE OF YOUR v{prev_iteration} ANALYSIS
{rd_review}

---

## TASK
Produce your v{iteration} analysis incorporating the Research Director's feedback.
Address their critiques directly. Strengthen weak areas. Maintain your investing philosophy perspective.
"""

    def _build_rd_review_system_prompt(self) -> str:
        """Build system prompt for RD review."""
        return f"""{self.prompt_loader.rd_review_role}

---

## YOUR FRAMEWORK
{self.prompt_loader.memo_engine}
"""

    def _build_rd_review_user_prompt(self, type_id: int, iteration: int) -> str:
        """Build user prompt for RD review."""
        analyst_report = self.report_saver.load_analyst_report(type_id, iteration)
        if not analyst_report:
            raise RuntimeError(f"Missing analyst report for type {type_id} v{iteration}")

        type_name = INVESTING_TYPES[type_id]["name"]
        return f"""## ANALYST MEMO TO REVIEW

**Ticker:** {self.ticker}
**Analyst Type:** {type_name}
**Iteration:** v{iteration}

---

{analyst_report}

---

Please provide your Research Director critique following your framework.
"""

    async def _run_iteration(self, iteration: int) -> None:
        """Run a single debate iteration (analysts + RD reviews)."""
        logger.info(f"{'='*60}")
        logger.info(f"ITERATION {iteration}: Debate")
        logger.info(f"{'='*60}")

        # Phase 1: Analyst refinements
        logger.info(f"Phase 1: Running 6 analyst refinement calls...")
        analyst_calls = []
        for type_id in range(1, 7):
            call = AgentCall(
                role=AgentRole.ANALYST,
                system_prompt=self._build_analyst_system_prompt(type_id),
                user_prompt=self._build_analyst_refinement_user_prompt(type_id, iteration),
                investing_type_id=type_id,
                iteration=iteration,
            )
            analyst_calls.append(call)

        analyst_results = await self.agent_runner.run_analyst_batch(analyst_calls)

        # Save analyst reports
        for type_id, report in analyst_results.items():
            if report.is_success:
                self.report_saver.save_analyst_report(report)
                logger.info(f"  Analyst {type_id}: {report.token_usage.total_tokens:,} tokens")
            else:
                logger.error(f"  Analyst {type_id} failed: {report.error}")

        # Phase 2: RD reviews
        logger.info(f"Phase 2: Running 6 RD review calls...")
        rd_calls = []
        for type_id in range(1, 7):
            call = AgentCall(
                role=AgentRole.RD_REVIEW,
                system_prompt=self._build_rd_review_system_prompt(),
                user_prompt=self._build_rd_review_user_prompt(type_id, iteration),
                investing_type_id=type_id,
                iteration=iteration,
            )
            rd_calls.append(call)

        rd_results = await self.agent_runner.run_rd_review_batch(rd_calls)

        # Save RD reviews
        for type_id, report in rd_results.items():
            if report.is_success:
                self.report_saver.save_rd_review(report)
                logger.info(f"  RD Review {type_id}: {report.token_usage.total_tokens:,} tokens")
            else:
                logger.error(f"  RD Review {type_id} failed: {report.error}")

        # Calculate totals
        analyst_tokens = sum(r.token_usage.total_tokens for r in analyst_results.values())
        rd_tokens = sum(r.token_usage.total_tokens for r in rd_results.values())
        logger.info(f"Iteration {iteration} complete: {analyst_tokens + rd_tokens:,} total tokens")

    async def _run_synthesis(self) -> None:
        """Run final synthesis phase."""
        logger.info(f"{'='*60}")
        logger.info("SYNTHESIS: Research Director Final View")
        logger.info(f"{'='*60}")

        # Load all final reports
        final_iteration = self.config.num_iterations
        all_final_reports = self.report_saver.load_all_final_reports(final_iteration)
        logger.info(f"Loaded {len(all_final_reports)} final analyst reports (v{final_iteration})")

        if len(all_final_reports) < 4:
            raise RuntimeError(f"Need at least 4 final reports, got {len(all_final_reports)}")

        # Build prompts
        system_prompt = f"""{self.prompt_loader.rd_synthesis_role}

---

## YOUR FRAMEWORK
{self.prompt_loader.memo_engine}
"""

        combined_reports = "\n\n".join([
            f"## {INVESTING_TYPES[type_id]['name']} Analyst (v{final_iteration})\n\n{content}"
            for type_id, content in sorted(all_final_reports.items())
        ])

        user_prompt = f"""## ANALYST REPORTS TO SYNTHESIZE

{combined_reports}

---

Please synthesize these 6 analyst perspectives into a unified Research Director view.
"""

        # Run synthesis
        call = AgentCall(
            role=AgentRole.RD_SYNTHESIS,
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            iteration=1,
        )

        synthesis_report = await self.agent_runner.run_single(call)

        if not synthesis_report.is_success:
            raise RuntimeError(f"Synthesis failed: {synthesis_report.error}")

        self.report_saver.save_synthesis(synthesis_report)
        logger.info(f"Synthesis complete: {synthesis_report.token_usage.total_tokens:,} tokens")

        return synthesis_report.content

    async def _run_polish(self, synthesis_content: str) -> Path:
        """Run human-readable polish phase."""
        logger.info(f"{'='*60}")
        logger.info("POLISH: Human-Readable Output")
        logger.info(f"{'='*60}")

        polish_call = AgentCall(
            role=AgentRole.RD_SYNTHESIS,
            system_prompt=self.prompt_loader.human_readable_engine,
            user_prompt=f"""## RAW SYNTHESIS TO POLISH

{synthesis_content}

---

Please transform this raw synthesis into a polished, human-readable investment memo.
""",
            iteration=1,
            identifier="human_readable_polish",
        )

        polish_report = await self.agent_runner.run_single(polish_call)

        if not polish_report.is_success:
            raise RuntimeError(f"Polish failed: {polish_report.error}")

        # Save final memo
        final_path = get_final_memo_path(self.ticker)
        final_path.write_text(polish_report.content, encoding="utf-8")
        logger.info(f"Final memo saved: {final_path}")
        logger.info(f"Polish complete: {polish_report.token_usage.total_tokens:,} tokens")

        return final_path

    async def resume_from(self, start_iteration: int) -> Path:
        """
        Resume pipeline from a specific iteration.

        Args:
            start_iteration: The iteration to start from (e.g., 3 means run 3, 4, 5)

        Returns:
            Path to the final memo
        """
        logger.info(f"{'='*60}")
        logger.info(f"RESUMING PIPELINE FOR {self.ticker}")
        logger.info(f"Starting from iteration {start_iteration}, ending at {self.config.num_iterations}")
        logger.info(f"{'='*60}")

        # Run remaining iterations
        for iteration in range(start_iteration, self.config.num_iterations + 1):
            await self._run_iteration(iteration)

        # Run synthesis and polish
        synthesis_content = await self._run_synthesis()
        final_path = await self._run_polish(synthesis_content)

        logger.info(f"{'='*60}")
        logger.info("PIPELINE COMPLETE")
        logger.info(f"{'='*60}")

        return final_path


async def main():
    if len(sys.argv) < 3:
        print("Usage: python resume_pipeline.py <TICKER> <START_ITERATION> [PRELIMINARY_THINKING]")
        print("Example: python resume_pipeline.py WU 3 'Your thesis here...'")
        sys.exit(1)

    ticker = sys.argv[1]
    start_iteration = int(sys.argv[2])
    preliminary_thinking = sys.argv[3] if len(sys.argv) > 3 else "Resuming analysis..."

    pipeline = ResumablePipeline(ticker, preliminary_thinking)
    final_path = await pipeline.resume_from(start_iteration)
    print(f"\nSuccess! Final memo: {final_path}")


if __name__ == "__main__":
    asyncio.run(main())
