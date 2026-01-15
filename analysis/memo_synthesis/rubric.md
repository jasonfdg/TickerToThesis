# Scoring Rubric - Buyside Memo Engine v0.1.0

## Overview

This rubric scores buyside memos on 5 dimensions, each rated 1-10. The rubric is designed to be AI-executable while remaining human-readable.

**Important Caveats:**
- VIC community scores (1-10) are weak labels mixing quality, perceived edge, and outcome bias
- This rubric focuses on memo quality at time of writing, not subsequent performance
- High scores indicate decision-ready documents, not guaranteed returns

---

## Dimension 1: Variant View Clarity (Weight: 25%)

**Definition:** Does the memo clearly articulate what the market is missing and why the author has an edge?

### Scoring Anchors

| Score | Description |
|-------|-------------|
| **2** | No variant view. Memo presents bull/bear case without explaining why market is wrong. Generic "undervalued" claim. |
| **5** | Variant view stated but not proven. Author claims market is missing something but provides weak or no evidence. "The market doesn't understand X" without explaining why author does. |
| **8** | Variant view clearly stated AND proven with evidence. Author explains specific insight, sources of edge (primary research, proprietary data, expertise), and why this insight is not widely known. |
| **10** | Exceptional variant view with multiple sources of confirmation. Author demonstrates deep, differentiated insight that is both non-obvious and well-supported. Anticipates and addresses counter-arguments. |

### Detection Cues
- Look for: "market is missing", "mispriced because", "street gets wrong", "edge", "insight"
- Red flag: Generic claims like "undervalued on all metrics" without explanation
- Positive signal: Primary research cited, proprietary data, industry expertise stated

### Scoring Function
```python
def score_variant_view(memo):
    has_variant_statement = check_for_variant_keywords(memo)
    has_evidence = check_for_evidence_supporting_variant(memo)
    has_primary_research = check_for_primary_research(memo)
    addresses_counter = check_for_counter_argument_handling(memo)

    if not has_variant_statement:
        return 2
    elif has_variant_statement and not has_evidence:
        return 4
    elif has_variant_statement and has_evidence and not has_primary_research:
        return 6
    elif has_variant_statement and has_evidence and has_primary_research:
        return 8
    if addresses_counter:
        return min(10, score + 1)
```

---

## Dimension 2: Evidence Quality (Weight: 25%)

**Definition:** How specific and verifiable is the evidence? Does the memo rely on primary or secondary sources?

### Scoring Anchors

| Score | Description |
|-------|-------------|
| **2** | Vague qualitative claims. No specific data points. "The company has a strong brand" without support. |
| **5** | SEC filings and public data only. Specific numbers cited but all from 10-K/10-Q. No original analysis or primary sources. |
| **8** | Mix of public filings AND primary research. Channel checks, management conversations, industry expert calls, proprietary data analysis. Specific, verifiable claims. |
| **10** | Exceptional evidence quality. Multiple primary sources, cross-verified data, quantified insights that cannot be found elsewhere. Evidence is both deep and differentiated. |

### Detection Cues
- Keywords for primary: "spoke with", "channel check", "industry contact", "former employee", "site visit"
- Keywords for secondary: "10-K states", "according to filings", "management guide"
- Quantification: Specific numbers (revenue breakdown, margin analysis, unit economics)

### Evidence Type Hierarchy
1. **Primary** (highest value): Channel checks, management calls, expert network, site visits
2. **Proprietary analysis**: Original data analysis, alternative data, model building
3. **Secondary** (baseline): SEC filings, earnings calls, investor presentations
4. **Tertiary** (lowest value): Sell-side research, media articles

---

## Dimension 3: Valuation Rigor (Weight: 20%)

**Definition:** Is the valuation methodology sound, with explicit assumptions and appropriate sensitivity analysis?

### Scoring Anchors

| Score | Description |
|-------|-------------|
| **2** | No valuation or single vague metric. "Cheap at 10x earnings" with no context or assumptions. |
| **5** | Basic valuation with some context. Multiple comparisons (historical, peers) but assumptions not explicit. No sensitivity analysis. |
| **8** | Rigorous valuation with explicit assumptions. Multiple methods cross-checked. Key driver sensitivity shown. Target price derived from stated assumptions. |
| **10** | Exceptional valuation rigor. Bull/base/bear scenarios. Full sensitivity on key drivers. Explicit discussion of what's priced in vs. author's view. Margin of safety quantified. |

### Detection Cues
- Methods: EV/EBITDA, P/E, DCF, FCF yield, NAV, sum-of-parts
- Context: "vs. historical average of", "peers trade at", "implies X growth"
- Sensitivity: "if margins improve to X, worth Y", "upside/downside scenarios"

### Valuation Checklist
- [ ] Current multiples stated
- [ ] Historical context provided
- [ ] Peer comparison included
- [ ] Target price with assumptions
- [ ] At least one sensitivity analysis
- [ ] Discussion of what's "priced in"

---

## Dimension 4: Risk Honesty (Weight: 15%)

**Definition:** Are risks specific, honest, and do they include kill conditions (what would prove the thesis wrong)?

### Scoring Anchors

| Score | Description |
|-------|-------------|
| **2** | No risk section or generic risks only. "Competition could increase" or "macro could hurt." |
| **5** | Specific risks listed but no kill conditions. Risks acknowledged but not quantified or connected to thesis. No discussion of mitigants or monitoring. |
| **8** | Specific risks with kill conditions. Each risk is quantified where possible. Clear statements of "if X happens, thesis is wrong." Mitigants addressed. |
| **10** | Exceptional risk analysis. Risks quantified and probability-weighted. Clear kill conditions with monitoring metrics. Discussion of how author would know if wrong. Pre-mortem analysis. |

### Detection Cues
- Generic (bad): "competition", "recession", "management execution"
- Specific (good): "if gross margin falls below 30%", "if competitor launches X by Q2"
- Kill condition keywords: "would exit if", "thesis is wrong if", "deal-breaker"

### Risk Quality Checklist
- [ ] Risks are specific to this company (not generic)
- [ ] At least one risk addresses the core thesis
- [ ] Kill conditions defined (what would change your mind?)
- [ ] Mitigants discussed where applicable
- [ ] No obvious risks ignored

---

## Dimension 5: Decision Readiness (Weight: 15%)

**Definition:** Can a PM act on this memo? Does it include sizing guidance, timing, and exit criteria?

### Scoring Anchors

| Score | Description |
|-------|-------------|
| **2** | Memo ends without clear recommendation. No target price, timing, or actionable conclusion. Reader doesn't know what to do. |
| **5** | Clear directional view (long/short) with target price but no timing, sizing, or exit criteria. PM could act but lacks implementation guidance. |
| **8** | Actionable memo with target price, catalyst timing, and conviction level. PM can size position and knows what to monitor. Exit criteria stated. |
| **10** | Fully decision-ready. Target price with time horizon, conviction level with sizing suggestion, specific catalyst dates, clear exit criteria (price and event-based), monitoring framework. |

### Detection Cues
- Target: "worth $X" or "X% upside"
- Timing: "within X months", "by Q2", "when X happens"
- Conviction: "high conviction", "starter position", "full position"
- Exit: "sell at $X", "exit if", "reassess when"

### Decision Readiness Checklist
- [ ] Clear recommendation (long/short with target)
- [ ] Catalyst with timing
- [ ] Conviction level indicated
- [ ] Exit criteria defined
- [ ] What to monitor specified

---

## Overall Score Calculation

### Weighted Formula
```
Overall = (Variant × 0.25) + (Evidence × 0.25) + (Valuation × 0.20) +
          (Risk × 0.15) + (Decision × 0.15)
```

### Score Interpretation

| Overall | Interpretation |
|---------|----------------|
| 1-3 | Not decision-grade. Major gaps in thesis, evidence, or actionability. |
| 4-5 | Below average. Some substance but significant weaknesses. |
| 6-7 | Good. Decision-ready for further diligence but has gaps. |
| 8-9 | Excellent. High-quality, actionable memo with minor gaps. |
| 10 | Elite. Exceptional across all dimensions. Rare. |

---

## Handling Biases

### Outcome Bias
- Score based on memo quality at time of writing
- Do not let subsequent stock performance influence score
- A well-reasoned memo that was wrong is still high-quality

### Length Bias
- Long memos are not automatically better
- Score on substance density, not word count
- A concise memo with high density scores higher than verbose padding

### Confidence Theater
- Distinguish between genuine conviction and rhetorical confidence
- Penalize memos that assert without evidence
- Reward humble acknowledgment of uncertainty with specific bounds

### Rhetorical Polish
- Substance over style
- Well-written fluff scores low
- Poorly written but substantive memos score higher

---

## Tie-Breaker Rules

When two memos have the same overall score:

1. Prefer higher Variant View score (most differentiating)
2. Prefer higher Evidence Quality score
3. Prefer higher Risk Honesty score
4. If still tied, prefer shorter memo (efficiency)

---

## Calibration Examples

### Score 8+ Example Pattern
- Opens with specific thesis and variant view
- Cites primary research (calls, channel checks)
- Shows valuation math with assumptions
- Lists specific risks with kill conditions
- Ends with actionable recommendation and timing

### Score 4-5 Example Pattern
- Thesis stated but variant view weak or missing
- Relies on public filings only
- Valuation present but assumptions unclear
- Generic risks without kill conditions
- Directional view but no implementation guidance

### Score 2-3 Example Pattern
- No clear thesis or buried deep in memo
- Vague qualitative claims
- "Cheap" without context
- No risks or "competition might increase"
- No actionable conclusion
