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
    from .agent_runner import AgentCall, AgentRunner, MultiProviderRunner
    from .citation_extractor import CitationExtractor, extract_citations_from_reports
    from .config import INVESTING_TYPES, PipelineConfig, get_final_memo_path, get_final_pdf_path, clear_output_dir_cache
    from .models import AgentReport, AgentRole, IterationState, PipelineState, TokenUsage
    from .prompt_loader import PromptLoader
    from .progress_tracker import ProgressTracker, PhaseType
    from .report_saver import ReportSaver
    from .source_manager import SourceManager
    from .translate_export import run_pipeline as run_translate_export
except ImportError:
    from agent_runner import AgentCall, AgentRunner, MultiProviderRunner
    from citation_extractor import CitationExtractor, extract_citations_from_reports
    from config import INVESTING_TYPES, PipelineConfig, get_final_memo_path, get_final_pdf_path, clear_output_dir_cache
    from models import AgentReport, AgentRole, IterationState, PipelineState, TokenUsage
    from prompt_loader import PromptLoader
    from progress_tracker import ProgressTracker, PhaseType
    from report_saver import ReportSaver
    from source_manager import SourceManager
    from translate_export import run_pipeline as run_translate_export

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

        # Use MultiProviderRunner for parallel multi-provider execution
        if self.config.multi_provider:
            self.agent_runner = MultiProviderRunner(self.config)
            logger.info("Using MultiProviderRunner (Claude/GPT-4o/Gemini/Perplexity)")
        else:
            self.agent_runner = AgentRunner(self.config)
            logger.info("Using AgentRunner (Claude only)")

        self.source_manager = SourceManager(self.ticker, self.prompt_loader)
        self.report_saver = ReportSaver(self.ticker)

        # Initialize state
        self.state = PipelineState(
            ticker=self.ticker,
            preliminary_thinking=self.preliminary_thinking,
        )

        # Initialize progress tracker
        self.progress = ProgressTracker(
            ticker=self.ticker,
            num_iterations=self.config.num_iterations,
            num_analysts=len(INVESTING_TYPES),
            provider_factory=getattr(self.agent_runner, 'provider_factory', None),
            log_file=str(self.config.log_dir / f"{self.ticker}_progress.log") if self.config.log_dir else None,
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

    def _build_analyst_user_prompt_v1(self, type_id: int, use_filtered_sources: bool = True) -> str:
        """Build the user prompt for analyst iteration 1 (genesis)."""
        # Use filtered sources to reduce token count (~30-50% reduction)
        if use_filtered_sources:
            source_content = self.source_manager.get_filtered_sources_for_analyst(type_id)
        else:
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
        use_filtered_sources: bool = True,
    ) -> str:
        """Build the user prompt for analyst iterations 2-5."""
        # Use filtered sources to reduce token count (~30-50% reduction)
        if use_filtered_sources:
            source_content = self.source_manager.get_filtered_sources_for_analyst(type_id)
        else:
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

**STEP 1: Respond to Research Director Critique (REQUIRED)**

Before writing your updated report, you MUST explicitly address each point from the Research Director's feedback. This creates accountability and visibility into your analytical evolution.

Begin your response with:

---
## Response to Research Director Critique

For EACH specific critique or question from the Research Director:

### Critique: "[Quote the exact critique or question]"
**Verdict:** Accept / Reject / Partially Accept
**Response:** [1-2 sentences explaining how this changes or doesn't change your analysis]
**Evidence:** [Cite new sources or reasoning that supports your response]

[Repeat for each RD point]

### What I Got Wrong in v{iteration - 1} (if applicable)
[List specific errors or blind spots you're correcting]

---

**STEP 2: Write Updated Report**

After completing your Response section, write your complete updated report following the memo engine structure. Your updated analysis should reflect the conclusions from Step 1.

**Key principles:**
- If RD critique lands, update your analysis with evidence
- If you disagree, defend your position with stronger evidence
- Sharpen your thesis - more conviction, not less
- Update the Sources Used table

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
        previous_rd_feedback: Optional[str] = None,
    ) -> str:
        """Build the user prompt for RD review."""
        type_name = self.prompt_loader.investing_type_name(type_id)

        # Build engagement assessment section for iterations 2+
        engagement_section = ""
        if iteration > 1 and previous_rd_feedback:
            engagement_section = f"""
### Your Previous Feedback (v{iteration - 1})
{previous_rd_feedback}

### STEP 1: Engagement Assessment (REQUIRED for Iterations 2+)

Before reviewing the current report, assess how well the analyst engaged with your previous feedback.

Complete this assessment:

---
## Engagement Assessment

| RD Critique (v{iteration - 1}) | Addressed? | Quality |
|--------------------------------|------------|---------|
| [Quote your specific critique] | ✅ / ⚠️ / ❌ | [Brief quality assessment] |
| [Next critique] | ✅ / ⚠️ / ❌ | [Brief quality assessment] |

**Legend:** ✅ = Addressed substantively, ⚠️ = Partial/superficial, ❌ = Ignored

| Engagement Metric | Score (1-10) |
|-------------------|--------------|
| Response Completeness | Did they address each point? |
| Response Depth | Substantive or superficial? |
| Evidence Support | Did they add new evidence? |
| Intellectual Honesty | Did they acknowledge valid critiques? |

**Overall Engagement Score:** X/10
**Quality:** Thorough / Adequate / Superficial / Dismissive

---

### STEP 2: Current Report Review

"""

        base_instructions = f"""## Task: Review {type_name} Analysis of {self.ticker} (Iteration {iteration})

### Analyst Report
{analyst_report}
{engagement_section}
### Instructions
1. Hunt for weaknesses - what's missing? What's assumed without evidence?
2. Challenge the thesis - what would make this analyst wrong?
3. Push on the tails - what's the 90th percentile outcome? The 10th?
4. Be constructive - every critique must include a path forward
5. Score the memo using the rubric dimensions

Your job is to sharpen, not to kill. Make this analyst better.
"""
        return base_instructions

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

    def _build_source_scout_system_prompt(self) -> str:
        """Build the system prompt for web research agent."""
        return f"""{self.prompt_loader.source_scout_agent}

---

## Memo Engine (Evidence Standards)

{self.prompt_loader.memo_engine}
"""

    def _build_source_scout_user_prompt(
        self,
        iteration: int,
        rd_reviews: Dict[int, AgentReport],
    ) -> str:
        """Build the user prompt for web research agent."""
        source_content = self.source_manager.get_source_content()

        # Extract RD feedback for each analyst type
        rd_feedback_section = ""
        for type_id in range(1, 7):
            if type_id in rd_reviews and rd_reviews[type_id].is_success:
                type_name = self.prompt_loader.investing_type_name(type_id)
                rd_feedback_section += f"""
### Research Director Feedback for {type_name} Analyst
{rd_reviews[type_id].content}

---
"""

        return f"""## Task: Web Research for {self.ticker} — Iteration {iteration}

### Company
- **Ticker**: {self.ticker}
- **Iteration**: {iteration} of {self.config.num_iterations}

### Research Director Feedback (All Analyst Types)
The Research Director has reviewed each analyst's report. Extract research questions from their feedback and find evidence.

{rd_feedback_section}

### Current Source File
```json
{source_content}
```

### Instructions
1. **Extract Research Questions**: Identify specific questions, gaps, or verification requests from RD feedback
2. **Prioritize Primary Sources**: Hunt for Glassdoor, customer reviews, GitHub activity, Reddit threads, insider transactions
3. **Verify Claims**: When RD questions a claim, search for evidence that supports OR refutes it
4. **Document Gaps**: If you can't find evidence for something, note it explicitly
5. **Output Format**: Follow the web research report template with JSON source additions

Focus on finding evidence that will sharpen the next iteration of analyst work.
"""

    async def _run_source_scout(self, iteration: int, rd_reviews: Dict[int, AgentReport]) -> None:
        """Run web research agent with fallback chain for robustness.

        Fallback order: Perplexity → Gemini → Claude
        Each provider has different web search capabilities.
        """
        logger.info(f"Phase 4: Running web research agent...")

        # Fallback chain: try each provider in order until one succeeds
        fallback_providers = [
            ("perplexity", "sonar"),   # Primary: Best web search
            ("gemini", "gemini-2.0-flash"),  # Secondary: Good web capabilities
            ("claude", "sonnet"),       # Tertiary: Fallback using knowledge
        ]

        source_scout_report = None
        system_prompt = self._build_source_scout_system_prompt()
        user_prompt = self._build_source_scout_user_prompt(iteration, rd_reviews)

        for provider, model in fallback_providers:
            try:
                call = AgentCall(
                    role=AgentRole.SOURCE_SCOUT,
                    system_prompt=system_prompt,
                    user_prompt=user_prompt,
                    iteration=iteration,
                    identifier=f"source_scout_iter{iteration}_{provider}",
                    provider=provider,
                    model=model,
                )

                source_scout_report = await self.agent_runner.run_single(call)

                if source_scout_report.is_success:
                    logger.info(f"  Web Research ({provider}): {source_scout_report.token_usage.total_tokens:,} tokens")
                    break
                else:
                    logger.warning(f"  Web Research failed with {provider}: {source_scout_report.error}")

            except Exception as e:
                logger.warning(f"  Web Research exception with {provider}: {e}")
                continue

        # Store in iteration state
        if source_scout_report:
            self.state.iterations[iteration].source_scout_report = source_scout_report

            if source_scout_report.is_success:
                self.report_saver.save_source_scout(source_scout_report, iteration)
                # Update source file with web research findings
                await self._update_sources_from_source_scout(source_scout_report, iteration)
            else:
                logger.error("  Web Research failed with all providers")
        else:
            logger.error("  Web Research: No report generated (all providers failed)")

    async def _update_sources_from_source_scout(
        self,
        source_scout_report: AgentReport,
        iteration: int,
    ) -> bool:
        """Update source file with findings from web research agent."""
        if not source_scout_report.is_success:
            return False

        # Build source update prompt from web research findings
        update_prompt = self.source_manager.build_source_update_prompt(
            source_scout_report.content,
            report_type="source_scout",
        )

        # Run source summary agent to merge findings
        call = AgentCall(
            role=AgentRole.SOURCE_SUMMARY,
            system_prompt=self.prompt_loader.source_summary_agent,
            user_prompt=update_prompt,
            iteration=iteration,
            identifier=f"source_update_source_scout_iter{iteration}",
        )

        source_response = await self.agent_runner.run_single(call)

        if not source_response.is_success:
            logger.warning(f"Source summary agent failed for web research: {source_response.error}")
            return False

        update_success = self.source_manager.update_from_report(
            source_scout_report.content,
            source_response.content
        )

        if update_success:
            logger.info(f"  Source file updated from web research (iteration {iteration})")
            return True

        logger.warning(f"  Source file update from web research failed (iteration {iteration})")
        return False

    async def _run_initial_source_scout(self) -> None:
        """Run source scout to gather baseline data before iteration 1.

        This establishes foundational data (price, filings, earnings, news)
        so analysts don't hallucinate outdated information in iteration 1.
        """
        logger.info("Running initial source scout to establish baseline data...")

        system_prompt = self._build_source_scout_system_prompt()
        user_prompt = f"""## Task: Initial Data Collection for {self.ticker}

### Company
- **Ticker**: {self.ticker}

### User's Research Focus
{self.preliminary_thinking}

### Instructions
Gather baseline data to ground analyst work:
1. Current stock price, 52-week range, market cap
2. Latest SEC filings (10-K, 10-Q dates, recent 8-Ks)
3. Most recent earnings call date and key highlights
4. Top 3-5 recent news items
5. Analyst consensus (if available)

Output using Source Scout format with JSON source additions.
"""

        # Use same fallback chain as regular source scout
        fallback_providers = [
            ("perplexity", "sonar"),
            ("gemini", "gemini-2.0-flash"),
            ("claude", "sonnet"),
        ]

        for provider, model in fallback_providers:
            try:
                call = AgentCall(
                    role=AgentRole.SOURCE_SCOUT,
                    system_prompt=system_prompt,
                    user_prompt=user_prompt,
                    iteration=0,
                    identifier=f"initial_scout_{provider}",
                    provider=provider,
                    model=model,
                )
                report = await self.agent_runner.run_single(call)

                if report.is_success:
                    logger.info(f"  Initial scout ({provider}): {report.token_usage.total_tokens:,} tokens")
                    # Save the initial scout report
                    self.report_saver.save_initial_scout(report)
                    # Update source file with findings
                    await self._update_sources_from_source_scout(report, 0)
                    return
                else:
                    logger.warning(f"  Initial scout failed with {provider}: {report.error}")

            except Exception as e:
                logger.warning(f"  Initial scout exception with {provider}: {e}")
                continue

        logger.error("Initial source scout failed with all providers")

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

        # Phase 2 & 3: Run source update AND RD reviews in parallel
        # Source update doesn't affect RD reviews (they review analyst reports, not sources)
        logger.info("Phase 2+3: Updating sources AND running RD reviews in parallel...")

        # Build RD review calls
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

        # Run both in parallel - source update doesn't block RD reviews
        source_task = asyncio.create_task(
            self._update_sources_from_reports(analyst_reports, 1)
        )
        rd_task = asyncio.create_task(
            self.agent_runner.run_rd_review_batch(rd_calls)
        )

        # Wait for both to complete
        source_updated, rd_reviews = await asyncio.gather(source_task, rd_task)
        iteration_state.source_updated = source_updated
        iteration_state.rd_reviews = rd_reviews

        # Save RD reviews
        for type_id, review in rd_reviews.items():
            if review.is_success:
                self.report_saver.save_rd_review(review)
                logger.info(
                    f"  RD Review {type_id}: {review.token_usage.total_tokens:,} tokens"
                )

        # Phase 4: Run web research to gather evidence for next iteration
        await self._run_source_scout(1, rd_reviews)

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

        # Validate all 6 analysts have data before proceeding
        if len(analyst_calls) < 6:
            missing_types = [t for t in range(1, 7) if not any(c.investing_type_id == t for c in analyst_calls)]
            raise RuntimeError(
                f"Cannot proceed with iteration {iteration}: missing reports for analyst types {missing_types}. "
                f"Expected 6 analysts, got {len(analyst_calls)}. "
                f"Check interim/ directory for missing analyst_*_v{iteration-1}.md or rd_review_*_v{iteration-1}.md files."
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

        # Phase 2 & 3: Run source update AND RD reviews in parallel
        # Source update doesn't affect RD reviews (they review analyst reports, not sources)
        logger.info("Phase 2+3: Updating sources AND running RD reviews in parallel...")

        # Build RD review calls
        rd_calls = []
        for type_id in range(1, 7):
            if type_id in analyst_reports and analyst_reports[type_id].is_success:
                # Load previous RD feedback for engagement assessment
                previous_rd_feedback = self.report_saver.load_rd_review(type_id, iteration - 1)
                call = AgentCall(
                    role=AgentRole.RD_REVIEW,
                    system_prompt=self._build_rd_review_system_prompt(),
                    user_prompt=self._build_rd_review_user_prompt(
                        type_id, iteration, analyst_reports[type_id].content,
                        previous_rd_feedback=previous_rd_feedback
                    ),
                    investing_type_id=type_id,
                    iteration=iteration,
                )
                rd_calls.append(call)

        # Run both in parallel - source update doesn't block RD reviews
        source_task = asyncio.create_task(
            self._update_sources_from_reports(analyst_reports, iteration)
        )
        rd_task = asyncio.create_task(
            self.agent_runner.run_rd_review_batch(rd_calls)
        )

        # Wait for both to complete
        source_updated, rd_reviews = await asyncio.gather(source_task, rd_task)
        iteration_state.source_updated = source_updated
        iteration_state.rd_reviews = rd_reviews

        # Save RD reviews
        for type_id, review in rd_reviews.items():
            if review.is_success:
                self.report_saver.save_rd_review(review)
                logger.info(f"  RD Review {type_id}: {review.token_usage.total_tokens:,} tokens")

        # Phase 4: Run web research to gather evidence for next iteration
        # Skip on final iteration since there's no next iteration to inform
        if iteration < self.config.num_iterations:
            await self._run_source_scout(iteration, rd_reviews)

        iteration_state.mark_completed()
        logger.info(
            f"Iteration {iteration} complete: "
            f"{iteration_state.total_token_usage.total_tokens:,} total tokens"
        )

    async def _run_synthesis(self) -> None:
        """Run final synthesis: RD synthesizes all v5 reports.

        Uses rd_synthesis_prompt_v2 which combines synthesis + polish in one pass.
        Gemini is used for this step (configured in ROLE_PROVIDER_CONFIG).
        The output is saved directly as the final memo - no separate polish step.
        """
        logger.info(f"{'='*60}")
        logger.info("SYNTHESIS: Research Director Final View (1-step with Gemini)")
        logger.info(f"{'='*60}")

        # Load all final reports (iteration matches config.num_iterations)
        final_iteration = self.config.num_iterations
        all_final_reports = self.report_saver.load_all_final_reports(final_iteration)
        logger.info(f"Loaded {len(all_final_reports)} final analyst reports (v{final_iteration})")

        if len(all_final_reports) < 4:
            raise RuntimeError(
                f"Need at least 4 final reports for synthesis, got {len(all_final_reports)}"
            )

        # Run synthesis (uses Gemini via ROLE_PROVIDER_CONFIG)
        call = AgentCall(
            role=AgentRole.RD_SYNTHESIS,
            system_prompt=self._build_rd_synthesis_system_prompt(),
            user_prompt=self._build_rd_synthesis_user_prompt(all_final_reports),
            iteration=1,
        )

        synthesis_report = await self.agent_runner.run_single(call)
        self.state.synthesis_report = synthesis_report
        # Store as final_report too since synthesis now produces the final output
        self.state.final_report = synthesis_report

        if synthesis_report.is_success:
            # Only save final memo (synthesis v2 includes polish, no need for raw)
            filepath = self.report_saver.save_final(synthesis_report, lang="EN")
            logger.info(f"Synthesis complete: {synthesis_report.token_usage.total_tokens:,} tokens")
            logger.info(f"Final memo saved: {filepath}")
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
            filepath = self.report_saver.save_final(final_report, lang="EN")
            logger.info(f"Final memo saved: {filepath}")
            logger.info(f"Polish complete: {final_report.token_usage.total_tokens:,} tokens")
        else:
            raise RuntimeError(f"Polish failed: {final_report.error}")

    async def _run_pdf_export(self) -> dict:
        """Generate translated Chinese version and PDFs (EN + CN).

        Returns:
            Dict with results from translate_export pipeline.
        """
        logger.info(f"{'='*60}")
        logger.info("PDF EXPORT: Generating EN and CN PDFs")
        logger.info(f"{'='*60}")

        memo_path = get_final_memo_path(self.ticker, lang="EN")

        if not memo_path.exists():
            logger.error(f"Final memo not found: {memo_path}")
            return {"errors": ["Final memo not found"]}

        try:
            results = await run_translate_export(
                target=str(memo_path),
                translate=True,   # Translate to Chinese
                pdf_en=True,      # Generate English PDF
                pdf_zh=True,      # Generate Chinese PDF
            )

            if results.get("pdf_en"):
                logger.info(f"English PDF: {results['pdf_en'].output_path.name}")
            if results.get("pdf_zh"):
                logger.info(f"Chinese PDF: {results['pdf_zh'].output_path.name}")
            if results.get("translation"):
                logger.info(f"Chinese memo: {results['translation'].target_path.name}")

            if results.get("errors"):
                for err in results["errors"]:
                    logger.warning(f"PDF export warning: {err}")

            return results

        except Exception as e:
            logger.error(f"PDF export failed: {e}")
            return {"errors": [str(e)]}

    async def _update_sources_from_reports(
        self,
        reports: Dict[int, AgentReport],
        iteration: int,
        max_retries: int = 2,
        use_v2: bool = True,
    ) -> bool:
        """
        Update source file with sources from analyst reports.

        V2 Flow (default):
        1. Pre-extract citations using CitationExtractor
        2. Build slim structured prompt
        3. Try Haiku first (fast, cheap)
        4. Escalate to Sonnet if thesis extraction fails

        Args:
            reports: Dict of analyst reports by type_id
            iteration: Current iteration number
            max_retries: Number of retries if source update fails
            use_v2: Use v2 flow with pre-extraction (default True)

        Returns:
            True if source file was updated successfully
        """
        if not use_v2:
            return await self._update_sources_from_reports_v1(reports, iteration, max_retries)

        # V2 Flow: Pre-extract citations
        report_contents = {
            type_id: report.content
            for type_id, report in reports.items()
            if report.is_success
        }

        if not report_contents:
            logger.warning("No successful reports to update sources from")
            return False

        # Pre-extract citations and thesis claims
        extractor = CitationExtractor()
        extractions = []
        for type_id, content in report_contents.items():
            extraction = extractor.extract_from_report(content, type_id, iteration)
            extractions.append(extraction.to_dict())

        total_sources = sum(len(e["sources"]) for e in extractions)
        total_claims = sum(len(e["thesis_claims"]) for e in extractions)
        logger.info(
            f"Pre-extracted: {total_sources} sources, {total_claims} thesis claims "
            f"from {len(report_contents)} reports"
        )

        # Build slim prompt with extractions
        update_prompt = self.source_manager.build_slim_source_update_prompt(
            extractions, iteration
        )

        # Try with source_summary_agent_v2
        success = await self._run_source_update_v2(
            update_prompt, iteration, extractions, max_retries
        )

        if success:
            return True

        # Fallback to v1 if v2 fails completely
        logger.warning("V2 source update failed, falling back to v1...")
        return await self._update_sources_from_reports_v1(reports, iteration, max_retries)

    async def _run_source_update_v2(
        self,
        update_prompt: str,
        iteration: int,
        extractions: List[Dict],
        max_retries: int = 2,
    ) -> bool:
        """
        Run source update with v2 agent and optional model escalation.

        Args:
            update_prompt: Structured prompt for v2 agent
            iteration: Current iteration number
            extractions: Pre-extracted data for validation
            max_retries: Number of retries

        Returns:
            True if update succeeded
        """
        # Try Haiku first (fast, cheap)
        models_to_try = [
            ("claude", "haiku"),
            ("claude", "sonnet"),  # Escalate if Haiku fails
        ]

        for provider, model in models_to_try:
            for attempt in range(max_retries + 1):
                call = AgentCall(
                    role=AgentRole.SOURCE_SUMMARY,
                    system_prompt=self.prompt_loader.source_summary_agent_v2,
                    user_prompt=update_prompt,
                    iteration=iteration,
                    identifier=f"source_update_v2_iter{iteration}_{model}_attempt{attempt}",
                    provider=provider,
                    model=model,
                )

                source_response = await self.agent_runner.run_single(call)

                if not source_response.is_success:
                    logger.warning(f"Source summary v2 ({model}) failed: {source_response.error}")
                    continue

                # Try to update from the response
                update_success = self.source_manager.update_from_report(
                    "",  # No raw report content needed for v2
                    source_response.content
                )

                if not update_success:
                    logger.warning(f"Source update parsing failed ({model})")
                    continue

                # Validate thesis extraction quality
                data = self.source_manager.load_source_file()
                if self.source_manager.validate_thesis_extraction(data):
                    logger.info(
                        f"Source file updated with v2 ({model}), "
                        f"iteration {iteration}"
                    )
                    return True
                else:
                    logger.warning(f"Thesis extraction incomplete ({model}), escalating...")
                    break  # Try next model

            if provider == "claude" and model == "haiku":
                logger.info("Escalating to Sonnet for better thesis extraction...")

        return False

    async def _update_sources_from_reports_v1(
        self,
        reports: Dict[int, AgentReport],
        iteration: int,
        max_retries: int = 2,
    ) -> bool:
        """
        Original v1 source update flow (fallback).

        Uses raw markdown reports and v1 source_summary_agent.
        """
        # Combine all successful reports into one update
        combined_content = ""
        for type_id, report in reports.items():
            if report.is_success:
                type_name = self.prompt_loader.investing_type_name(type_id)
                combined_content += f"\n\n## {type_name} Analyst (Iteration {iteration})\n"
                combined_content += report.content

        if not combined_content:
            logger.warning("No successful reports to update sources from")
            return False

        for attempt in range(max_retries + 1):
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
                identifier=f"source_update_v1_iter{iteration}_attempt{attempt}",
            )

            source_response = await self.agent_runner.run_single(call)

            if not source_response.is_success:
                logger.warning(f"Source summary agent failed: {source_response.error}")
                if attempt < max_retries:
                    logger.info(f"Retrying source update (attempt {attempt + 2}/{max_retries + 1})...")
                    continue
                return False

            # Try to update from the response
            update_success = self.source_manager.update_from_report(
                combined_content,
                source_response.content
            )

            if update_success:
                logger.info(f"Source file updated successfully v1 (iteration {iteration})")
                return True

            if attempt < max_retries:
                logger.warning(f"Source update parsing failed, retrying (attempt {attempt + 2}/{max_retries + 1})...")
            else:
                logger.error(f"Source file update failed after {max_retries + 1} attempts")

        return False

    async def run(self) -> str:
        """
        Run the complete pipeline.

        Returns:
            Path to the final memo file
        """
        # Clear output directory cache to ensure fresh versioned directory for this run
        clear_output_dir_cache()

        logger.info(f"{'='*60}")
        logger.info(f"TickerToThesis Pipeline: {self.ticker}")
        logger.info(f"{'='*60}")

        self.state.mark_started()
        self.progress.start_pipeline()

        try:
            # Pre-load all prompts
            prompt_stats = self.prompt_loader.load_all()
            logger.info(f"Loaded {len(prompt_stats)} prompts")

            # Run initial source scout to establish baseline data
            self.progress.start_genesis()
            await self._run_initial_source_scout()
            # Estimate genesis cost (rough: ~2K tokens at $0.003/1K)
            self.progress.end_genesis(tokens=2000, cost=0.006)

            # Run iteration 1 (genesis)
            self.progress.start_iteration(1)
            await self._run_iteration_1()
            self.progress.end_iteration(self.state.iterations[1])

            # Run subsequent iterations (debate)
            for iteration in range(2, self.config.num_iterations + 1):
                self.progress.start_iteration(iteration)
                await self._run_iteration(iteration)
                self.progress.end_iteration(self.state.iterations[iteration])

            # Run synthesis (1-step: includes polish, uses Gemini)
            self.progress.start_phase(PhaseType.SYNTHESIS, 1)
            await self._run_synthesis()
            synthesis_tokens = self.state.synthesis_report.token_usage.total_tokens if self.state.synthesis_report else 0
            # Estimate synthesis cost (Gemini pricing ~$0.00025/1K input, $0.001/1K output)
            synthesis_cost = synthesis_tokens * 0.0005 / 1000
            self.progress.end_phase(PhaseType.SYNTHESIS, synthesis_tokens, synthesis_cost)

            # Generate PDFs (EN + CN) after synthesis
            await self._run_pdf_export()

            self.state.mark_completed()

            # Save final state
            self.report_saver.save_pipeline_state(self.state)

            # Progress tracker final summary
            self.progress.end_pipeline(self.state)

            # Additional logging
            logger.info(f"Final memo (EN): {get_final_memo_path(self.ticker, 'EN')}")
            logger.info(f"Final memo (CN): {get_final_memo_path(self.ticker, 'CN')}")

            # Log provider stats if using MultiProviderRunner
            if self.config.multi_provider and hasattr(self.agent_runner, 'get_provider_stats'):
                logger.info(f"{'='*60}")
                logger.info("PROVIDER BREAKDOWN")
                logger.info(f"{'='*60}")
                for provider, stats in self.agent_runner.get_provider_stats().items():
                    logger.info(
                        f"  {provider}: {stats['calls']} calls, "
                        f"{stats['input_tokens'] + stats['output_tokens']:,} tokens"
                    )
                costs = self.agent_runner.get_cost_estimate()
                logger.info(f"Estimated cost: ${costs.get('total', 0):.2f}")

            return str(get_final_memo_path(self.ticker, "EN"))

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
