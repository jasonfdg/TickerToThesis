#!/usr/bin/env python3
"""
Run only the synthesis phase (for when iterations are already complete).
Uses v2 merged prompt that includes polish - no separate polish step needed.

Now includes pre-synthesis debate extraction to force accountability for disagreements.
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


async def extract_analyst_positions(
    ticker: str,
    all_reports: dict,
    agent_runner: AgentRunner,
    prompt_loader: PromptLoader,
) -> str:
    """Extract analyst recommendations and key debates before synthesis.

    This forces the synthesis to acknowledge and address disagreements rather
    than picking whichever narrative is easiest to defend.
    """
    # Build the extraction prompt with all reports
    reports_section = ""
    for type_id in sorted(all_reports.keys()):
        type_name = INVESTING_TYPES[type_id]['name']
        reports_section += f"""
### Analyst {type_id}: {type_name}
{all_reports[type_id]}

---
"""

    extraction_prompt = f"""Analyze these analyst reports on {ticker} and extract a structured summary of positions and debates.

{reports_section}

## Instructions

Extract the following information in a structured format:

### 1. RECOMMENDATION TALLY

For each analyst, extract:
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
- Analyst #X ({type_name}) recommends [X] while [count] others recommend [Y]. Their key argument: [summary]

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

    extraction_report = await agent_runner.run_single(call)

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


async def run_synthesis(ticker: str, iteration: int = 2):
    """Run synthesis for a ticker that has completed iterations.

    Flow:
    1. Load all final analyst reports
    2. Extract analyst positions and key debates (forces accountability)
    3. Run synthesis with debate summary injected (must address disagreements)

    Uses v2 merged prompt - synthesis output is already polished and publication-ready.
    No separate polish step needed.
    """

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

    # NEW: Extract analyst positions and debates before synthesis
    logger.info("Extracting analyst positions and key debates...")
    debate_summary = await extract_analyst_positions(
        ticker, all_final_reports, agent_runner, prompt_loader
    )
    logger.info(f"Debate summary extracted: {len(debate_summary)} chars")

    # Save debate summary for debugging/audit
    debate_path = report_saver.output_dir / "interim" / "debate_summary.md"
    debate_path.parent.mkdir(parents=True, exist_ok=True)
    debate_path.write_text(debate_summary, encoding="utf-8")
    logger.info(f"Debate summary saved: {debate_path}")

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

    # Build user prompt WITH debate summary injected
    user_prompt = f"""## Task: Synthesize Final Investment View on {ticker}

---

## ⚠️ ANALYST POSITIONS & DEBATES (YOU MUST ADDRESS THESE)

The following positions and debates were extracted from the analyst reports.
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

## ANALYST REPORTS TO SYNTHESIZE

{combined_reports}

---

Please synthesize these analyst perspectives into a unified, publication-ready Research Director memo following your framework.

Remember: If your conclusion is consensus, you've added nothing.
But also: If your conclusion contradicts the majority without explanation, you've avoided the hard work.
"""

    # Run synthesis (v2 prompt produces polished output directly)
    logger.info("Running synthesis (v2 merged prompt - single step)...")
    call = AgentCall(
        role=AgentRole.RD_SYNTHESIS,
        system_prompt=system_prompt,
        user_prompt=user_prompt,
        iteration=1,
    )

    synthesis_report = await agent_runner.run_single(call)

    if not synthesis_report.is_success:
        raise RuntimeError(f"Synthesis failed: {synthesis_report.error}")

    # Save both raw synthesis and final memo (they're the same with v2)
    report_saver.save_synthesis(synthesis_report)

    # With v2 merged prompt, synthesis IS the final memo - no polish step needed
    final_path = get_final_memo_path(ticker)
    final_path.write_text(synthesis_report.content, encoding="utf-8")

    logger.info(f"Synthesis complete: {synthesis_report.token_usage.total_tokens:,} tokens")
    logger.info(f"Final memo saved: {final_path}")

    return final_path


if __name__ == "__main__":
    import sys
    ticker = sys.argv[1] if len(sys.argv) > 1 else "WU"
    iteration = int(sys.argv[2]) if len(sys.argv) > 2 else 2

    result = asyncio.run(run_synthesis(ticker, iteration))
    print(f"\nSuccess! Final memo: {result}")
