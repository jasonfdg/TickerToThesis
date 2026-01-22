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
    python TickerToThesis.py AAPL "thinking..." --no-gui  # Disable dashboard
    python TickerToThesis.py AAPL ""  # Bootstrap generates thesis automatically
    python TickerToThesis.py AAPL     # Same as above (empty thesis)
"""

import argparse
import asyncio
import json
import logging
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from dashboard.emitter import ProgressEmitter
    from dashboard.server import DashboardServer

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
    from .config import INVESTING_TYPES, PipelineConfig, get_final_memo_path, get_final_pdf_path, clear_output_dir_cache, set_pipeline_mode
    from .models import AgentReport, AgentRole, IterationState, PipelineState, TokenUsage
    from .prompt_loader import PromptLoader
    from .progress_tracker import ProgressTracker, PhaseType
    from .report_saver import ReportSaver
    from .source_manager import SourceManager
    from .translate_export import run_pipeline as run_translate_export
except ImportError:
    from agent_runner import AgentCall, AgentRunner, MultiProviderRunner
    from citation_extractor import CitationExtractor, extract_citations_from_reports
    from config import INVESTING_TYPES, PipelineConfig, get_final_memo_path, get_final_pdf_path, clear_output_dir_cache, set_pipeline_mode
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
        emitter: Optional["ProgressEmitter"] = None,
    ):
        self.ticker = ticker.upper()
        self.preliminary_thinking = preliminary_thinking
        self.config = config or PipelineConfig()
        self.emitter = emitter

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

        # Initialize progress tracker with optional dashboard emitter
        self.progress = ProgressTracker(
            ticker=self.ticker,
            num_iterations=self.config.num_iterations,
            num_analysts=len(INVESTING_TYPES),
            provider_factory=getattr(self.agent_runner, 'provider_factory', None),
            log_file=str(self.config.log_dir / f"{self.ticker}_progress.log") if self.config.log_dir else None,
            emitter=emitter,
        )

        # Thesis evolution tracking for dashboard
        self._previous_thesis_summary: Optional[str] = None

    # Analyst type names for dashboard display
    ANALYST_NAMES = {
        1: "Quality Compounders",
        2: "Imaginative Growth",
        3: "Fundamental L/S",
        4: "Deep Value",
        5: "Event-Driven",
        6: "Macro-Tactical",
    }

    def _emit_cost_update(self) -> None:
        """Emit current cost breakdown to dashboard.

        Gets cost estimates from the provider factory (if using MultiProviderRunner)
        and emits them to the progress tracker for dashboard display.
        """
        if not self.emitter:
            return

        try:
            # Only MultiProviderRunner has get_cost_estimate()
            if hasattr(self.agent_runner, 'get_cost_estimate'):
                costs = self.agent_runner.get_cost_estimate()
                self.progress.emit_cost_update(
                    claude_cli=costs.get("claude-cli", 0.0),
                    openai=costs.get("openai", 0.0),
                    gemini=costs.get("gemini", 0.0),
                )
        except Exception as e:
            logger.debug(f"Could not emit cost update: {e}")

    async def _generate_thesis_summary(
        self,
        iteration: int,
        analyst_reports: Dict[int, AgentReport],
        rd_reviews: Dict[int, AgentReport],
    ) -> None:
        """Generate and emit thesis evolution summary for dashboard.

        Called after RD reviews complete to provide a concise summary of
        thesis evolution for the dashboard's Thesis Evolution panel.
        """
        if not self.emitter:
            return

        try:
            # Import summarizer (optional dependency)
            try:
                from dashboard.summarizer import generate_thesis_summary
            except ImportError:
                logger.debug("Dashboard summarizer not available")
                return

            # Extract conclusions from analyst reports (last 500 chars of each)
            analyst_excerpts = {
                tid: report.content[-500:]
                for tid, report in analyst_reports.items()
                if report.is_success
            }

            # Extract critiques from RD reviews (first 300 chars of each)
            rd_excerpts = {
                tid: review.content[:300]
                for tid, review in rd_reviews.items()
                if review.is_success
            }

            # Get provider factory for API call
            provider_factory = getattr(self.agent_runner, 'provider_factory', None)

            # Generate summary
            summary = await generate_thesis_summary(
                iteration=iteration,
                analyst_reports=analyst_excerpts,
                rd_critiques=rd_excerpts,
                previous_summary=self._previous_thesis_summary,
                provider_factory=provider_factory,
            )

            # Store for next iteration
            self._previous_thesis_summary = summary

            # Emit to dashboard
            self.progress.emit_thesis_summary(iteration, summary)
            logger.debug(f"Thesis summary for iteration {iteration}: {summary[:100]}...")

        except Exception as e:
            logger.warning(f"Failed to generate thesis summary: {e}")

    def _format_analyst_summaries_for_rd(self, exclude_type_id: int) -> Optional[str]:
        """
        Format analyst summaries for RD review prompt, excluding the current analyst.

        This provides the RD with cross-analyst context so they can highlight
        impactful findings from other analysts when relevant.

        Args:
            exclude_type_id: Analyst type to exclude (the one being reviewed)

        Returns:
            Formatted markdown string of other analysts' summaries,
            or None if no summaries are available.
        """
        summaries_data = self.source_manager.get_analyst_summaries()

        if not summaries_data or not summaries_data.get("summaries"):
            return None

        iteration = summaries_data.get("iteration", "?")
        summaries = summaries_data.get("summaries", [])

        # Filter out the analyst being reviewed
        other_summaries = [
            s for s in summaries
            if s.get("type_id") != exclude_type_id
        ]

        if not other_summaries:
            return None

        # Build formatted markdown
        lines = [
            f"## Other Analysts' Key Findings (Iteration {iteration})",
            "",
        ]

        for s in other_summaries:
            type_name = s.get("type_name", f"Analyst {s.get('type_id', '?')}")
            position = s.get("position", "?")
            target = s.get("target_price", "")
            summary = s.get("summary", "")

            # Format: **Quality Compounder** — LONG @ $85
            header = f"**{type_name}** — {position}"
            if target:
                header += f" @ {target}"

            lines.append(header)
            lines.append(summary)
            lines.append("")

        return "\n".join(lines)

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
        analyst_summaries_md: Optional[str] = None,
    ) -> str:
        """Build the user prompt for RD review.

        Args:
            type_id: Analyst type being reviewed (1-6)
            iteration: Current iteration number
            analyst_report: The analyst's report content
            previous_rd_feedback: RD's feedback from previous iteration (for engagement assessment)
            analyst_summaries_md: Formatted markdown of other analysts' summaries (for cross-analyst context)
        """
        type_name = self.prompt_loader.investing_type_name(type_id)

        # Build cross-analyst context section
        cross_analyst_section = ""
        if analyst_summaries_md:
            cross_analyst_section = f"""
{analyst_summaries_md}

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

        base_instructions = f"""## Task: Review {type_name} Analysis of {self.ticker} (Iteration {iteration})
{cross_analyst_section}
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

    def _build_rd_synthesis_user_prompt(
        self,
        all_v5_reports: Dict[int, str],
        debate_summary: Optional[str] = None,
    ) -> str:
        """Build the user prompt for final RD synthesis.

        Args:
            all_v5_reports: Dict mapping analyst type_id to their final report content
            debate_summary: Pre-extracted analyst positions and debates (if available)
        """
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

        # Build the debate accountability section
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
   the top 3 debates from the summary above. You may NOT substitute different tensions
   that better fit your conclusion.

3. **No Silent Disagreement**: You cannot ignore a debate where 3+ analysts flagged a concern.
   Address it explicitly with evidence, even if you conclude it's not material.

4. **Contrarian Flags**: If any contrarian flag was identified above, explain why that
   analyst's view is either correct (and the majority is wrong) or incorrect.

---

"""

        return f"""## Task: Synthesize Final Investment View on {self.ticker}

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

    async def _extract_analyst_positions(self, all_v5_reports: Dict[int, str]) -> str:
        """Extract analyst recommendations and key debates before synthesis.

        This forces the synthesis to acknowledge and address disagreements rather
        than picking whichever narrative is easiest to defend.

        Args:
            all_v5_reports: Dict mapping analyst type_id to their final report content

        Returns:
            Structured debate summary that synthesis MUST address
        """
        # Build the extraction prompt with all reports
        reports_section = ""
        for type_id in range(1, 7):
            if type_id in all_v5_reports:
                type_name = self.prompt_loader.investing_type_name(type_id)
                reports_section += f"""
### Analyst {type_id}: {type_name}
{all_v5_reports[type_id]}

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

Focus on debates where analysts cite conflicting evidence or reach opposite conclusions from the same facts.

### 3. CONSENSUS VIEWS

List 2-3 things where most/all analysts agreed (to distinguish from debates).

### 4. KILL CONDITIONS (2+ analysts mentioned)

List specific kill conditions that appear in multiple analyst reports:
- [Kill condition] — cited by Analysts #X, #Y
- [Kill condition] — cited by Analysts #X, #Y, #Z

Be specific and actionable (not generic like "revenue declines").

### 5. CONTRARIAN FLAGS

If any analyst has a view that directly contradicts the majority, flag it:
- Analyst #X ({type_name}) recommends [X] while {count} others recommend [Y]. Their key argument: [summary]

---

Output this structured summary. The synthesis step MUST address each debate and explain its resolution with evidence.
"""

        # Use Haiku for speed and cost - this is a structured extraction task
        call = AgentCall(
            role=AgentRole.SOURCE_SUMMARY,  # Reuse role for extraction task
            system_prompt="""You are an expert at extracting structured information from investment research reports.
Your job is to identify recommendations, debates, and disagreements between analysts.
Be precise about recommendations - if an analyst says "avoid", "sell", or expresses bearish conviction, that's a SHORT recommendation.
Extract the exact evidence and reasoning each analyst uses.""",
            user_prompt=extraction_prompt,
            iteration=0,
            identifier="analyst_position_extraction",
            provider="claude",
            model="haiku",  # Fast and cheap for extraction
        )

        extraction_report = await self.agent_runner.run_single(call)

        if extraction_report.is_success:
            logger.info(f"Extracted analyst positions: {extraction_report.token_usage.total_tokens:,} tokens")
            return extraction_report.content
        else:
            logger.warning(f"Position extraction failed: {extraction_report.error}")
            # Return a minimal fallback that still forces synthesis to consider disagreements
            return """## Position Extraction Failed

⚠️ Automated extraction failed. Synthesis MUST still:
1. Manually identify the recommendation of each analyst (LONG/SHORT/PASS)
2. Identify key disagreements between analysts
3. If your final recommendation differs from the majority, explain why they are wrong

Do NOT proceed without addressing analyst disagreements explicitly.
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
            # Emit source update event for dashboard
            self.progress.emit_source_updated(new_citations=1)  # Web research typically adds sources
            return True

        logger.warning(f"  Source file update from web research failed (iteration {iteration})")
        return False

    async def _bootstrap_thesis(self) -> str:
        """Quick search for bull/bear cases and key debates.

        Runs a single Perplexity search at pipeline start to provide
        market context. This augments the user's thesis (if provided)
        or generates a starting thesis (if empty).

        Returns:
            Concise summary of current investment debates for the ticker.
        """
        query = (
            f"What are the key investment debates for {self.ticker}? "
            f"Specifically: (1) What transformative forces (AI, robotics, Web3, or other) most impact this company? "
            f"(2) What strategic pivots or hidden optionality might the market be missing? "
            f"(3) What's the most controversial bull and bear case?"
        )

        logger.info("Bootstrapping thesis via Perplexity search...")

        try:
            result = await self.agent_runner.run_single(
                AgentCall(
                    role=AgentRole.SOURCE_SCOUT,
                    system_prompt=(
                        "You are a buyside research analyst. Find the BIG STORY - the single most "
                        "transformative force acting on this company over the next 3-5 years. "
                        "Focus on:\n"
                        "1. TRANSFORMATIVE FORCES: Consider AI, robotics, Web3, regulatory shifts, or other "
                        "paradigm changes. Is this an existential threat to the moat, or a transformative opportunity?\n"
                        "2. STRATEGIC PIVOTS: Is management making a bold bet the market undervalues?\n"
                        "3. VARIANT VIEW: What does the market believe that might be wrong?\n\n"
                        "Be specific and narrative-driven. Surface debates, not just facts."
                    ),
                    user_prompt=query,
                    provider="perplexity",
                    model="sonar",
                )
            )

            if result.is_success:
                logger.info(f"Thesis bootstrap complete: {result.token_usage.total_tokens:,} tokens")
                return result.content
            else:
                logger.warning(f"Thesis bootstrap failed: {result.error}")
                return ""

        except Exception as e:
            logger.warning(f"Thesis bootstrap exception: {e}")
            return ""

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
                    # Emit cost update for dashboard
                    self._emit_cost_update()
                    return
                else:
                    logger.warning(f"  Initial scout failed with {provider}: {report.error}")

            except Exception as e:
                logger.warning(f"  Initial scout exception with {provider}: {e}")
                continue

        logger.error("Initial source scout failed with all providers")
        self._emit_cost_update()

    async def _run_iteration_1(self) -> None:
        """Run iteration 1 (genesis): Initial analyst reports and RD reviews."""
        logger.info(f"{'='*60}")
        logger.info(f"ITERATION 1: Genesis")
        logger.info(f"{'='*60}")

        iteration_state = self.state.iterations[1]
        iteration_state.mark_started()

        # Phase 1: Run 6 parallel analyst calls
        logger.info("Phase 1: Running 6 parallel analyst calls...")

        # Emit agent started events
        for type_id in range(1, 7):
            self.progress.emit_agent_started("analyst", type_id, self.ANALYST_NAMES.get(type_id, f"Analyst {type_id}"))

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

        # Save analyst reports and emit completion events
        for type_id, report in analyst_reports.items():
            if report.is_success:
                self.report_saver.save_analyst_report(report)
                self.progress.emit_agent_completed("analyst", type_id, report.token_usage.total_tokens, True)
                logger.info(
                    f"  Analyst {type_id} ({self.prompt_loader.investing_type_name(type_id)}): "
                    f"{report.token_usage.total_tokens:,} tokens"
                )
            else:
                self.progress.emit_agent_failed("analyst", type_id, report.error or "Unknown error")

        # Emit cost update after analyst phase
        self._emit_cost_update()

        # Phase 2: Source update (extracts citations AND analyst_summaries)
        # Must complete before RD reviews so summaries are available for cross-analyst context
        logger.info("Phase 2: Updating sources (citations + analyst summaries)...")
        source_updated = await self._update_sources_from_reports(analyst_reports, 1)
        iteration_state.source_updated = source_updated

        # Phase 3: RD reviews with cross-analyst summaries
        logger.info("Phase 3: Running 6 parallel RD reviews (with cross-analyst context)...")

        # Build RD review calls with analyst summaries injected
        rd_calls = []
        for type_id in range(1, 7):
            if type_id in analyst_reports and analyst_reports[type_id].is_success:
                # Get summaries of OTHER analysts for cross-analyst context
                summaries_md = self._format_analyst_summaries_for_rd(exclude_type_id=type_id)
                call = AgentCall(
                    role=AgentRole.RD_REVIEW,
                    system_prompt=self._build_rd_review_system_prompt(),
                    user_prompt=self._build_rd_review_user_prompt(
                        type_id, 1, analyst_reports[type_id].content,
                        analyst_summaries_md=summaries_md,
                    ),
                    investing_type_id=type_id,
                    iteration=1,
                )
                rd_calls.append(call)

        rd_reviews = await self.agent_runner.run_rd_review_batch(rd_calls)
        iteration_state.rd_reviews = rd_reviews

        # Emit RD started events
        for type_id in range(1, 7):
            self.progress.emit_agent_started("rd_review", type_id, f"RD Review {type_id}")

        # Save RD reviews and emit completion events
        for type_id, review in rd_reviews.items():
            if review.is_success:
                self.report_saver.save_rd_review(review)
                self.progress.emit_agent_completed("rd_review", type_id, review.token_usage.total_tokens, True)
                logger.info(
                    f"  RD Review {type_id}: {review.token_usage.total_tokens:,} tokens"
                )
            else:
                self.progress.emit_agent_failed("rd_review", type_id, review.error or "Unknown error")

        # Emit cost update after RD review phase
        self._emit_cost_update()

        # Generate thesis summary for dashboard
        await self._generate_thesis_summary(1, analyst_reports, rd_reviews)

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

        # Emit agent started events
        for type_id in range(1, 7):
            self.progress.emit_agent_started("analyst", type_id, self.ANALYST_NAMES.get(type_id, f"Analyst {type_id}"))

        analyst_reports = await self.agent_runner.run_analyst_batch(analyst_calls)
        iteration_state.analyst_reports = analyst_reports

        # Save analyst reports and emit completion events
        for type_id, report in analyst_reports.items():
            if report.is_success:
                self.report_saver.save_analyst_report(report)
                self.progress.emit_agent_completed("analyst", type_id, report.token_usage.total_tokens, True)
                logger.info(
                    f"  Analyst {type_id}: {report.token_usage.total_tokens:,} tokens"
                )
            else:
                self.progress.emit_agent_failed("analyst", type_id, report.error or "Unknown error")

        # Emit cost update after analyst phase
        self._emit_cost_update()

        # Phase 2: Source update (extracts citations AND analyst_summaries)
        # Must complete before RD reviews so summaries are available for cross-analyst context
        logger.info("Phase 2: Updating sources (citations + analyst summaries)...")
        source_updated = await self._update_sources_from_reports(analyst_reports, iteration)
        iteration_state.source_updated = source_updated

        # Phase 3: RD reviews with cross-analyst summaries
        logger.info("Phase 3: Running 6 parallel RD reviews (with cross-analyst context)...")

        # Build RD review calls with analyst summaries injected
        rd_calls = []
        for type_id in range(1, 7):
            if type_id in analyst_reports and analyst_reports[type_id].is_success:
                # Load previous RD feedback for engagement assessment
                previous_rd_feedback = self.report_saver.load_rd_review(type_id, iteration - 1)
                # Get summaries of OTHER analysts for cross-analyst context
                summaries_md = self._format_analyst_summaries_for_rd(exclude_type_id=type_id)
                call = AgentCall(
                    role=AgentRole.RD_REVIEW,
                    system_prompt=self._build_rd_review_system_prompt(),
                    user_prompt=self._build_rd_review_user_prompt(
                        type_id, iteration, analyst_reports[type_id].content,
                        previous_rd_feedback=previous_rd_feedback,
                        analyst_summaries_md=summaries_md,
                    ),
                    investing_type_id=type_id,
                    iteration=iteration,
                )
                rd_calls.append(call)

        # Emit RD started events
        for type_id in range(1, 7):
            self.progress.emit_agent_started("rd_review", type_id, f"RD Review {type_id}")

        rd_reviews = await self.agent_runner.run_rd_review_batch(rd_calls)
        iteration_state.rd_reviews = rd_reviews

        # Save RD reviews and emit completion events
        for type_id, review in rd_reviews.items():
            if review.is_success:
                self.report_saver.save_rd_review(review)
                self.progress.emit_agent_completed("rd_review", type_id, review.token_usage.total_tokens, True)
                logger.info(f"  RD Review {type_id}: {review.token_usage.total_tokens:,} tokens")
            else:
                self.progress.emit_agent_failed("rd_review", type_id, review.error or "Unknown error")

        # Emit cost update after RD review phase
        self._emit_cost_update()

        # Generate thesis summary for dashboard
        await self._generate_thesis_summary(iteration, analyst_reports, rd_reviews)

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

        Flow:
        1. Load all v5 analyst reports
        2. Extract analyst positions and key debates (forces accountability)
        3. Run synthesis with debate summary injected (must address disagreements)

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

        # NEW: Extract analyst positions and debates before synthesis
        # This forces the synthesis to acknowledge and address disagreements
        logger.info("Extracting analyst positions and key debates...")
        debate_summary = await self._extract_analyst_positions(all_final_reports)
        logger.info(f"Debate summary extracted: {len(debate_summary)} chars")

        # Save debate summary for debugging/audit
        debate_path = self.report_saver.output_dir / "interim" / "debate_summary.md"
        debate_path.parent.mkdir(parents=True, exist_ok=True)
        debate_path.write_text(debate_summary, encoding="utf-8")
        logger.info(f"Debate summary saved: {debate_path}")

        # Run synthesis with debate summary (uses Gemini via ROLE_PROVIDER_CONFIG)
        call = AgentCall(
            role=AgentRole.RD_SYNTHESIS,
            system_prompt=self._build_rd_synthesis_system_prompt(),
            user_prompt=self._build_rd_synthesis_user_prompt(all_final_reports, debate_summary),
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
            # Emit final cost update
            self._emit_cost_update()
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
        Run source update with v2 agent using configured provider.

        Uses provider from ROLE_PROVIDER_CONFIG["source_summary"] (default: gpt-4o-mini).
        GPT-4o-mini has best JSON validity from benchmark testing.

        Args:
            update_prompt: Structured prompt for v2 agent
            iteration: Current iteration number
            extractions: Pre-extracted data for validation
            max_retries: Number of retries

        Returns:
            True if update succeeded
        """
        for attempt in range(max_retries + 1):
            # Use configured provider (gpt-4o-mini by default - best JSON validity)
            call = AgentCall(
                role=AgentRole.SOURCE_SUMMARY,
                system_prompt=self.prompt_loader.source_summary_agent_v2,
                user_prompt=update_prompt,
                iteration=iteration,
                identifier=f"source_update_v2_iter{iteration}_attempt{attempt}",
                # No provider/model override - uses config routing
            )

            source_response = await self.agent_runner.run_single(call)

            if not source_response.is_success:
                logger.warning(f"Source summary v2 failed: {source_response.error}")
                if attempt < max_retries:
                    logger.info(f"Retrying source update (attempt {attempt + 2}/{max_retries + 1})...")
                continue

            # Try to update from the response
            update_success = self.source_manager.update_from_report(
                "",  # No raw report content needed for v2
                source_response.content
            )

            if not update_success:
                logger.warning(f"Source update parsing failed (attempt {attempt + 1})")
                continue

            # Validate thesis extraction quality
            data = self.source_manager.load_source_file()
            if self.source_manager.validate_thesis_extraction(data):
                logger.info(f"Source file updated with v2, iteration {iteration}")
                # Emit source update event for dashboard
                num_sources = sum(len(e.get("sources", [])) for e in extractions)
                self.progress.emit_source_updated(new_citations=num_sources)
                return True
            else:
                logger.warning(f"Thesis extraction incomplete (attempt {attempt + 1})")

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
                # Emit source update event for dashboard
                self.progress.emit_source_updated(new_citations=len(reports))
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

            # Quick thesis bootstrap via Perplexity
            bootstrap_context = await self._bootstrap_thesis()
            if bootstrap_context:
                if self.preliminary_thinking.strip():
                    # Augment user's thesis with market context
                    self.preliminary_thinking = (
                        f"{self.preliminary_thinking}\n\n---\n\n"
                        f"### Market Context\n{bootstrap_context}"
                    )
                    logger.info("Augmented user thesis with market context")
                else:
                    # Use bootstrap as the thesis
                    self.preliminary_thinking = bootstrap_context
                    logger.info("Using bootstrapped thesis (no user input)")
                # Update state to reflect the enriched thesis
                self.state.preliminary_thinking = self.preliminary_thinking

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
            export_results = await self._run_pdf_export()

            # Extract PDF paths for dashboard
            pdf_paths = {}
            if export_results.get("pdf_en"):
                pdf_paths["pdf_en"] = str(export_results["pdf_en"].output_path.relative_to(
                    self.report_saver.output_dir.parent
                ))
            if export_results.get("pdf_zh"):
                pdf_paths["pdf_cn"] = str(export_results["pdf_zh"].output_path.relative_to(
                    self.report_saver.output_dir.parent
                ))

            self.state.mark_completed()

            # Save final state
            self.report_saver.save_pipeline_state(self.state)

            # Progress tracker final summary (include PDF paths for dashboard)
            self.progress.end_pipeline(self.state, pdf_paths=pdf_paths)

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
        default="",
        help="Preliminary thinking about the company (optional - bootstrap generates if empty)",
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
        default="",
        help="Preliminary thinking (optional - bootstrap generates if empty)",
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
    parser.add_argument(
        "--no-gui",
        action="store_true",
        help="Disable the browser-based progress dashboard",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8765,
        help="Port for the dashboard server (default: 8765)",
    )
    parser.add_argument(
        "--light",
        action="store_true",
        help="Use light mode (gpt-4o-mini) for faster, cheaper analysis (~$0.20 vs ~$2.50/ticker)",
    )

    args = parser.parse_args()

    # Resolve ticker and thinking from either positional or flag args
    ticker = args.ticker or args.ticker_flag
    # Use positional thinking if provided (even if empty), else fall back to flag
    thinking = args.thinking if args.thinking is not None else (args.thinking_flag or "")

    if not ticker:
        parser.error("ticker is required (positional or --ticker)")

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

    # Determine pipeline mode
    pipeline_mode = "light" if args.light else "full"

    # Set global pipeline mode for path functions
    set_pipeline_mode(pipeline_mode)

    # Create config with pipeline mode
    config = PipelineConfig(
        model=args.model,
        verbose=args.verbose,
        pipeline_mode=pipeline_mode,
    )

    if args.light:
        logger.info("Running in LIGHT MODE (gpt-4o-mini for most agents)")

    # Initialize dashboard if enabled
    emitter = None
    dashboard_server = None

    if not args.no_gui:
        try:
            from dashboard.emitter import ProgressEmitter
            from dashboard.server import start_dashboard_server

            emitter = ProgressEmitter()
            dashboard_server = start_dashboard_server(
                emitter=emitter,
                port=args.port,
                open_browser=True,
            )
            logger.info(f"Dashboard started at http://127.0.0.1:{dashboard_server.port}")
        except ImportError as e:
            logger.warning(f"Dashboard not available: {e}")
            logger.info("Run with --no-gui to suppress this warning")
        except Exception as e:
            logger.warning(f"Failed to start dashboard: {e}")

    # Run pipeline
    pipeline = TickerToThesisPipeline(ticker, thinking, config, emitter=emitter)

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
    finally:
        # Cleanup dashboard
        if dashboard_server:
            dashboard_server.stop()


if __name__ == "__main__":
    main()
