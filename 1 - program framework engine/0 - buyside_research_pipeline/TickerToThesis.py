#!/usr/bin/env python3
"""
TickerToThesis Pipeline
=======================
Main orchestrator for generating institutional-quality buyside research reports.

Coordinates 6 parallel analyst agents (each with a distinct investing philosophy)
through 5 debate iterations with a Research Director.

Usage:
    python TickerToThesis.py AAPL "preliminary thinking about the company..."
    python TickerToThesis.py --ticker AAPL --thinking "preliminary thinking..."
"""

import argparse
import asyncio
import json
import logging
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

# Load .env file from project root or pipeline directory
from dotenv import load_dotenv

# Try multiple locations for .env file
_env_locations = [
    Path(__file__).parent / ".env",  # Pipeline directory
    Path(__file__).parent.parent.parent / ".env",  # Project root
    Path.home() / ".anthropic" / ".env",  # User's anthropic config
]
for _env_path in _env_locations:
    if _env_path.exists():
        load_dotenv(_env_path)
        break

# Support both module and direct script execution
try:
    from .agent_runner import AgentCall, AgentRunner
    from .config import INVESTING_TYPES, PipelineConfig, get_final_memo_path
    from .models import AgentReport, AgentRole, IterationState, PipelineState, TokenUsage
    from .prompt_loader import PromptLoader
    from .report_saver import ReportSaver
    from .source_manager import SourceManager
except ImportError:
    from agent_runner import AgentCall, AgentRunner
    from config import INVESTING_TYPES, PipelineConfig, get_final_memo_path
    from models import AgentReport, AgentRole, IterationState, PipelineState, TokenUsage
    from prompt_loader import PromptLoader
    from report_saver import ReportSaver
    from source_manager import SourceManager

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)


class TickerToThesisPipeline:
    """
    Main pipeline orchestrator.

    Flow:
    1. Iteration 1 (Genesis): 6 parallel analysts → source update → 6 parallel RD reviews
    2. Iterations 2-5 (Debate): Analysts refine with RD feedback → RD sharpens critique
    3. Final: RD synthesis on all v5 reports → human readable polish
    """

    def __init__(
        self,
        ticker: str,
        preliminary_thinking: str,
        config: Optional[PipelineConfig] = None,
    ):
        self.ticker = ticker.upper()
        self.preliminary_thinking = preliminary_thinking
        self.config = config or PipelineConfig()

        # Initialize components
        self.prompt_loader = PromptLoader()
        self.agent_runner = AgentRunner(self.config)
        self.source_manager = SourceManager(self.ticker, self.prompt_loader)
        self.report_saver = ReportSaver(self.ticker)

        # Initialize state
        self.state = PipelineState(
            ticker=self.ticker,
            preliminary_thinking=self.preliminary_thinking,
        )

    def _build_analyst_system_prompt(self, type_id: int) -> str:
        """Build the system prompt for an analyst agent."""
        return f"""{self.prompt_loader.analyst_role}

---

## Your Investing Philosophy

{self.prompt_loader.investing_type(type_id)}

---

## Memo Engine (Structure & Standards)

{self.prompt_loader.memo_engine}
"""

    def _build_analyst_user_prompt_v1(self, type_id: int) -> str:
        """Build the user prompt for analyst iteration 1 (genesis)."""
        source_content = self.source_manager.get_source_content()

        return f"""## Task: Initial Analysis of {self.ticker}

### Preliminary Thinking (from user)
{self.preliminary_thinking}

### Source File
```json
{source_content}
```

### Instructions
1. Analyze {self.ticker} through your {self.prompt_loader.investing_type_name(type_id)} lens
2. Form a conviction-driven thesis - take a position
3. Follow the memo engine structure precisely
4. Cite sources from the source file AND conduct your own research
5. Include the Sources Used table at the end

This is iteration 1. Be bold. Form your initial view.
"""

    def _build_analyst_user_prompt_subsequent(
        self,
        type_id: int,
        iteration: int,
        previous_report: str,
        rd_feedback: str,
    ) -> str:
        """Build the user prompt for analyst iterations 2-5."""
        source_content = self.source_manager.get_source_content()

        return f"""## Task: Refine Your Analysis of {self.ticker} (Iteration {iteration})

### Your Previous Report (v{iteration - 1})
{previous_report}

### Research Director Feedback
{rd_feedback}

### Updated Source File
```json
{source_content}
```

### Instructions
1. Engage with the Research Director's critique
2. If their points land, update your analysis with evidence
3. If you disagree, defend your position with stronger evidence
4. Sharpen your thesis - more conviction, not less
5. Update the Sources Used table

Remember: A memo without a position is noise. Refine, don't retreat.
"""

    def _build_rd_review_system_prompt(self) -> str:
        """Build the system prompt for RD review agent."""
        return f"""{self.prompt_loader.rd_review_role}

---

## Memo Engine (Rubric & Standards)

{self.prompt_loader.memo_engine}
"""

    def _build_rd_review_user_prompt(
        self,
        type_id: int,
        iteration: int,
        analyst_report: str,
    ) -> str:
        """Build the user prompt for RD review."""
        type_name = self.prompt_loader.investing_type_name(type_id)

        return f"""## Task: Review {type_name} Analysis of {self.ticker} (Iteration {iteration})

### Analyst Report
{analyst_report}

### Instructions
1. Hunt for weaknesses - what's missing? What's assumed without evidence?
2. Challenge the thesis - what would make this analyst wrong?
3. Push on the tails - what's the 90th percentile outcome? The 10th?
4. Be constructive - every critique must include a path forward
5. Score the memo using the rubric dimensions

Your job is to sharpen, not to kill. Make this analyst better.
"""

    def _build_rd_synthesis_system_prompt(self) -> str:
        """Build the system prompt for RD synthesis."""
        return f"""{self.prompt_loader.rd_synthesis_role}

---

## Memo Engine (Structure & Standards)

{self.prompt_loader.memo_engine}
"""

    def _build_rd_synthesis_user_prompt(self, all_v5_reports: Dict[int, str]) -> str:
        """Build the user prompt for final RD synthesis."""
        reports_section = ""
        for type_id in range(1, 7):
            if type_id in all_v5_reports:
                type_name = self.prompt_loader.investing_type_name(type_id)
                reports_section += f"""
### {type_name} Analyst (Final Report)
{all_v5_reports[type_id]}

---
"""

        source_content = self.source_manager.get_source_content()

        return f"""## Task: Synthesize Final Investment View on {self.ticker}

You have received final reports from 6 analysts, each with a distinct investing philosophy.
Your job is to synthesize these into a single, decision-grade investment memo.

{reports_section}

### Complete Source File
```json
{source_content}
```

### Instructions
1. Identify the central tension across reports - where do they agree? Disagree?
2. Determine which assumptions are defensible
3. Form YOUR final view - don't split the difference
4. Articulate the variant perception: What does the market believe? Why are they wrong?
5. Rank your conviction: Is this "high conviction" or "worth monitoring"?
6. Include complete Sources Used table

Remember: If your conclusion is consensus, you've added nothing.
"""

    def _build_human_readable_system_prompt(self) -> str:
        """Build the system prompt for human readable polish."""
        return self.prompt_loader.human_readable_engine

    def _build_human_readable_user_prompt(self, synthesis_report: str) -> str:
        """Build the user prompt for human readable polish."""
        return f"""## Task: Polish the Final Memo for {self.ticker}

### Raw Synthesis
{synthesis_report}

### Instructions
Apply the Writing Craft Engine to transform this memo:

1. **Cut** - Remove 20-30% of words. Hunt redundancy, qualifiers, throat-clearing.
2. **Activate** - Convert passive to active voice. Transform nouns to verbs.
3. **Shorten** - Tighten every phrase and sentence.
4. **Structure** - Ensure proper paragraph breaks, table formatting, bullet structure.
5. **Impact** - Strong opening (no "In this memo..."), punchy closing.

Preserve: Thesis, evidence, logic, recommendations, Sources Used table.
Change: Sentences, paragraphs, words, readability.

Output the complete polished memo.
"""

    async def _run_iteration_1(self) -> None:
        """Run iteration 1 (genesis): Initial analyst reports and RD reviews."""
        logger.info(f"{'='*60}")
        logger.info(f"ITERATION 1: Genesis")
        logger.info(f"{'='*60}")

        iteration_state = self.state.iterations[1]
        iteration_state.mark_started()

        # Phase 1: Run 6 parallel analyst calls
        logger.info("Phase 1: Running 6 parallel analyst calls...")
        analyst_calls = []
        for type_id in range(1, 7):
            call = AgentCall(
                role=AgentRole.ANALYST,
                system_prompt=self._build_analyst_system_prompt(type_id),
                user_prompt=self._build_analyst_user_prompt_v1(type_id),
                investing_type_id=type_id,
                iteration=1,
            )
            analyst_calls.append(call)

        analyst_reports = await self.agent_runner.run_analyst_batch(analyst_calls)
        iteration_state.analyst_reports = analyst_reports

        # Save analyst reports
        for type_id, report in analyst_reports.items():
            if report.is_success:
                self.report_saver.save_analyst_report(report)
                logger.info(
                    f"  Analyst {type_id} ({self.prompt_loader.investing_type_name(type_id)}): "
                    f"{report.token_usage.total_tokens:,} tokens"
                )

        # Phase 2: Update source file (sequential, uses all reports)
        logger.info("Phase 2: Updating source file...")
        await self._update_sources_from_reports(analyst_reports, 1)
        iteration_state.source_updated = True

        # Phase 3: Run 6 parallel RD review calls
        logger.info("Phase 3: Running 6 parallel RD review calls...")
        rd_calls = []
        for type_id in range(1, 7):
            if type_id in analyst_reports and analyst_reports[type_id].is_success:
                call = AgentCall(
                    role=AgentRole.RD_REVIEW,
                    system_prompt=self._build_rd_review_system_prompt(),
                    user_prompt=self._build_rd_review_user_prompt(
                        type_id, 1, analyst_reports[type_id].content
                    ),
                    investing_type_id=type_id,
                    iteration=1,
                )
                rd_calls.append(call)

        rd_reviews = await self.agent_runner.run_rd_review_batch(rd_calls)
        iteration_state.rd_reviews = rd_reviews

        # Save RD reviews
        for type_id, review in rd_reviews.items():
            if review.is_success:
                self.report_saver.save_rd_review(review)
                logger.info(
                    f"  RD Review {type_id}: {review.token_usage.total_tokens:,} tokens"
                )

        iteration_state.mark_completed()
        logger.info(
            f"Iteration 1 complete: {iteration_state.total_token_usage.total_tokens:,} total tokens"
        )

    async def _run_iteration(self, iteration: int) -> None:
        """Run iterations 2-5: Debate loop."""
        logger.info(f"{'='*60}")
        logger.info(f"ITERATION {iteration}: Debate")
        logger.info(f"{'='*60}")

        iteration_state = self.state.iterations[iteration]
        iteration_state.mark_started()

        # Phase 1: Run 6 parallel analyst refinement calls
        logger.info(f"Phase 1: Running 6 parallel analyst refinement calls...")
        analyst_calls = []
        for type_id in range(1, 7):
            # Get previous report and RD feedback
            previous_report = self.report_saver.load_analyst_report(type_id, iteration - 1)
            rd_feedback = self.report_saver.load_rd_review(type_id, iteration - 1)

            if previous_report and rd_feedback:
                call = AgentCall(
                    role=AgentRole.ANALYST,
                    system_prompt=self._build_analyst_system_prompt(type_id),
                    user_prompt=self._build_analyst_user_prompt_subsequent(
                        type_id, iteration, previous_report, rd_feedback
                    ),
                    investing_type_id=type_id,
                    iteration=iteration,
                )
                analyst_calls.append(call)
            else:
                logger.warning(
                    f"  Missing data for type {type_id}: "
                    f"report={bool(previous_report)}, feedback={bool(rd_feedback)}"
                )

        analyst_reports = await self.agent_runner.run_analyst_batch(analyst_calls)
        iteration_state.analyst_reports = analyst_reports

        # Save analyst reports
        for type_id, report in analyst_reports.items():
            if report.is_success:
                self.report_saver.save_analyst_report(report)
                logger.info(
                    f"  Analyst {type_id}: {report.token_usage.total_tokens:,} tokens"
                )

        # Phase 2: Update source file
        logger.info("Phase 2: Updating source file...")
        await self._update_sources_from_reports(analyst_reports, iteration)
        iteration_state.source_updated = True

        # Phase 3: Run 6 parallel RD review calls
        logger.info("Phase 3: Running 6 parallel RD review calls...")
        rd_calls = []
        for type_id in range(1, 7):
            if type_id in analyst_reports and analyst_reports[type_id].is_success:
                call = AgentCall(
                    role=AgentRole.RD_REVIEW,
                    system_prompt=self._build_rd_review_system_prompt(),
                    user_prompt=self._build_rd_review_user_prompt(
                        type_id, iteration, analyst_reports[type_id].content
                    ),
                    investing_type_id=type_id,
                    iteration=iteration,
                )
                rd_calls.append(call)

        rd_reviews = await self.agent_runner.run_rd_review_batch(rd_calls)
        iteration_state.rd_reviews = rd_reviews

        # Save RD reviews
        for type_id, review in rd_reviews.items():
            if review.is_success:
                self.report_saver.save_rd_review(review)
                logger.info(f"  RD Review {type_id}: {review.token_usage.total_tokens:,} tokens")

        iteration_state.mark_completed()
        logger.info(
            f"Iteration {iteration} complete: "
            f"{iteration_state.total_token_usage.total_tokens:,} total tokens"
        )

    async def _run_synthesis(self) -> None:
        """Run final synthesis: RD synthesizes all v5 reports."""
        logger.info(f"{'='*60}")
        logger.info("SYNTHESIS: Research Director Final View")
        logger.info(f"{'='*60}")

        # Load all final reports (iteration matches config.num_iterations)
        final_iteration = self.config.num_iterations
        all_final_reports = self.report_saver.load_all_final_reports(final_iteration)
        logger.info(f"Loaded {len(all_final_reports)} final analyst reports (v{final_iteration})")

        if len(all_final_reports) < 4:
            raise RuntimeError(
                f"Need at least 4 final reports for synthesis, got {len(all_final_reports)}"
            )

        # Run synthesis
        call = AgentCall(
            role=AgentRole.RD_SYNTHESIS,
            system_prompt=self._build_rd_synthesis_system_prompt(),
            user_prompt=self._build_rd_synthesis_user_prompt(all_final_reports),
            iteration=1,
        )

        synthesis_report = await self.agent_runner.run_single(call)
        self.state.synthesis_report = synthesis_report

        if synthesis_report.is_success:
            self.report_saver.save_synthesis(synthesis_report)
            logger.info(f"Synthesis complete: {synthesis_report.token_usage.total_tokens:,} tokens")
        else:
            raise RuntimeError(f"Synthesis failed: {synthesis_report.error}")

    async def _run_human_readable_polish(self) -> None:
        """Run human readable polish pass on synthesis."""
        logger.info(f"{'='*60}")
        logger.info("POLISH: Human Readable Output")
        logger.info(f"{'='*60}")

        if not self.state.synthesis_report or not self.state.synthesis_report.is_success:
            raise RuntimeError("No synthesis report to polish")

        call = AgentCall(
            role=AgentRole.HUMAN_READABLE,
            system_prompt=self._build_human_readable_system_prompt(),
            user_prompt=self._build_human_readable_user_prompt(
                self.state.synthesis_report.content
            ),
            iteration=1,
        )

        final_report = await self.agent_runner.run_single(call)
        self.state.final_report = final_report

        if final_report.is_success:
            filepath = self.report_saver.save_final(final_report)
            logger.info(f"Final memo saved: {filepath}")
            logger.info(f"Polish complete: {final_report.token_usage.total_tokens:,} tokens")
        else:
            raise RuntimeError(f"Polish failed: {final_report.error}")

    async def _update_sources_from_reports(
        self,
        reports: Dict[int, AgentReport],
        iteration: int,
    ) -> None:
        """Update source file with sources from analyst reports."""
        # Combine all successful reports into one update
        combined_content = ""
        for type_id, report in reports.items():
            if report.is_success:
                type_name = self.prompt_loader.investing_type_name(type_id)
                combined_content += f"\n\n## {type_name} Analyst (Iteration {iteration})\n"
                combined_content += report.content

        if not combined_content:
            logger.warning("No successful reports to update sources from")
            return

        # Build source update prompt
        update_prompt = self.source_manager.build_source_update_prompt(
            combined_content,
            report_type="analyst_reports",
        )

        # Run source summary agent
        call = AgentCall(
            role=AgentRole.SOURCE_SUMMARY,
            system_prompt=self.prompt_loader.source_summary_agent,
            user_prompt=update_prompt,
            iteration=iteration,
        )

        source_response = await self.agent_runner.run_single(call)

        if source_response.is_success:
            self.source_manager.update_from_report(combined_content, source_response.content)
            logger.info("Source file updated")
        else:
            logger.warning(f"Source update failed: {source_response.error}")

    async def run(self) -> str:
        """
        Run the complete pipeline.

        Returns:
            Path to the final memo file
        """
        logger.info(f"{'='*60}")
        logger.info(f"TickerToThesis Pipeline: {self.ticker}")
        logger.info(f"{'='*60}")

        self.state.mark_started()

        try:
            # Pre-load all prompts
            prompt_stats = self.prompt_loader.load_all()
            logger.info(f"Loaded {len(prompt_stats)} prompts")

            # Run iteration 1 (genesis)
            await self._run_iteration_1()

            # Run subsequent iterations (debate)
            for iteration in range(2, self.config.num_iterations + 1):
                await self._run_iteration(iteration)

            # Run synthesis
            await self._run_synthesis()

            # Run human readable polish
            await self._run_human_readable_polish()

            self.state.mark_completed()

            # Save final state
            self.report_saver.save_pipeline_state(self.state)

            # Summary
            logger.info(f"{'='*60}")
            logger.info("PIPELINE COMPLETE")
            logger.info(f"{'='*60}")
            logger.info(f"Total tokens: {self.state.total_token_usage.total_tokens:,}")
            logger.info(f"Duration: {self.state.duration_seconds:.1f}s")
            logger.info(f"Final memo: {get_final_memo_path(self.ticker)}")

            return str(get_final_memo_path(self.ticker))

        except Exception as e:
            self.state.mark_failed(str(e))
            self.report_saver.save_pipeline_state(self.state)
            logger.error(f"Pipeline failed: {e}")
            raise


def main():
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Generate institutional-quality buyside research reports",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python -m buyside_research_pipeline.TickerToThesis AAPL "Apple seems undervalued..."
  python -m buyside_research_pipeline.TickerToThesis --ticker MSFT --thinking "Cloud growth..."
        """,
    )

    parser.add_argument(
        "ticker",
        nargs="?",
        help="Stock ticker symbol (e.g., AAPL, MSFT)",
    )
    parser.add_argument(
        "thinking",
        nargs="?",
        help="Preliminary thinking about the company",
    )
    parser.add_argument(
        "--ticker",
        "-t",
        dest="ticker_flag",
        help="Stock ticker symbol (alternative to positional)",
    )
    parser.add_argument(
        "--thinking",
        "-p",
        dest="thinking_flag",
        help="Preliminary thinking (alternative to positional)",
    )
    parser.add_argument(
        "--model",
        "-m",
        default="claude-sonnet-4-20250514",
        help="Claude model to use (default: claude-sonnet-4-20250514)",
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Enable verbose logging",
    )
    parser.add_argument(
        "--api-key",
        "-k",
        dest="api_key",
        help="Anthropic API key (or set ANTHROPIC_API_KEY env var)",
    )

    args = parser.parse_args()

    # Resolve ticker and thinking from either positional or flag args
    ticker = args.ticker or args.ticker_flag
    thinking = args.thinking or args.thinking_flag

    if not ticker:
        parser.error("ticker is required (positional or --ticker)")
    if not thinking:
        parser.error("preliminary thinking is required (positional or --thinking)")

    # Handle API key (loaded from .env, environment, or CLI)
    api_key = args.api_key or os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        env_path = Path(__file__).parent / ".env"
        parser.error(
            f"API key required. Options:\n"
            f"  1. Create {env_path} with: ANTHROPIC_API_KEY=sk-ant-...\n"
            f"  2. Set ANTHROPIC_API_KEY environment variable\n"
            f"  3. Pass --api-key YOUR_KEY"
        )
    # Set for the anthropic client to pick up
    os.environ["ANTHROPIC_API_KEY"] = api_key

    # Configure logging level
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    # Create config
    config = PipelineConfig(model=args.model, verbose=args.verbose)

    # Run pipeline
    pipeline = TickerToThesisPipeline(ticker, thinking, config)

    try:
        result = asyncio.run(pipeline.run())
        print(f"\nSuccess! Final memo: {result}")
        sys.exit(0)
    except KeyboardInterrupt:
        print("\nInterrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\nError: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
