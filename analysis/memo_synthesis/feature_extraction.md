# Feature Extraction Plan - Buyside Memo Engine v0.1.0

## Overview

This document defines how to detect core buyside qualities from memo text using heuristics, regex patterns, and model-assisted classification.

---

## Feature 1: Variant View Detection

### Operational Definition
A variant view is an explicit statement of what the market misunderstands about the company, combined with why the author has insight the market lacks.

### Heuristic Detection

**Positive Patterns (regex-style)**
```
market (is |does not |doesn't )?(understand|see|appreciate|recognize|get)
(street|consensus|analysts) (miss|ignore|overlook|underestimate)
mispriced because
undervalued due to
our edge (is|comes from)
we believe .* while (the )?market
what (the )?market (is )?missing
non-consensus view
variant perception
```

**Negative Patterns (false positives)**
```
# Generic without explanation
simply undervalued
cheap stock
low multiple
```

### Model-Assisted Classification

**Prompt template:**
```
Analyze this investment memo excerpt. Does it contain a variant view?

A variant view has TWO components:
1. Statement of what the market believes or is missing
2. Explanation of why the author has differentiated insight

Classify as:
- PROVEN_VARIANT: Both components present with evidence
- ASSERTED_VARIANT: Claim made but not proven
- NO_VARIANT: No variant view articulated

Excerpt: {memo_text}
```

### Gold-Label Examples

| Memo ID | Text Snippet | Label |
|---------|--------------|-------|
| 5650586949 | "Many believe this transaction will never happen and Agribrands will, instead, be sold" | PROVEN_VARIANT |
| 5661635680 | "Tell me what I am missing" | NO_VARIANT |
| 4005633636 | "The Street does not understand this company... This is genuinely worth a long look as a VALUE play" | ASSERTED_VARIANT |

---

## Feature 2: Evidence Specificity

### Operational Definition
Classify evidence as primary (original research), secondary (public filings), or tertiary (third-party analysis).

### Heuristic Detection

**Primary Evidence Keywords**
```
spoke with|talked to|called|met with
channel check|store visit|site visit
industry contact|former (employee|executive|manager)
proprietary (data|analysis|model)
expert network|expert call
our research indicates
we verified|confirmed through
```

**Secondary Evidence Keywords**
```
10-K|10-Q|8-K|proxy|annual report
SEC filing|company filings
earnings call|investor presentation|transcript
management guide|guidance
company disclosed|disclosed in
```

**Tertiary Evidence Keywords**
```
according to (analyst|sellside|broker|media)
research report|equity research
news article|press reported
```

### Quantification Markers
```
\$[\d,]+[MBK]?  # Dollar amounts
\d+\.?\d*%      # Percentages
\d+x            # Multiples
(revenue|EBITDA|margin|ROIC) of \d+
```

### Evidence Quality Score
```python
def score_evidence(memo):
    primary_count = count_matches(memo, PRIMARY_PATTERNS)
    secondary_count = count_matches(memo, SECONDARY_PATTERNS)
    quantified_claims = count_matches(memo, QUANT_PATTERNS)

    if primary_count >= 3 and quantified_claims >= 5:
        return "HIGH"
    elif primary_count >= 1 or quantified_claims >= 3:
        return "MEDIUM"
    else:
        return "LOW"
```

---

## Feature 3: Valuation Framing

### Operational Definition
Identify valuation methods used, key assumptions stated, and sensitivity analysis present.

### Method Detection Patterns

| Method | Pattern |
|--------|---------|
| EV/EBITDA | `EV/(EBITDA|Ebitda)|enterprise value.{0,20}EBITDA|\d+(\.\d+)?x EBITDA` |
| P/E | `P/E|price.{0,10}earnings|\d+(\.\d+)?x (earnings|EPS)` |
| DCF | `DCF|discounted cash flow|WACC|terminal value` |
| FCF Yield | `FCF yield|free cash flow yield|\d+% FCF` |
| NAV | `NAV|net asset value|liquidation value|book value` |
| Sum-of-Parts | `sum.of.parts|SOTP|segment.?by.?segment` |

### Assumption Detection
```
assum(e|ing|ption)
if .* then
scenario|case|bull|bear|base
sensitivity
upside.{0,20}downside
implies|implied
```

### Valuation Completeness Checklist
```python
def check_valuation(memo):
    return {
        "has_current_multiple": bool(re.search(r'currently trad(es|ing) at', memo)),
        "has_target": bool(re.search(r'(target|worth|value)\s+(of\s+)?\$\d+', memo)),
        "has_historical_context": bool(re.search(r'historical(ly)?|vs\.?\s*\d+.year', memo)),
        "has_peer_comparison": bool(re.search(r'peer|competitor|comp(arable)?s?\s+trad', memo)),
        "has_assumptions": bool(re.search(r'assum', memo, re.I)),
        "has_sensitivity": bool(re.search(r'sensitivity|if.*then|scenario', memo, re.I))
    }
```

---

## Feature 4: Risk / Kill Conditions

### Operational Definition
Distinguish between generic risks and specific kill conditions that would invalidate the thesis.

### Risk Section Detection
```
\n#+\s*risk|risks?\n|risks?:
things (that )?could go wrong
bear case
what (could|would) (go wrong|kill)
```

### Generic Risk Patterns (LOW value)
```
competition (could|may|might) increase
macro (environment|conditions|risk)
execution risk
management (could|may|might)
regulatory (risk|changes)
```

### Specific Risk Patterns (HIGH value)
```
if .* (drops|falls|declines) (below|under) \d+
if (revenue|margin|EBITDA) .* (below|under)
would exit if
thesis (is|would be) wrong if
deal.?breaker
kill condition
```

### Kill Condition Extraction
```python
def extract_kill_conditions(memo):
    patterns = [
        r"would (exit|sell|close) if (.+?)[\.\n]",
        r"thesis (is|would be) wrong if (.+?)[\.\n]",
        r"deal.?breaker:?\s*(.+?)[\.\n]",
        r"if (.+?), (we would|I would|will) (exit|sell|reassess)"
    ]
    return [match for pattern in patterns for match in re.findall(pattern, memo, re.I)]
```

---

## Feature 5: Catalyst Extraction

### Operational Definition
Identify catalysts with timing and assess whether they are measurable/verifiable.

### Catalyst Section Detection
```
\n#+\s*catalyst|catalysts?\n|catalysts?:
what (will|could) (unlock|drive|move)
near.?term (event|driver|catalyst)
timing|timeline
```

### Timing Patterns
```
Q[1-4]\s*\d{2,4}
(within|in)\s*\d+\s*(month|week|year|day)s?
by (year.?end|Q[1-4]|end of \d{4})
(this|next) (quarter|year|month)
(January|February|...|December)\s*\d{4}
\d{1,2}/\d{1,2}/\d{2,4}
```

### Catalyst Type Classification
```python
CATALYST_TYPES = {
    "earnings": r"earnings|results|report|quarter|guidance",
    "strategic": r"buyback|dividend|M&A|merger|acquisition|spin|split|sale",
    "regulatory": r"FDA|approval|regulatory|license|permit",
    "management": r"CEO|CFO|management|activist|board",
    "market": r"analyst day|investor day|coverage|initiation"
}
```

### Measurability Check
A catalyst is measurable if:
1. Has specific timing (date or quarter)
2. Has verifiable outcome (yes/no, number)
3. Not dependent on vague "market recognition"

---

## Feature 6: Decision Readiness

### Operational Definition
Assess whether memo provides actionable guidance: position sizing, entry/exit criteria, conviction level.

### Component Detection

**Target Price**
```
(target|worth|fair value|intrinsic value)\s*(of\s*)?\$\d+
(\d+%|\d+x)\s*(upside|return)
could (reach|hit|trade to)\s*\$\d+
```

**Conviction Level**
```
(high|low|medium|starter|full|core)\s*(conviction|position|sizing)
(confident|conviction) (level|is)
position size
```

**Exit Criteria**
```
(would|will) (exit|sell|close|trim) (at|if|when)
sell (at|above|if)
exit (criteria|trigger|price)
stop.?loss
```

**Time Horizon**
```
(hold for|holding period|time horizon)\s*\d+\s*(year|month)
(long.?term|short.?term|medium.?term)
patient investor
```

### Decision Readiness Score
```python
def score_decision_readiness(memo):
    score = 0
    if has_target_price(memo): score += 2
    if has_catalyst_timing(memo): score += 2
    if has_conviction_level(memo): score += 2
    if has_exit_criteria(memo): score += 2
    if has_time_horizon(memo): score += 2
    return score  # 0-10 scale
```

---

## Gold Labeling Strategy

### Approach
1. Manually label 20-30 memos across score range
2. Ensure coverage of all features
3. Use labels to calibrate heuristics and model prompts

### Labeling Template
```json
{
  "memo_id": "5650586949",
  "variant_view": "PROVEN",
  "variant_view_text": "Many believe this transaction will never happen...",
  "evidence_quality": "HIGH",
  "primary_sources": ["hedge fund letter", "proxy analysis"],
  "valuation_methods": ["ev_ebitda", "nav"],
  "has_sensitivity": true,
  "risk_quality": "HIGH",
  "kill_conditions": ["Stock falls below $39"],
  "catalyst_type": "strategic",
  "catalyst_timing": "Q4 2000",
  "decision_ready": true,
  "labeler": "human",
  "date": "2026-01-15"
}
```

### Inter-Rater Reliability
- Have 2+ labelers score same memos
- Calculate Cohen's kappa for each feature
- Revise definitions where kappa < 0.7

---

## Implementation Order

1. **Regex heuristics** - Fast, interpretable baseline
2. **Keyword counting** - Evidence quality, catalyst presence
3. **Model classification** - Variant view (nuanced), risk quality
4. **Gold labeling** - 20 examples minimum
5. **Calibration** - Adjust thresholds based on gold labels
6. **Validation** - Test on holdout set
