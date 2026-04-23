"""
Materials Analyst (Sub-Agent Architecture)
==========================================
Two-phase extraction:
  Phase 1: Parallel Sonnet sub-agents each read 3-4 documents by type,
           with type-specific primers and 2nd derivative focus.
  Phase 2: Single Opus consolidator reads all sub-agent extracts,
           cross-references, flags contradictions, produces final brief.

Output: ~40K char structured brief with [QUOTE]/[STATED]/[INFERRED] labels.
"""

import asyncio
import logging
from collections import defaultdict
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from agent_runner import AgentCall
from models import AgentReport, AgentRole

logger = logging.getLogger(__name__)


# =============================================================================
# Type-specific primers for sub-agents
# =============================================================================

# Maps materials_manager.DocumentType.value to primer text
DOC_TYPE_PRIMERS: Dict[str, str] = {
    "Earnings Transcript": """You are reading EARNINGS CALL TRANSCRIPTS.

Focus on extracting:
- **Guidance**: Specific revenue, margin, and growth targets. Note if guidance was raised, maintained, or lowered vs prior quarter.
- **Beat/Miss**: Actual results vs consensus/prior guidance. Quantify the delta.
- **2nd Derivative Signals**: Is revenue growth ACCELERATING or DECELERATING quarter-over-quarter? Are margins EXPANDING or COMPRESSING? Is guidance being RAISED or CUT? These inflection points matter more than the absolute numbers.
- **Management Tone**: Confidence level on calls — hedging language ("we expect", "we hope") vs conviction ("we will", "we're confident"). Note shifts in tone across quarters.
- **Key Metrics**: NRR, RPO, customer count, ARPU, churn — and whether each is improving or deteriorating sequentially.
- **Q&A Insights**: Analyst questions often probe weak spots. What did analysts push back on? What did management deflect or answer vaguely?
- **Competitor Mentions**: Any references to competitive wins/losses, pricing pressure, or market share shifts.""",

    "Expert Network": """You are reading EXPERT NETWORK TRANSCRIPTS (former employees, industry insiders, competitors).

Focus on extracting:
- **Competitive Intelligence**: Win/loss dynamics, product comparisons, customer switching behavior. These are primary-source insights unavailable in public filings.
- **Pricing & Margin Signals**: Are prices rising or falling in the market? Are customers pushing back on renewals? Is there a pricing war emerging or easing?
- **2nd Derivative Signals**: Is competitive positioning IMPROVING or DETERIORATING? Is the company gaining or losing share? Are customer conversations getting better or worse?
- **Inside Knowledge**: Operational issues, cultural problems, product gaps, or strengths that don't show up in financials.
- **Contradiction with Management**: Where does the expert's view diverge from what management says publicly? These divergences are high-signal.
- **Direct Quotes**: Expert opinions are uniquely valuable — capture exact words when they make strong claims.""",

    "SEC Filing": """You are reading SEC FILINGS (10-K, 10-Q).

Focus on extracting:
- **Segment Breakdowns**: Revenue, operating income, and growth by segment/product/geography. Track how mix is shifting.
- **2nd Derivative Signals**: Is segment growth accelerating or decelerating vs prior periods? Are gross margins expanding or compressing by segment? Is operating leverage improving?
- **Risk Factors**: Only extract SPECIFIC, MATERIAL risks — not boilerplate. Look for new risk factors added this quarter or risks with changed language.
- **Customer Concentration**: Top customer % of revenue, any named customers, concentration trends.
- **Accounting Changes**: Revenue recognition changes, impairments, restructuring charges, stock-based comp trends.
- **Balance Sheet Signals**: Cash burn rate trajectory, debt maturities, AR/DSO trends (leading indicator of revenue quality).
- **Quantitative Data Tables**: Extract exact figures for financial model inputs.""",

    "Sell-Side Research": """You are reading SELL-SIDE RESEARCH (broker reports, financial models).

⚠️ BIAS WARNING: The issuing firm may have banking relationships or trading interests. Extract facts and model assumptions — do NOT adopt conclusions uncritically.

Focus on extracting:
- **Model Assumptions**: Revenue growth rates, margin assumptions, and terminal value assumptions. What drives their price target?
- **2nd Derivative Signals**: Is the analyst RAISING or LOWERING estimates? Has the rating changed recently? Are estimates being revised up or down? What's the direction of estimate revisions across the street?
- **Bull/Bear Cases**: What scenarios does the analyst lay out? What are the key swing factors?
- **Consensus vs Variant**: Where does this analyst differ from consensus? What's their unique insight?
- **Valuation Multiples**: What comps/multiples are used? What peer group?
- **Financial Projections**: Extract specific numbers for revenue, EBITDA, FCF, EPS projections.""",

    "Investor Presentation": """You are reading INVESTOR PRESENTATIONS (conference decks, investor day materials).

Focus on extracting:
- **New Metrics or KPIs**: Companies often introduce new metrics at conferences when old metrics are deteriorating. Note what's NEW and what's been DROPPED.
- **2nd Derivative Signals**: Is the company's messaging becoming more or less confident? Are they emphasizing growth or profitability (pivot signal)? Are TAM estimates expanding or being walked back?
- **Product Roadmap**: New product announcements, launch timelines, early traction data.
- **Go-to-Market Changes**: Sales org restructuring, channel strategy shifts, international expansion — these signal where management sees opportunity or problems.
- **Competitive Positioning Claims**: How the company positions itself vs competitors. Cross-reference with expert network insights for reality check.
- **Financial Targets**: Medium-term financial targets, margin goals, rule-of-40 progress.""",

    "Merger/Proxy": """You are reading MERGER PROXY / DEF 14A filings.

Focus on extracting:
- **Deal Terms**: Price, premium, consideration mix (cash/stock), conditions, termination fees.
- **Fairness Opinion**: Valuation range, methodology, selected comparables, DCF assumptions.
- **Financial Projections**: Management projections provided to the board — these are the ONLY forward-looking projections with legal liability. Extremely high value.
- **Background of the Merger**: Timeline, competing bids, negotiation dynamics.
- **Board Recommendation**: Unanimous? Dissenting directors?""",

    "Other": """You are reading a GENERAL RESEARCH DOCUMENT.

Focus on extracting:
- Key facts, figures, and claims with source attribution.
- Any data points relevant to revenue trajectory, margin trends, or competitive dynamics.
- 2nd derivative signals: is the situation improving or deteriorating?""",

    "Competitor": """You are reading COMPETITOR DOCUMENTS (earnings transcripts, filings, or research for a company that competes with the focus company).

⚠️ The purpose of reading competitor docs is NOT to analyze the competitor as an investment. It is to understand the RELATIVE competitive position of the focus company.

Focus on extracting:
- **Revenue growth rates**: Is the competitor growing faster or slower than the focus company? Is the gap widening or narrowing? ⬆️⬇️🔄
- **Margin trajectory**: Are competitor margins expanding while focus company margins compress (or vice versa)? What does this imply about pricing power and cost structure?
- **Market share signals**: Is the competitor gaining share in segments where the focus company operates? Cite specific product overlap.
- **Pricing commentary**: Is the competitor raising prices (pricing power) or cutting them (competitive pressure)? How does this affect the focus company?
- **Product roadmap overlap**: Where is the competitor investing? Does this threaten or validate the focus company's strategy?
- **Customer wins/losses**: Any mentions of taking customers from (or losing to) the focus company?
- **Management commentary about the focus company**: Direct or indirect references to the competitive dynamic.

Frame everything RELATIVE to the focus company:
- "Competitor revenue grew 25% vs focus company's 11% — gap widening" ⬇️
- "Competitor gross margins compressed 300bp while focus company expanded 150bp — relative advantage improving" ⬆️""",
}

# Default primer for unknown types
DEFAULT_PRIMER = DOC_TYPE_PRIMERS["Other"]

# =============================================================================
# Shared extraction rules (injected into every sub-agent)
# =============================================================================

EXTRACTION_RULES = """
## LABELING RULES (MANDATORY)

Tag every fact with one of:
- **[QUOTE]** — Exact verbatim text from the source. Use quotation marks. Words inside MUST appear word-for-word in the document.
- **[STATED]** — A fact explicitly stated in the source, paraphrased. No quotation marks.
- **[INFERRED]** — Your conclusion from combining/interpreting info. Flag your reasoning.

⛔ DO NOT use [QUOTE] unless the exact words appear in the source.
⛔ DO NOT present inferences as stated facts.

## 2nd DERIVATIVE FOCUS (CRITICAL)

For every key metric, revenue line, and margin figure you extract, answer:
- **Direction**: Is it going UP or DOWN?
- **Rate of change**: Is the improvement/decline ACCELERATING or DECELERATING?
- **Inflection signals**: Any hints of a turning point — sequential improvement after declines, language shifts, new initiatives?

Flag these with ⬆️ (accelerating), ⬇️ (decelerating), or 🔄 (inflection point).

Examples:
- ⬆️ Revenue growth re-accelerated from 8% to 11% YoY [STATED] (transcript_Q4)
- ⬇️ Gross margin compressed 200bp sequentially despite revenue growth [STATED] (10-Q)
- 🔄 Management shifted language from "investing for growth" to "path to profitability" [INFERRED] (comparing Q2 vs Q4 presentations)
"""


# =============================================================================
# Consolidator prompt (Opus)
# =============================================================================

CONSOLIDATOR_SYSTEM_PROMPT = """You are a senior equity research analyst producing the final materials brief from sub-analyst extracts.

You are receiving pre-extracted notes from multiple junior analysts, each of whom read a subset of research documents. Your job is to:

1. **Cross-reference** across extracts — find contradictions, corroborations, and patterns
2. **Consolidate** financial data into unified tables with sources
3. **Highlight 2nd derivative signals** — where is momentum changing? Flag with ⬆️⬇️🔄
4. **Preserve labels** — keep [QUOTE], [STATED], [INFERRED] from sub-analysts. Add your own [INFERRED] when you draw cross-document conclusions.
5. **Flag contradictions** between sources with ⚠️ CONTRADICTION

## Output Structure

### Document Inventory
Table: filename | type | date | key topic

### Revenue & Growth Trajectory
- Revenue by segment/product with trend direction (⬆️⬇️🔄)
- Sequential and YoY growth rates — is growth accelerating or decelerating?
- Leading indicators: RPO, pipeline, bookings, NRR trends

### Margins & Profitability Trajectory
- Gross margin, operating margin, FCF margin trends
- Margin expansion or compression signals
- Operating leverage evidence

### Management Commentary & Guidance
- Key verbatim quotes (keep [QUOTE] labels)
- Guidance changes: raised, maintained, or lowered?
- Tone shifts across periods

### Competitive Dynamics
- Market share trends — gaining or losing?
- Pricing power signals
- Win/loss intelligence from expert network
- Competitor mentions and positioning

### Expert & Industry Intelligence
- Primary-source insights not available in public filings
- Where experts contradict management claims

### SEC Filing & Model Data
- Segment data, geographic mix, customer concentration
- Sell-side estimates and revisions direction

### 2nd Derivative Summary
Dedicated section: for each key metric, one line:
| Metric | Current | Trend | Acceleration | Signal Source |

### Contradictions & Open Questions
- Cross-source contradictions
- Unverified claims
- Data gaps

Target length: ~40,000 characters. Prioritize 2nd derivative signals and cross-source insights over raw data repetition."""


# =============================================================================
# Sub-agent grouping and execution
# =============================================================================

def _is_competitor_doc(filename: str, ticker: str) -> bool:
    """Check if a document is about a competitor (not the focus company).

    Convention: competitor docs should NOT contain the focus ticker in filename.
    e.g., transcript_NET_earnings_2026.md is a competitor doc when analyzing FSLY.
    Also matches explicit 'competitor_' prefix.
    """
    name_lower = filename.lower()
    # Strip exchange suffix (e.g., "UMG.AS" -> "umg", "7203.T" -> "7203")
    # so filenames tagged with the bare ticker still match.
    ticker_lower = ticker.lower().split(".")[0]

    # Explicit competitor prefix
    if name_lower.startswith("competitor_") or name_lower.startswith("comp_"):
        return True

    # If filename doesn't contain the focus ticker but contains another known
    # ticker-like pattern, treat as competitor
    # Check for common doc prefixes followed by a different ticker
    for prefix in ["transcript_", "10k_", "sec_", "sellside_", "presentation_", "expert_"]:
        if name_lower.startswith(prefix):
            # Extract the ticker part (e.g., "transcript_NET_..." -> "NET")
            remainder = name_lower[len(prefix):]
            parts = remainder.split("_")
            if parts and parts[0] != ticker_lower:
                return True

    return False


def _group_documents_by_type(
    materials_dir: Path,
    ticker: str = "",
) -> Dict[str, List[Tuple[str, str]]]:
    """Group .md files by document type, separating competitor docs.

    Returns:
        Dict mapping doc_type_value to list of (filename, content) tuples.
        Competitor docs are grouped under "Competitor" regardless of their doc type.
    """
    from materials_manager import MaterialsManager, DocumentType

    md_files = sorted(materials_dir.glob("*.md"))
    if not md_files:
        return {}

    # Use MaterialsManager's classification logic
    mm = MaterialsManager(materials_dir.parent, materials_dir=materials_dir)

    groups: Dict[str, List[Tuple[str, str]]] = defaultdict(list)

    for md_path in md_files:
        content = md_path.read_text(encoding="utf-8")
        if not content.strip():
            continue

        # Check if this is a competitor document
        if ticker and _is_competitor_doc(md_path.stem, ticker):
            groups["Competitor"].append((md_path.stem, content))
        else:
            doc_type = mm._classify_document(md_path, content)
            groups[doc_type.value].append((md_path.stem, content))

    return dict(groups)


def _build_subagent_call(
    doc_type: str,
    documents: List[Tuple[str, str]],
    ticker: str,
    call_index: int,
) -> AgentCall:
    """Build an AgentCall for a sub-agent reading a group of documents."""
    primer = DOC_TYPE_PRIMERS.get(doc_type, DEFAULT_PRIMER)

    docs_block = ""
    for filename, content in documents:
        docs_block += f"\n\n---\n\n## Document: {filename}\n\n{content}"

    total_chars = sum(len(c) for _, c in documents)
    doc_names = ", ".join(f for f, _ in documents)

    focus_note = ""
    if doc_type == "Competitor":
        focus_note = f"\n\nThe FOCUS COMPANY is {ticker}. Frame all competitor data RELATIVE to {ticker}."

    system_prompt = f"""{primer}

{EXTRACTION_RULES}{focus_note}

You are extracting from {len(documents)} {doc_type} document(s) for {ticker}.
Be thorough but selective. Every claim needs a [QUOTE], [STATED], or [INFERRED] label and source filename."""

    user_prompt = f"""Extract key facts, figures, and 2nd derivative signals from these {len(documents)} documents ({total_chars:,} chars total).

Documents: {doc_names}

{docs_block}

---

Produce your extraction now. Label every claim. Flag 2nd derivative signals with ⬆️⬇️🔄."""

    return AgentCall(
        role=AgentRole.MATERIALS_ANALYST,
        system_prompt=system_prompt,
        user_prompt=user_prompt,
        iteration=0,
        identifier=f"materials_sub_{call_index}_{doc_type.lower().replace(' ', '_')}",
        provider="claude-cli",
        model="sonnet",
    )


def _build_consolidator_call(
    sub_extracts: Dict[str, str],
    ticker: str,
) -> AgentCall:
    """Build the Opus consolidator call from sub-agent extracts."""
    extracts_block = ""
    for identifier, content in sub_extracts.items():
        extracts_block += f"\n\n---\n\n## Sub-Analyst Extract: {identifier}\n\n{content}"

    total_chars = sum(len(c) for c in sub_extracts.values())

    user_prompt = f"""Consolidate the following {len(sub_extracts)} sub-analyst extracts into a unified materials brief for {ticker}.

Total extract size: {total_chars:,} characters from {len(sub_extracts)} sub-analysts.

Cross-reference across extracts. Flag contradictions. Highlight 2nd derivative signals. Produce the final brief.

{extracts_block}

---

Produce the consolidated materials brief now."""

    return AgentCall(
        role=AgentRole.MATERIALS_ANALYST,
        system_prompt=CONSOLIDATOR_SYSTEM_PROMPT,
        user_prompt=user_prompt,
        iteration=0,
        identifier="materials_consolidator",
        provider="claude-cli",
        model="sonnet",
    )


# =============================================================================
# Main entry point
# =============================================================================

async def run_materials_analyst(
    materials_dir: Path,
    agent_runner,
    ticker: str,
) -> AgentReport:
    """Run the two-phase materials analyst pipeline.

    Phase 1: Parallel Sonnet sub-agents extract from grouped documents.
    Phase 2: Opus consolidator cross-references and produces final brief.

    Args:
        materials_dir: Path to the materials/ folder with extracted .md files.
        agent_runner: The pipeline's AgentRunner instance.
        ticker: Ticker symbol.

    Returns:
        AgentReport with the structured materials brief.
    """
    # Group documents by type (competitor docs detected by ticker mismatch)
    groups = _group_documents_by_type(materials_dir, ticker=ticker)
    if not groups:
        logger.warning("No extracted materials found — skipping materials analyst")
        from models import TokenUsage
        return AgentReport(
            role=AgentRole.MATERIALS_ANALYST,
            investing_type_id=None,
            iteration=0,
            content="",
            token_usage=TokenUsage(),
            error="No materials found",
        )

    total_docs = sum(len(docs) for docs in groups.values())
    total_chars = sum(len(c) for docs in groups.values() for _, c in docs)
    logger.info(
        f"Materials analyst: {total_docs} documents in {len(groups)} groups, "
        f"{total_chars:,} total chars"
    )
    for doc_type, docs in groups.items():
        doc_chars = sum(len(c) for _, c in docs)
        logger.info(f"  {doc_type}: {len(docs)} docs, {doc_chars:,} chars")

    # Phase 1: Build sub-agent calls (one per document type)
    sub_calls = []
    for i, (doc_type, documents) in enumerate(groups.items()):
        call = _build_subagent_call(doc_type, documents, ticker, i)
        sub_calls.append(call)

    logger.info(f"Phase 1: Running {len(sub_calls)} parallel sub-agents (Sonnet)...")
    sub_results = await agent_runner.run_parallel(sub_calls)

    # Collect successful extracts
    sub_extracts = {}
    for identifier, report in sub_results.items():
        if isinstance(report, AgentReport) and report.is_success:
            sub_extracts[identifier] = report.content
            logger.info(f"  ✓ {identifier}: {len(report.content):,} chars")
        elif isinstance(report, AgentReport):
            logger.warning(f"  ✗ {identifier}: {report.error}")
        else:
            # Handle case where result is an exception from gather
            logger.warning(f"  ✗ {identifier}: {report}")

    if not sub_extracts:
        logger.error("All sub-agents failed — no materials brief produced")
        from models import TokenUsage
        return AgentReport(
            role=AgentRole.MATERIALS_ANALYST,
            investing_type_id=None,
            iteration=0,
            content="",
            token_usage=TokenUsage(),
            error="All sub-agents failed",
        )

    total_extract_chars = sum(len(c) for c in sub_extracts.values())
    logger.info(
        f"Phase 1 complete: {len(sub_extracts)}/{len(sub_calls)} succeeded, "
        f"{total_extract_chars:,} chars total"
    )

    # Phase 2: Opus consolidator
    logger.info("Phase 2: Running Opus consolidator...")
    consolidator_call = _build_consolidator_call(sub_extracts, ticker)
    report = await agent_runner.run_single(consolidator_call)

    if report.is_success:
        logger.info(
            f"Materials brief generated: {len(report.content):,} chars, "
            f"{report.token_usage.total_tokens:,} tokens"
        )
    else:
        logger.warning(f"Consolidator failed: {report.error}")

    return report
