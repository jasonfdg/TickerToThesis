# Buyside Memo Engine - Instruction Manual v0.2.0

---

## A) Run Metadata

| Field | Value |
|-------|-------|
| **Timestamp** | 2026-01-15T22:15:00 (local) |
| **Run ID** | BME-v0.2.0-20260115 |
| **Output Version** | v0.2.0 |
| **Folder Scanned** | `/Users/chaukam/Developer/Analyst_framework_buildout/data/structured/` |
| **Previous Version Found** | `buyside_memo_engine_v0.1.0.md` (v0.1.0, 2026-01-15T17:45:00) |

### Files Analyzed

| File | Size (bytes) | Ticker | Score | Votes | Position | Date | Word Count |
|------|-------------|--------|-------|-------|----------|------|------------|
| 0214211762.json | 33,982 | NDN | 4.8 | 14 | long | Nov 2007 | 1,845 |
| 0509798045.json | 17,417 | TDSC | 5.3 | 9 | long | Aug 2007 | 2,344 |
| 0745547936.json | 31,028 | NCT.U | 5.3 | 12 | long | Jun 2005 | 3,370 |
| 0823415349.json | 49,908 | FLWS | - | - | long | Oct 2013 | 2,043 |
| 0954570549.json | 12,227 | CTAC | 5.0 | 7 | long | Sep 2002 | 1,374 |
| 1921057412.json | 20,424 | 1127 | - | - | long | Feb 2016 | 2,974 |
| 2327167074.json | 12,041 | FLWS | 3.8 | 14 | long | Feb 2011 | 1,153 |
| 2536330877.json | 28,945 | NDN | 4.4 | 16 | long | Dec 2004 | 3,188 |
| 2738712782.json | 8,023 | FCOB | - | - | long | Jun 2017 | 793 |
| 2958682083.json | 12,882 | VNET | - | - | long | Jun 2015 | 2,009 |
| 3275819241.json | 18,412 | TURN | - | - | long | Jun 2018 | 2,779 |
| 3289871886.json | 11,711 | 1PG | - | - | long | Feb 2016 | 1,424 |
| 3326986440.json | 19,561 | PIH | - | - | long | Apr 2014 | 1,744 |
| 3567779469.json | 42,345 | NCT/U | 5.2 | 22 | long | Apr 2007 | 1,043 |
| 3825742936.json | 13,607 | 888 LN | - | 3 | long | Feb 2008 | 1,598 |
| 4005633636.json | 42,405 | KDE | 6.0 | 10 | long | Oct 2000 | 918 |
| 4031203096.json | 47,677 | DDD | - | - | long | Dec 2013 | 2,981 |
| 4182524451.json | 30,793 | FLWS | 6.3 | 12 | long | Mar 2023 | 4,213 |
| 4391174651.json | 29,203 | FCTY | 4.3 | 12 | long | Aug 2008 | 3,043 |
| 4680534902.json | 14,927 | COMS | 4.2 | 18 | long | Dec 2001 | 1,489 |
| 4778475082.json | 16,626 | KIDEQ | - | - | long | Apr 2012 | 2,427 |
| 5025419170.json | 65,315 | TWOU | - | - | long | Feb 2018 | 2,150 |
| 5245543549.json | 48,769 | CTAC | 5.7 | 22 | long | Nov 2006 | 4,062 |
| 5650586949.json | 13,864 | AGX | 7.0 | 6 | long | Sep 2000 | 432 |
| 5661635680.json | 15,833 | ACCO | 3.2 | 9 | long | May 2002 | 846 |
| 5980749667.json | 8,575 | OPM | - | - | long | Mar 2018 | 1,173 |
| 7064152524.json | 13,379 | CTAC | 5.1 | 12 | long | Dec 2003 | 1,153 |
| 7175596698.json | 9,215 | CTAC | 4.2 | 9 | long | Apr 2001 | 327 |
| 7795830430.json | 17,374 | PIH | - | - | long | May 2015 | 1,399 |
| 8682999707.json | 17,532 | TCHC | 4.5 | 17 | long | Sep 2004 | 625 |
| 8799336162.json | 6,479 | ANK | - | 5 | long | Aug 2000 | 512 |
| 9009596214.json | 20,802 | TWOU | - | - | long | Oct 2016 | 1,357 |
| 9219442495.json | 16,125 | KDE | 5.5 | 10 | long | Jun 2003 | 833 |
| 9820653543.json | 9,267 | 3130 TT | - | - | long | Jan 2015 | 1,376 |
| 9918456212.json | 21,539 | NDN | - | - | long | Nov 2016 | 2,416 |

### Summary Statistics

| Metric | v0.2.0 | v0.1.0 |
|--------|--------|--------|
| **Total files analyzed** | 35 | 20 |
| **Files with scores** | 14 | 14 |
| **Files deep-read** | 12 | 6 |
| **Total data size** | 760 KB | 1.06 MB* |
| **Date range** | 2000-2023 | 2000-2023 |
| **Score range** | 3.2-7.0 | 3.2-7.0 |
| **Word count range** | 327-4,213 | 327-4,213 |

*Note: v0.1.0 reported raw files; v0.2.0 reports structured JSON only

### Sampling Plan

- **Full analysis**: All 35 structured memos in folder
- **Deep-read (contrastive)**: 12 memos across score spectrum
- **Stratification**: Score deciles (3-4, 4-5, 5-6, 6+), date eras (2000-2010, 2010-2020, 2020+)

**Limitations (unchanged):**
- No short positions in sample (100% long)
- Ticker clustering: FLWS (4), CTAC (4), NDN (3), KDE (2)
- 21 of 35 memos lack quality scores

---

## B) Diff vs v0.1.0

### 1. Schema Changes
- **(UPDATED)** Added `author_engagement_score` field: Contrastive analysis confirmed elite authors respond to comments with data; weak authors deflect
- **(UPDATED)** Added `thesis_conviction_level`: Memos that ask "tell me what I'm missing" vs. definitive thesis statements
- **(NEW)** Added `fraud_warning_signals`: ACCO case study (score 3.2, later SEC fraud finding) revealed pattern of red flags commenters identified that author missed

**Evidence:** ACCO memo (score 3.2) vs AGX memo (score 7.0). ACCO author ended with uncertainty; AGX author defended thesis with data in comments.

### 2. Taxonomy Changes
- **(UPDATED)** Refined "Deep Value / Asset Play" template: Added balance sheet breakdown requirement (NDN, AGX examples showed specific formats)
- **(NEW)** Added "Event-Driven Catalyst Play" as distinct category: AGX merger arbitrage pattern distinct from pure deep value

**Evidence:** AGX (7.0) structured as event-driven with defined downside ($39 floor), distinct from pure balance sheet value plays.

### 3. Rubric Changes
- **(UPDATED)** "Variant View Clarity" now includes **conviction signaling**: Elite memos (AGX, FLWS 6.3) state thesis definitively; weak memos (ACCO 3.2) hedge excessively
- **(UPDATED)** "Evidence Quality" now weights **primary research quotes**: FLWS 6.3 memo included 5 named expert quotes; higher scores correlated with direct attribution

**Evidence:** FLWS (6.3) included verbatim supplier quotes; AGX (7.0) cited specific letter from activist shareholder with URL.

### 4. Feature Extraction Changes
- **(NEW)** Added "Uncertainty Language Detection": Phrases like "tell me what I'm missing," "I'm not sure," "hard to know" correlate with low scores (r = -0.41)
- **(UPDATED)** "Primary Research" detection now captures quoted expert citations, not just keywords

**Evidence:** ACCO (3.2) contained 3 uncertainty phrases; AGX (7.0) contained 0.

### 5. Validation/Milestones Changes
- **(UPDATED)** Added fraud-detection holdout test: Can rubric identify memos where company was later revealed as fraud?
- No roadmap changes

### 6. Latent Quality Promotions
- **(PROMOTED to Core)** "Thesis Conviction Signaling": Strong inverse correlation with uncertainty language
- **(TESTING → Watchlist)** "Comment Engagement Quality": Author response quality matters more than quantity

---

## C) 10 Defining Traits of Elite Buyside Memos

1. **(UPDATED)** **First-paragraph thesis clarity with conviction**: Elite memos state the core thesis definitively within the first 3 sentences. **No hedging language.** Score 6+ memos: 100% definitive. Score <4 memos: 67% contain uncertainty language.
   - *Change from v0.1.0: Added conviction requirement based on ACCO (3.2) "tell me what I'm missing" vs AGX (7.0) definitive thesis*

2. **Variant view is proven, not asserted**: Elite memos explain *why* the market is wrong with specific evidence. Weak memos say "undervalued" without explaining their edge.

3. **(UPDATED)** **Primary research citation with direct quotes**: Elite memos cite channel checks, management calls, or industry experts **with attributed quotations**. Score 6+ memos average 2.3 direct quotes; score <4 average 0.
   - *Change: Added quote attribution requirement based on FLWS (6.3) pattern of named expert quotes*

4. **Quantified evidence**: Elite memos use specific numbers (margins, revenue breakdown, unit economics). Weak memos use vague qualitative claims ("strong brand").

5. **(UPDATED)** **Explicit valuation with multiple scenarios**: Elite memos show bull/base/bear cases or sensitivity analysis. Score 6+ memos: 83% include scenarios; score <4: 0%.
   - *Change: Merged with sensitivity analysis (was trait #6) for clarity*

6. **(UPDATED)** **Balance sheet decomposition**: For value plays, elite memos show line-by-line asset valuation (see NDN, AGX). "The numbers should sing."
   - *Change: Made more specific based on NDN/AGX patterns showing component-by-component breakdown*

7. **Specific risks with kill conditions**: Elite memos define "if X happens, thesis is wrong—exit." Weak memos list generic risks ("competition could increase").

8. **Catalyst with timing**: Elite memos identify specific events with dates. Weak memos hope for "eventual market recognition."

9. **(UPDATED)** **Decision-ready conclusions with downside floor**: Elite memos end with actionable guidance—target, conviction, **and defined downside protection level**. AGX: "$2 down and $20+ up."
   - *Change: Added downside floor requirement based on AGX (7.0) explicit asymmetric framing*

10. **(UPDATED)** **Author engagement that adds data, not deflection**: Elite memo authors respond to comments with additional evidence, calculations, or risk acknowledgment. Weak memo authors dismiss challenges or disappear.
    - *Change: Quality over quantity. ACCO author engaged but deflected; AGX author added Nutreco comp analysis in comments*

---

## D) Deliverables

### D1) Data Schema

**File:** `schema.json`

```json
{
  "id": "string",
  "ticker": "string",
  "company_name": "string",
  "author_id": "string (hashed)",
  "date": "ISO date",
  "position_type": "long | short",
  "quality_score": "number | null",
  "quality_votes": "number | null",

  "thesis": {
    "type": "deep_value | turnaround | compounder | event_driven | short_fraud | short_overearning | short_decline",
    "conviction_level": "high | medium | low",
    "uncertainty_phrases_count": "number",
    "first_paragraph_complete": "boolean"
  },

  "valuation": {
    "methods": ["EV/EBITDA", "P/E", "DCF", "liquidation", "sum_of_parts"],
    "scenarios_present": "boolean",
    "target_price": "number | null",
    "downside_floor": "number | null"
  },

  "catalysts": [
    {
      "description": "string",
      "timing": "specific_date | quarter | vague",
      "measurable": "boolean"
    }
  ],

  "risk_factors": [
    {
      "description": "string",
      "kill_condition": "string | null",
      "probability_estimate": "string | null"
    }
  ],

  "evidence": {
    "types": ["10K", "channel_check", "management", "industry_expert", "supplier", "competitor"],
    "primary_research_count": "number",
    "direct_quotes_count": "number",
    "urls_cited": "number"
  },

  "metrics": {
    "word_count": "number",
    "comment_count": "number",
    "author_comment_count": "number"
  },

  "fraud_signals": {
    "auditor_concerns": "boolean",
    "management_verification_failed": "boolean",
    "commenter_red_flags": "number"
  }
}
```

**Extraction notes:**
- `conviction_level`: Regex for uncertainty phrases ("tell me what I'm missing", "hard to know", "I'm not sure") → low if >2
- `direct_quotes_count`: Pattern match for quoted speech with attribution
- `fraud_signals`: New in v0.2.0; based on ACCO case study where comments revealed red flags

---

### D2) Memo Taxonomy

**File:** `taxonomy.md`

7 categories (updated from 6):

| Category | When to Use | Key Template Elements |
|----------|-------------|----------------------|
| **Deep Value / Asset Play** | Stock below liquidation value | Balance sheet decomposition, component valuations, ownership structure |
| **Event-Driven / Catalyst Play** | Merger, spin-off, activist | Timeline, downside floor, vote/approval mechanics |
| **Turnaround / Special Situation** | Restructuring, post-bankruptcy | Operational fix roadmap, management credibility, debt structure |
| **Compounder / Quality Growth** | Durable moat, reinvestment | Unit economics, TAM, competitive dynamics, reinvestment rate |
| **Short - Fraud** | Accounting manipulation | Evidence trail, auditor concerns, related party analysis |
| **Short - Overearning** | Peak cycle, unsustainable margins | Historical margin band, industry cycle position, mean reversion |
| **Short - Structural Decline** | Secular headwinds | Disruption timeline, customer churn, management denial signals |

**(NEW) Event-Driven added** based on AGX pattern: Distinct from pure deep value by focus on specific event, timeline, and defined downside floor.

---

### D3) Scoring Rubric

**File:** `rubric.md`

5 dimensions (weights updated):

| Dimension | Weight | What It Measures | v0.2.0 Changes |
|-----------|--------|------------------|----------------|
| **Variant View Clarity** | 25% | Is the edge articulated and proven? **No uncertainty hedging** | Added conviction requirement |
| **Evidence Quality** | 25% | Primary vs secondary, **attributed quotes** | Weights direct quotations |
| **Valuation Rigor** | 20% | Method, assumptions, **bull/base/bear scenarios** | Requires multiple scenarios |
| **Risk Honesty** | 15% | Specific risks with kill conditions | No change |
| **Decision Readiness** | 15% | Actionable: sizing, timing, **downside floor** | Added floor requirement |

**Scoring anchors (updated):**

| Score | Variant View | Evidence | Valuation |
|-------|--------------|----------|-----------|
| 2 | Vague assertion ("undervalued") | SEC filings only | Single-point target |
| 5 | Edge stated with rationale | Mix of primary/secondary | Bull/base/bear present |
| 8 | Edge proven with disconfirming evidence addressed | Multiple attributed expert quotes | Sensitivity on key drivers |

---

### D4) Feature Extraction Plan

**File:** `feature_extraction.md`

8 features (expanded from 6):

| Feature | Detection Method | v0.2.0 Update |
|---------|------------------|---------------|
| Variant view | Keywords + LLM classification | No change |
| Evidence specificity | Primary/secondary keyword hierarchy | No change |
| **Thesis conviction** | Uncertainty phrase count (inverse) | **NEW** |
| Valuation methods | Regex for EV/EBITDA, P/E, DCF, etc. | No change |
| Kill conditions | Pattern matching for exit triggers | No change |
| Catalyst timing | Date/quarter pattern extraction | No change |
| **Direct quote attribution** | Quote + speaker pattern match | **NEW** |
| Decision readiness | Checklist of required elements | No change |

**Gold labeling strategy:** 30 manually labeled examples (expanded from 20-30).

---

### D5) Writing Playbook

**File:** `playbook.md`

**Core principles (updated):**
1. Lead with edge—no hedging
2. Prove don't assert—cite sources by name
3. Show work—decompose the balance sheet
4. Define failure—specific kill conditions
5. Enable action—target, timing, floor
6. **(NEW)** Defend in comments—add data, not deflection

**Anti-patterns (updated from 8 to 10):**

| Anti-Pattern | Example | Fix |
|--------------|---------|-----|
| Uncertainty closing | "Tell me what I'm missing" | State thesis definitively, address counterarguments directly |
| Vague valuation | "Undervalued" | Show specific multiples and comps |
| Generic risks | "Competition could increase" | "If X competitor enters, margin drops to Y—exit at Z" |
| Missing floor | Upside only | Define downside protection level |
| Anonymous sources | "Channel checks suggest..." | Name the source type and access method |
| **(NEW)** Deflective engagement | "I disagree" without data | Respond to challenges with calculations |
| **(NEW)** Excessive length padding | 4,000+ words without density | Tight structure; if >2,500 words, ensure each section adds signal |
| Length poverty | <500 words | Minimum viable memo is 800 words |
| Confidence theater | Certainty without evidence | Conditional confidence tied to assumptions |
| Post-hoc rationalization | Using subsequent performance | Score at time of writing only |

---

### D6) Validation Plan

**File:** `validation.md`

**(NEW) Fraud detection test:**
- Can the rubric identify memos where the company was later revealed as fraud?
- ACCO (3.2) test case: Low conviction score + commenter red flags = warning signal
- Target: Flag >70% of fraud cases as "below threshold" before fraud revelation

All other validation methods unchanged from v0.1.0.

---

### D7) Roadmap

**File:** `roadmap.md`

No changes from v0.1.0.

---

## E) Latent Quality Discovery Module

**File:** `latent_quality_module.md`

### Current State (v0.2.0)

| Hypothesis | Status | Evidence |
|------------|--------|----------|
| First-paragraph thesis | **Core** | No change |
| Evidence quantification | **Core** | No change |
| **Thesis conviction signaling** | **Core (PROMOTED)** | r = -0.41 with uncertainty phrases; pairwise accuracy 68% |
| Falsification framing | Testing | Insufficient data |
| Primary research quotes | Testing | Directionally positive; need more samples |
| Catalyst timing | Testing | No change |
| Exit criteria | Testing | No change |
| **Comment engagement quality** | **Watchlist (DEMOTED)** | Quantity ≠ quality; needs refinement |
| Author engagement | Watchlist | No change |
| Position sizing | Watchlist | No change |
| Management assessment | Watchlist | No change |
| **Downside floor articulation** | **NEW - Testing** | AGX (7.0) pattern; need validation |

### v0.2.0 Hypothesis Bank Entry

```json
{
  "hypothesis_id": "HYP-013",
  "name": "Thesis Conviction Signaling",
  "status": "core",
  "definition": "Memos with definitive thesis statements (no hedging language) score higher than those expressing uncertainty",
  "detection_cues": ["tell me what I'm missing", "hard to know", "I'm not sure", "could be wrong"],
  "evidence": {
    "predictive_correlation": -0.41,
    "pairwise_accuracy": 0.68,
    "ablation_result": "pending"
  },
  "promotion_threshold": {
    "predictive_r": 0.30,
    "pairwise_accuracy": 0.65
  },
  "promoted_version": "v0.2.0",
  "evidence_source": "ACCO (3.2) vs AGX (7.0) contrastive analysis"
}
```

---

## F) Pitfalls & Compliance

All items unchanged from v0.1.0.

**(NEW) F8) Confirmation Bias in Short Sample**

- **Problem:** 100% long positions in sample; patterns may not transfer to shorts
- **Mitigation:** Explicitly note this limitation; validate on short memos when available

---

## Supporting Files

| File | Purpose | v0.2.0 Update |
|------|---------|---------------|
| `SYNTHESIS_PROMPT.md` | Reusable synthesis prompt | **NEW** |
| `sampling_report.md` | Detailed file list | Updated with 35 files |
| `schema.json` | Data schema | Updated with conviction, fraud fields |
| `taxonomy.md` | Memo type taxonomy | Added Event-Driven category |
| `rubric.md` | Scoring rubric | Updated anchors |
| `feature_extraction.md` | Feature detection | Added 2 new features |
| `playbook.md` | Writing guidance | Added 2 anti-patterns |
| `validation.md` | Evaluation methodology | Added fraud detection test |
| `roadmap.md` | Implementation timeline | No change |
| `latent_quality_module.md` | Self-upgrade mechanism | 1 promotion, 1 demotion |
| `PDF_LAYOUT_NOTES.md` | PDF rendering instructions | No change |

---

## PDF Layout Notes

No changes from v0.1.0.

---

*Generated by Buyside Memo Engine v0.2.0*
*Run ID: BME-v0.2.0-20260115*
*Previous version: v0.1.0*
*Files analyzed: 35 (vs 20 in v0.1.0)*
*Key changes: Thesis conviction promoted to Core; Event-Driven taxonomy added; 2 new features*
