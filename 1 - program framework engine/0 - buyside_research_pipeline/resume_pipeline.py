#!/usr/bin/env python3
"""
Resume Pipeline from a specific iteration.
Useful when iterations 1-2 are complete and you want to continue to iteration 5+.

Mirrors TickerToThesis.py architecture for consistency:
- MultiProviderRunner support
- DebateHistoryManager for tracking analyst↔RD evolution
- Market data injection (if stock_data available)
- Engagement assessment in RD prompts
- Structured "Response to RD Critique" in analyst prompts
- Position extraction before synthesis
- Provider fallback chain for source scout
- Parallel citation extraction + RD reviews
"""

import asyncio
import logging
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from dotenv import load_dotenv

# Load .env
_env_locations = [
    Path(__file__).parent / ".env",
    Path(__file__).parent.parent.parent / ".env",
    Path.home() / ".anthropic" / ".env",
]
for _env_path in _env_locations:
    if _env_path.exists():
        load_dotenv(_env_path)
        break

from agent_runner import AgentCall, AgentRunner, MultiProviderRunner
from citation_extractor import CitationExtractor
from config import INVESTING_TYPES, PipelineConfig, get_final_memo_path, set_pipeline_mode
from debate_tracker import DebateHistoryManager
from models import AgentReport, AgentRole
from prompt_loader import PromptLoader
from report_saver import ReportSaver
from source_manager import SourceManager

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)


class ResumablePipeline:
    """
    Pipeline that can resume from a specific iteration.

    Mirrors TickerToThesis architecture for feature parity.
    """

    def __init__(
        self,
        ticker: str,
        preliminary_thinking: str,
        num_iterations: int = 5,
        multi_provider: bool = True,
        pipeline_mode: str = "full",
    ):
        self.ticker = ticker.upper()
        self.preliminary_thinking = preliminary_thinking
        self.config = PipelineConfig(
            num_iterations=num_iterations,
            multi_provider=multi_provider,
            pipeline_mode=pipeline_mode,
        )

        # Set global pipeline mode
        set_pipeline_mode(pipeline_mode)

        # Initialize components
        self.prompt_loader = PromptLoader()

        # Use MultiProviderRunner for parallel multi-provider execution
        if self.config.multi_provider:
            self.agent_runner = MultiProviderRunner(self.config)
            logger.info("Using MultiProviderRunner (Claude/GPT-4o/Gemini/Perplexity)")
        else:
            self.agent_runner = AgentRunner(self.config)
            logger.info("Using AgentRunner (Claude only)")

        self.report_saver = ReportSaver(self.ticker)
        self.source_manager = SourceManager(self.ticker, self.prompt_loader)

        # Initialize debate history tracker
        self.debate_tracker = DebateHistoryManager(
            ticker=self.ticker,
            interim_dir=self.report_saver.output_dir / "interim",
        )

        # Optional: Load stock data if available
        self.stock_data = None
        self._try_load_stock_data()

    def _try_load_stock_data(self) -> None:
        """Try to load existing stock data from source file."""
        try:
            from stock_data import StockData
            source_content = self.source_manager.get_source_content()
            if source_content:
                import json
                data = json.loads(source_content)
                if "stock_data" in data:
                    self.stock_data = StockData.from_dict(data["stock_data"])
                    logger.info(f"Loaded stock data: ${self.stock_data.current_price:.2f}")
        except Exception as e:
            logger.debug(f"Could not load stock data: {e}")

    def _get_market_data_injection(self) -> str:
        """Get market data block for prompt injection."""
        if self.stock_data:
            return self.stock_data.get_ground_truth_block()
        return ""

    def _get_market_system_instruction(self) -> str:
        """Get system instruction for market data compliance."""
        if self.stock_data:
            return self.stock_data.get_system_instruction()
        return ""

    def _build_analyst_system_prompt(self, type_id: int) -> str:
        """Build the system prompt for an analyst agent."""
        market_instruction = self._get_market_system_instruction()

        return f"""{market_instruction}

{self.prompt_loader.analyst_role}

---

## Your Investing Philosophy

{self.prompt_loader.investing_type(type_id)}

---

## Memo Engine (Structure & Standards)

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

        # Load accumulated source file (filtered for this analyst type)
        source_content = self.source_manager.get_filtered_sources_for_analyst(type_id)

        # Get market data
        market_data = self._get_market_data_injection()

        # Get debate history for context (iterations 3+)
        debate_history_md = ""
        if iteration >= 3:
            debate_history_md = self.debate_tracker.format_for_analyst_prompt(type_id)
            if debate_history_md:
                debate_history_md = f"\n{debate_history_md}\n---\n"

        return f"""**Analysis Date: {datetime.now().strftime("%B %d, %Y")}**

{market_data}
{debate_history_md}
## Task: Refine Your Analysis of {self.ticker} (Iteration {iteration})

### Your Previous Report (v{prev_iteration})
{prev_report}

### Research Director Feedback
{rd_review}

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

### What I Got Wrong in v{prev_iteration} (if applicable)
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
        """Build system prompt for RD review."""
        market_instruction = self._get_market_system_instruction()

        return f"""{market_instruction}

{self.prompt_loader.rd_review_role}

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
        """Build user prompt for RD review with engagement assessment."""
        type_name = self.prompt_loader.investing_type_name(type_id)

        # Build debate history context section (iterations 3+)
        debate_history_section = ""
        if iteration >= 3:
            debate_history_md = self.debate_tracker.format_for_rd_prompt(type_id)
            if debate_history_md:
                debate_history_section = f"""
{debate_history_md}

---

"""

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

        market_data = self._get_market_data_injection()

        return f"""**Analysis Date: {datetime.now().strftime("%B %d, %Y")}**

{market_data}

## Task: Review {type_name} Analysis of {self.ticker} (Iteration {iteration})
{debate_history_section}### Analyst Report
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

    async def _run_citation_extraction_only(
        self,
        analyst_reports: Dict[int, AgentReport],
        iteration: int,
    ) -> int:
        """Extract citations from analyst reports and update webSource.json."""
        report_contents = {
            type_id: report.content
            for type_id, report in analyst_reports.items()
            if report.is_success
        }

        if not report_contents:
            logger.warning("No successful reports for citation extraction")
            return 0

        extractor = CitationExtractor()
        extractions = []
        for type_id, content in report_contents.items():
            extraction = extractor.extract_from_report(content, type_id, iteration)
            extractions.append(extraction.to_dict())

        total_sources = sum(len(e["sources"]) for e in extractions)
        logger.info(f"Pre-extracted: {total_sources} sources from {len(report_contents)} reports")

        sources_added = self.source_manager.update_citations_only(
            extractions=extractions,
            iteration=iteration,
        )

        return sources_added

    def _build_source_scout_system_prompt(self) -> str:
        """Build the system prompt for web research agent."""
        return f"""{self.prompt_loader.source_scout_agent}

---

## Memo Engine (Evidence Standards)

{self.prompt_loader.memo_engine}
"""

    def _build_source_scout_user_prompt(self, iteration: int, rd_results: dict) -> str:
        """Build the user prompt for web research agent."""
        source_content = self.source_manager.get_source_content()

        rd_feedback_section = ""
        for type_id in range(1, 7):
            if type_id in rd_results and rd_results[type_id].is_success:
                type_name = self.prompt_loader.investing_type_name(type_id)
                rd_feedback_section += f"""
### Research Director Feedback for {type_name} Analyst
{rd_results[type_id].content}

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

    async def _run_source_scout(self, iteration: int, rd_results: dict) -> None:
        """Run web research agent with fallback chain for robustness."""
        logger.info(f"Phase 3: Running web research agent...")

        # Fallback chain: try each provider in order until one succeeds
        fallback_providers = [
            ("perplexity", "sonar"),
            ("gemini", "gemini-2.0-flash"),
            ("claude", "sonnet"),
        ]

        source_scout_report = None
        system_prompt = self._build_source_scout_system_prompt()
        user_prompt = self._build_source_scout_user_prompt(iteration, rd_results)

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

        if source_scout_report and source_scout_report.is_success:
            self.report_saver.save_source_scout(source_scout_report, iteration)
            await self._update_sources_from_source_scout(source_scout_report, iteration)
        else:
            logger.error("  Web Research failed with all providers")

    async def _update_sources_from_source_scout(self, source_scout_report: AgentReport, iteration: int) -> bool:
        """Update source file with findings from web research agent (no LLM)."""
        if not source_scout_report.is_success:
            return False

        sources_added = self.source_manager.update_sources_from_scout_direct(
            source_scout_report.content,
            iteration,
        )

        if sources_added > 0:
            logger.info(f"  Source file updated from web research: +{sources_added} sources")
            return True

        return True

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
                # Track debate history
                self.debate_tracker.append_analyst_entry(type_id, iteration, report.content)
                logger.info(f"  Analyst {type_id}: {report.token_usage.total_tokens:,} tokens")
            else:
                logger.error(f"  Analyst {type_id} failed: {report.error}")

        # Phase 2: Run citation extraction AND RD reviews in PARALLEL
        logger.info("Phase 2: Citation extraction + RD reviews (parallel)...")

        # Build RD review calls
        rd_calls = []
        for type_id in range(1, 7):
            if type_id in analyst_results and analyst_results[type_id].is_success:
                # Load previous RD feedback for engagement assessment
                previous_rd_feedback = self.report_saver.load_rd_review(type_id, iteration - 1)
                call = AgentCall(
                    role=AgentRole.RD_REVIEW,
                    system_prompt=self._build_rd_review_system_prompt(),
                    user_prompt=self._build_rd_review_user_prompt(
                        type_id, iteration, analyst_results[type_id].content,
                        previous_rd_feedback=previous_rd_feedback,
                    ),
                    investing_type_id=type_id,
                    iteration=iteration,
                )
                rd_calls.append(call)

        # Run citation extraction and RD reviews in parallel
        async with asyncio.TaskGroup() as tg:
            citation_task = tg.create_task(
                self._run_citation_extraction_only(analyst_results, iteration)
            )
            rd_task = tg.create_task(
                self.agent_runner.run_rd_review_batch(rd_calls)
            )

        sources_added = citation_task.result()
        rd_results = rd_task.result()
        logger.info(f"  Citation extraction: +{sources_added} sources")

        # Save RD reviews
        for type_id, report in rd_results.items():
            if report.is_success:
                self.report_saver.save_rd_review(report)
                # Track debate history
                self.debate_tracker.append_rd_entry(type_id, iteration, report.content)
                logger.info(f"  RD Review {type_id}: {report.token_usage.total_tokens:,} tokens")
            else:
                logger.error(f"  RD Review {type_id} failed: {report.error}")

        # Phase 3: Run web research for next iteration
        if iteration < self.config.num_iterations:
            await self._run_source_scout(iteration, rd_results)

        # Calculate totals
        analyst_tokens = sum(r.token_usage.total_tokens for r in analyst_results.values() if r.is_success)
        rd_tokens = sum(r.token_usage.total_tokens for r in rd_results.values() if r.is_success)
        logger.info(f"Iteration {iteration} complete: {analyst_tokens + rd_tokens:,} total tokens")

    async def _extract_analyst_positions(self, all_final_reports: Dict[int, str]) -> str:
        """Extract analyst recommendations and key debates before synthesis."""
        reports_section = ""
        for type_id in range(1, 7):
            if type_id in all_final_reports:
                type_name = self.prompt_loader.investing_type_name(type_id)
                reports_section += f"""
### Analyst {type_id}: {type_name}
{all_final_reports[type_id]}

---
"""

        extraction_prompt = f"""Analyze these 6 analyst reports on {self.ticker} and extract a structured summary of positions and debates.

{reports_section}

## Instructions

Extract the following information in a structured format:

### 1. RECOMMENDATION TALLY

For each analyst (1-6), extract:
| Analyst | Type | Recommendation | Target Price | Conviction | Primary Rationale |
|---------|------|----------------|--------------|------------|-------------------|

Where:
- Recommendation: LONG / SHORT / PASS (be precise - if they say "avoid" or "sell" that's SHORT)
- Target Price: Extract if given, otherwise "N/A"
- Conviction: High / Medium / Low (infer from language)
- Primary Rationale: 1 sentence summary of their main argument

### 2. KEY DEBATES (rank by importance)

Identify 3-5 substantive disagreements where analysts took opposing positions.
For each debate, format as:

**Debate #X: [The core question]**
- **Bull Case:** Analyst(s) #X, #Y argue: [their position with evidence]
- **Bear Case:** Analyst(s) #X, #Y argue: [their position with evidence]
- **Vote Split:** X bulls vs Y bears vs Z neutral

### 3. CONSENSUS VIEWS

List 2-3 things where most/all analysts agreed.

### 4. KILL CONDITIONS (2+ analysts mentioned)

List specific kill conditions that appear in multiple analyst reports.

### 5. CONTRARIAN FLAGS

If any analyst has a view that directly contradicts the majority, flag it.

---

Output this structured summary. The synthesis step MUST address each debate.
"""

        call = AgentCall(
            role=AgentRole.SOURCE_SCOUT,
            system_prompt="""You are an expert at extracting structured information from investment research reports.
Your job is to identify recommendations, debates, and disagreements between analysts.
Be precise about recommendations - if an analyst says "avoid", "sell", or expresses bearish conviction, that's a SHORT recommendation.""",
            user_prompt=extraction_prompt,
            iteration=0,
            identifier="analyst_position_extraction",
            provider="claude",
            model="haiku",
        )

        extraction_report = await self.agent_runner.run_single(call)

        if extraction_report.is_success:
            logger.info(f"Extracted analyst positions: {extraction_report.token_usage.total_tokens:,} tokens")
            return extraction_report.content
        else:
            logger.warning(f"Position extraction failed: {extraction_report.error}")
            return """## Position Extraction Failed

⚠️ Automated extraction failed. Synthesis MUST still:
1. Manually identify the recommendation of each analyst (LONG/SHORT/PASS)
2. Identify key disagreements between analysts
3. If your final recommendation differs from the majority, explain why they are wrong
"""

    def _build_rd_synthesis_system_prompt(self) -> str:
        """Build the system prompt for RD synthesis."""
        market_instruction = self._get_market_system_instruction()

        return f"""{market_instruction}

{self.prompt_loader.rd_synthesis_role}

---

## Memo Engine (Structure & Standards)

{self.prompt_loader.memo_engine}
"""

    def _build_rd_synthesis_user_prompt(
        self,
        all_final_reports: Dict[int, str],
        debate_summary: Optional[str] = None,
    ) -> str:
        """Build the user prompt for final RD synthesis."""
        reports_section = ""
        for type_id in range(1, 7):
            if type_id in all_final_reports:
                type_name = self.prompt_loader.investing_type_name(type_id)
                reports_section += f"""
### {type_name} Analyst (Final Report)
{all_final_reports[type_id]}

---
"""

        source_content = self.source_manager.get_source_content()

        debate_section = ""
        if debate_summary:
            debate_section = f"""
---

## ⚠️ ANALYST POSITIONS & DEBATES (YOU MUST ADDRESS THESE)

The following positions and debates were extracted from the analyst reports above.
You MUST address each key debate in your synthesis.

{debate_summary}

---

### CRITICAL ACCOUNTABILITY RULES

1. **Majority Override Requires Justification**: If your final recommendation (LONG/SHORT/PASS)
   differs from the majority of analysts, you MUST include a section titled
   **"Why the [Bears/Bulls] Are Wrong"** with specific refutations of their arguments.

2. **Key Analytical Tensions**: Your "Key Analytical Tensions" section MUST include
   the top 3 debates from the summary above.

3. **No Silent Disagreement**: You cannot ignore a debate where 3+ analysts flagged a concern.
   Address it explicitly with evidence, even if you conclude it's not material.

4. **Contrarian Flags**: If any contrarian flag was identified above, explain why that
   analyst's view is either correct (and the majority is wrong) or incorrect.

---

"""

        market_data = self._get_market_data_injection()

        return f"""## Task: Synthesize Final Investment View on {self.ticker}

{market_data}

You have received final reports from 6 analysts, each with a distinct investing philosophy.
Your job is to synthesize these into a single, decision-grade investment memo.
{debate_section}
### Full Analyst Reports

{reports_section}

### Complete Source File
```json
{source_content}
```

### Instructions
1. **Address the extracted debates first** - Do not skip any debate from the summary above
2. Identify the central tension across reports - where do they agree? Disagree?
3. Determine which assumptions are defensible
4. Form YOUR final view - don't split the difference
5. Articulate the variant perception: What does the market believe? Why are they wrong?
6. Rank your conviction: Is this "high conviction" or "worth monitoring"?
7. Include complete Sources Used table

Remember: If your conclusion is consensus, you've added nothing.
But also: If your conclusion contradicts the majority without explanation, you've avoided the hard work.
"""

    async def _run_synthesis(self) -> str:
        """Run final synthesis phase with position extraction."""
        logger.info(f"{'='*60}")
        logger.info("SYNTHESIS: Research Director Final View")
        logger.info(f"{'='*60}")

        # Load all final reports
        final_iteration = self.config.num_iterations
        all_final_reports = self.report_saver.load_all_final_reports(final_iteration)
        logger.info(f"Loaded {len(all_final_reports)} final analyst reports (v{final_iteration})")

        if len(all_final_reports) < 4:
            raise RuntimeError(f"Need at least 4 final reports, got {len(all_final_reports)}")

        # Extract analyst positions and debates before synthesis
        logger.info("Extracting analyst positions and key debates...")
        debate_summary = await self._extract_analyst_positions(all_final_reports)
        logger.info(f"Debate summary extracted: {len(debate_summary)} chars")

        # Save debate summary
        debate_path = self.report_saver.output_dir / "interim" / "debate_summary.md"
        debate_path.parent.mkdir(parents=True, exist_ok=True)
        debate_path.write_text(debate_summary, encoding="utf-8")
        logger.info(f"Debate summary saved: {debate_path}")

        # Run synthesis with debate summary
        call = AgentCall(
            role=AgentRole.RD_SYNTHESIS,
            system_prompt=self._build_rd_synthesis_system_prompt(),
            user_prompt=self._build_rd_synthesis_user_prompt(all_final_reports, debate_summary),
            iteration=1,
        )

        synthesis_report = await self.agent_runner.run_single(call)

        if not synthesis_report.is_success:
            raise RuntimeError(f"Synthesis failed: {synthesis_report.error}")

        # Save final memo directly (synthesis v2 includes polish)
        filepath = self.report_saver.save_final(synthesis_report, lang="EN")
        logger.info(f"Final memo saved: {filepath}")
        logger.info(f"Synthesis complete: {synthesis_report.token_usage.total_tokens:,} tokens")

        return synthesis_report.content

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

        # Pre-load prompts
        prompt_stats = self.prompt_loader.load_all()
        logger.info(f"Loaded {len(prompt_stats)} prompts")

        # Rebuild debate history from existing files
        logger.info("Rebuilding debate history from existing files...")
        for iteration in range(1, start_iteration):
            for type_id in range(1, 7):
                analyst_content = self.report_saver.load_analyst_report(type_id, iteration)
                if analyst_content:
                    self.debate_tracker.append_analyst_entry(type_id, iteration, analyst_content)
                rd_content = self.report_saver.load_rd_review(type_id, iteration)
                if rd_content:
                    self.debate_tracker.append_rd_entry(type_id, iteration, rd_content)
        logger.info(f"Rebuilt debate history for iterations 1-{start_iteration - 1}")

        # Run remaining iterations
        for iteration in range(start_iteration, self.config.num_iterations + 1):
            await self._run_iteration(iteration)

        # Run synthesis (includes polish in v2)
        await self._run_synthesis()

        logger.info(f"{'='*60}")
        logger.info("PIPELINE COMPLETE")
        logger.info(f"{'='*60}")

        return get_final_memo_path(self.ticker, lang="EN")


async def main():
    if len(sys.argv) < 3:
        print("Usage: python resume_pipeline.py <TICKER> <START_ITERATION> [TOTAL_ITERATIONS] [--light]")
        print("Example: python resume_pipeline.py WU 3 5")
        print("Example: python resume_pipeline.py HOOD 6 10 --light  # Resume from iter 6, run until iter 10, light mode")
        sys.exit(1)

    ticker = sys.argv[1]
    start_iteration = int(sys.argv[2])

    # Parse remaining args
    num_iterations = 5
    pipeline_mode = "full"
    preliminary_thinking = "Resuming analysis..."

    remaining_args = sys.argv[3:]
    for i, arg in enumerate(remaining_args):
        if arg == "--light":
            pipeline_mode = "light"
        elif arg.isdigit():
            num_iterations = int(arg)
        elif not arg.startswith("--"):
            preliminary_thinking = arg

    # Clamp iterations to valid range
    num_iterations = max(5, min(10, num_iterations))

    if pipeline_mode == "light":
        logger.info("Running in LIGHT MODE (gpt-4o-mini for most agents)")

    pipeline = ResumablePipeline(
        ticker,
        preliminary_thinking,
        num_iterations=num_iterations,
        pipeline_mode=pipeline_mode,
    )
    final_path = await pipeline.resume_from(start_iteration)
    print(f"\nSuccess! Final memo: {final_path}")


if __name__ == "__main__":
    asyncio.run(main())
