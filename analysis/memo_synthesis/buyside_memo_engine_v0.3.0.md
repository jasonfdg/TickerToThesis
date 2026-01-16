# Buyside Memo Engine - Instruction Manual v0.3.0

---

## A) Run Metadata

| Field | Value |
|-------|-------|
| **Timestamp** | 2026-01-16T12:30:00 (local) |
| **Run ID** | BME-v0.3.0-20260116 |
| **Output Version** | v0.3.0 |
| **Folder Scanned** | `/Users/chaukam/Developer/Analyst_framework_buildout/data/structured/` |
| **Previous Version Found** | `buyside_memo_engine_v0.2.0.md` (v0.2.0, 2026-01-15T22:15:00) |

### Files Analyzed

| Source | Count | Position Types | Score Range | Notable Files |
|--------|-------|----------------|-------------|---------------|
| VIC | 63 | 100% long | 3.2-7.0 | TPNL (6551745629), DIBS (8109588594), GOED (6132195543) |
| Hindenburg | 10 | 100% short | 5.6-7.2 | Axos (72369e7dc276), Sezzle (f1d58f8e4977) |
| **Total** | **73** | 86% long / 14% short | 3.2-7.2 | - |

### Summary Statistics

| Metric | v0.3.0 | v0.2.0 | Delta |
|--------|--------|--------|-------|
| **Total files analyzed** | 73 | 35 | +108% |
| **Files with scores** | 24 | 14 | +71% |
| **Short positions included** | 10 | 0 | **NEW** |
| **Total data size** | 2,424 KB | 760 KB | +219% |
| **Date range** | 2000-2024 | 2000-2023 | Extended |
| **Score range** | 3.2-7.2 | 3.2-7.0 | Extended |
| **Avg word count (shorts)** | 7,974 | N/A | **NEW** |
| **Avg word count (longs)** | 2,134 | 1,843 | +16% |

### Sampling Plan

- **Full analysis**: All 73 structured memos in folder
- **Deep-read**: 12 VIC memos (stratified by score) + 4 Hindenburg memos
- **Contrastive pairs**: Long vs Short structure analysis
- **New**: Short thesis pattern extraction from Hindenburg corpus

**Key Improvement from v0.2.0:** First inclusion of professional short-seller reports enables SHORT thesis taxonomy development.

---

## B) Diff vs v0.2.0

### 1. Schema Changes

- **(NEW)** Added `position_type_specific{}` object: Short and long memos have fundamentally different structures
- **(NEW)** Added `evidence_sources[]` array with source taxonomy: Hindenburg reports cite 5-21 sources per report
- **(NEW)** Added `insider_signals{}` object: Track Form 4s, margin loans, stock pledges
- **(NEW)** Added `competitive_benchmarks{}`: Peer comparison metrics (critical for shorts)
- **(NEW)** Added `thesis_lifecycle_stage`: pitch | update | exit
- **(UPDATED)** Enhanced `evidence.types[]` with Hindenburg source patterns

**Evidence:** Axos memo (7.2) cited 21 former employee interviews, property visits, litigation records.

### 2. Taxonomy Changes

- **(NEW)** Added **3 Short thesis categories** from Hindenburg analysis:
  - **Short - Hidden Risk Exposure**: Company exposed to undisclosed risks (Axos CRE)
  - **Short - Metric Manipulation**: Reported metrics don't match reality (Axos LTV ratios)
  - **Short - Insider Exodus**: Management cashing out via sales/margin loans (Sezzle)
- **(UPDATED)** Renamed "Short - Fraud" to "Short - Accounting Fraud" for precision
- **(NEW)** Added **Thesis Lifecycle States**: Initial Pitch → Update → Exit Recommendation

**Evidence:** Hindenburg Axos report combined all 3 short patterns. TPNL VIC memo showed full lifecycle from $2.45 pitch to $15+ exit recommendation.

### 3. Rubric Changes

- **(NEW)** Created **Position-Specific Scoring Anchors**:
  - Longs scored on: Growth drivers, management quality, competitive moat
  - Shorts scored on: Evidence forensics, metric suspicion, insider behavior
- **(UPDATED)** "Evidence Quality" now includes **source triangulation requirement**: Elite memos verify claims from 3+ independent sources
- **(NEW)** "Forensic Evidence" dimension for short reports specifically

**Evidence:** Hindenburg verified Axos loan problems via: (1) property records (2) lease agent calls (3) site visits (4) former employee interviews (5) litigation records.

### 4. Feature Extraction Changes

- **(NEW)** Added "Insider Behavior Detection": Form 4 filings, margin loan disclosures, stock pledge footnotes
- **(NEW)** Added "Competitive Metric Comparison": Compare key ratios to peer medians
- **(NEW)** Added "Source Triangulation Score": Count of independent verification sources
- **(NEW)** Added "Thesis Lifecycle Tracking": Initial vs Update vs Exit
- **(UPDATED)** "Primary Research" expanded with Hindenburg source hierarchy

**Evidence:** Sezzle memo identified $542M margin loan buried on page 42 of proxy statement.

### 5. Validation/Milestones Changes

- **(NEW)** Added short-specific validation: Can rubric distinguish genuine fraud exposure from promotional shorts?
- **(NEW)** Added lifecycle validation: Did memos with exit recommendations outperform holds?
- No roadmap changes

### 6. Latent Quality Promotions

- **(PROMOTED to Testing)** "Insider Behavior Signals": Margin loans and Form 4 patterns predictive
- **(PROMOTED to Testing)** "Competitive Metric Deviation": When company metrics deviate >20% from peer median, warrants scrutiny

---

## C) 12 Defining Traits of Elite Buyside Memos (Updated from 10)

### Universal Traits (Both Long and Short)

1. **(UNCHANGED)** **First-paragraph thesis clarity with conviction**: Elite memos state the core thesis definitively within the first 3 sentences. No hedging language.

2. **(UNCHANGED)** **Variant view is proven, not asserted**: Elite memos explain *why* the market is wrong with specific evidence.

3. **(UPDATED)** **Multi-source evidence triangulation**: Elite memos verify key claims from 3+ independent sources. Hindenburg standard: former employees + litigation + site visits + public filings.
   - *Change from v0.2.0: Expanded beyond "primary research citation" to explicit triangulation requirement*

4. **(UNCHANGED)** **Quantified evidence**: Elite memos use specific numbers (margins, revenue breakdown, unit economics).

5. **(UNCHANGED)** **Explicit valuation with multiple scenarios**: Elite memos show bull/base/bear cases or sensitivity analysis.

6. **(UNCHANGED)** **Specific risks with kill conditions**: Elite memos define "if X happens, thesis is wrong—exit."

7. **(UNCHANGED)** **Catalyst with timing**: Elite memos identify specific events with dates.

8. **(UPDATED)** **Decision-ready conclusions with asymmetric framing**: Elite memos quantify both upside AND downside. "$2 down, $20 up" (AGX) or "100% upside, limited downside to net cash" (DIBS).
   - *Change: Added asymmetry requirement beyond just downside floor*

### Long-Specific Traits

9. **(UPDATED)** **Growth driver decomposition**: Elite long memos break down revenue into components (centers × donations × price for TPNL). Shows understanding of business mechanics.
   - *Change from v0.2.0: Made explicit based on TPNL pattern*

10. **(NEW)** **Management and insider alignment assessment**: Elite long memos evaluate CEO track record, insider ownership %, recent purchases. TPNL: "CEO owns 21%, hasn't sold despite 10x price increase."

### Short-Specific Traits

11. **(NEW)** **Forensic evidence with source hierarchy**: Elite short memos follow evidence hierarchy: Litigation records > Former employee interviews > Site visits > Competitor calls > Public filings. Axos memo: 21 former employee interviews.

12. **(NEW)** **Insider exodus documentation**: Elite short memos track Form 4 sales, margin loans, stock pledges. Sezzle memo: "$542M margin loan (30% of shares) buried on page 42."

---

## D) Deliverables

### D1) Data Schema (v0.3.0)

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
    "type": "deep_value | turnaround | compounder | event_driven | short_hidden_risk | short_metric_manipulation | short_insider_exodus | short_accounting_fraud | short_overearning | short_decline",
    "conviction_level": "high | medium | low",
    "uncertainty_phrases_count": "number",
    "first_paragraph_complete": "boolean",
    "lifecycle_stage": "initial_pitch | update | exit_recommendation"
  },

  "valuation": {
    "methods": ["EV/EBITDA", "P/E", "DCF", "liquidation", "sum_of_parts", "peer_relative"],
    "scenarios_present": "boolean",
    "target_price": "number | null",
    "downside_floor": "number | null",
    "asymmetric_framing": "string | null"
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
    "types": ["10K", "channel_check", "management", "industry_expert", "supplier", "competitor", "former_employee", "litigation", "site_visit", "regulatory_filing"],
    "primary_research_count": "number",
    "direct_quotes_count": "number",
    "urls_cited": "number",
    "triangulation_score": "number (0-5)"
  },

  "evidence_sources": [
    {
      "source_type": "former_employee | litigation | site_visit | regulatory | customer_review | competitor_call | industry_data",
      "count": "number",
      "key_finding": "string"
    }
  ],

  "insider_signals": {
    "form_4_net_sales_90d": "number | null",
    "margin_loan_disclosed": "boolean",
    "shares_pledged_pct": "number | null",
    "insider_ownership_pct": "number | null",
    "recent_purchases": "boolean"
  },

  "competitive_benchmarks": {
    "metric_name": "string",
    "company_value": "number",
    "peer_median": "number",
    "deviation_pct": "number",
    "suspicion_flag": "boolean"
  },

  "metrics": {
    "word_count": "number"
  },

  "fraud_signals": {
    "auditor_concerns": "boolean",
    "management_verification_failed": "boolean",
    "metric_peer_deviation": "number | null"
  }
}
```

**Extraction notes (v0.3.0 additions):**
- `triangulation_score`: 0=single source, 3=three independent sources, 5=five+ sources (Hindenburg standard)
- `insider_signals`: Parse proxy footnotes for margin loans, Form 4s for sales
- `lifecycle_stage`: Detect "update", "still like", "exit" language patterns
- `competitive_benchmarks.suspicion_flag`: True if deviation >20% from peer median

---

### D2) Memo Taxonomy (v0.3.0)

**File:** `taxonomy.md`

10 categories (expanded from 7):

| Category | Position | When to Use | Key Template Elements | Example |
|----------|----------|-------------|----------------------|---------|
| **Deep Value / Asset Play** | Long | Stock below liquidation value | Balance sheet decomposition, component valuations | NDN, AGX |
| **Event-Driven / Catalyst Play** | Long | Merger, spin-off, activist | Timeline, downside floor, approval mechanics | AGX |
| **Turnaround / Special Situation** | Long | Restructuring, post-bankruptcy | Operational fix roadmap, management credibility | - |
| **Compounder / Quality Growth** | Long | Durable moat, reinvestment | Unit economics, TAM, competitive dynamics | TPNL |
| **Short - Hidden Risk Exposure** | Short | Company exposed to undisclosed risks | Risk decomposition, peer comparison, source triangulation | Axos (CRE exposure) |
| **Short - Metric Manipulation** | Short | Reported metrics don't match reality | Peer benchmarking, forensic analysis | Axos (LTV ratios) |
| **Short - Insider Exodus** | Short | Management cashing out | Form 4 analysis, margin loans, stock pledges | Sezzle |
| **Short - Accounting Fraud** | Short | Accounting manipulation | Evidence trail, auditor concerns, related party | - |
| **Short - Overearning** | Short | Peak cycle, unsustainable margins | Historical margin band, cycle position | - |
| **Short - Structural Decline** | Short | Secular headwinds | Disruption timeline, customer churn | Sezzle (merchant exodus) |

**(NEW) Three Short categories added** based on Hindenburg pattern analysis. Note: Many shorts combine multiple patterns (Axos = Hidden Risk + Metric Manipulation; Sezzle = Insider Exodus + Structural Decline).

---

### D3) Scoring Rubric (v0.3.0)

**File:** `rubric.md`

#### Universal Dimensions (All Memos)

| Dimension | Weight | What It Measures | v0.3.0 Changes |
|-----------|--------|------------------|----------------|
| **Variant View Clarity** | 25% | Is the edge articulated and proven? | No change |
| **Evidence Quality** | 25% | Primary vs secondary, triangulation | **Added triangulation requirement** |
| **Valuation Rigor** | 20% | Method, assumptions, scenarios | No change |
| **Risk Honesty** | 15% | Specific risks with kill conditions | No change |
| **Decision Readiness** | 15% | Actionable: sizing, timing, floor | No change |

#### Position-Specific Scoring Anchors

**Long Memos:**

| Score | Variant View | Evidence | Management |
|-------|--------------|----------|------------|
| 2 | Vague "undervalued" | SEC filings only | Not mentioned |
| 5 | Edge with rationale | Primary + secondary mix | Track record noted |
| 8 | Edge proven with disconfirming evidence | 3+ source triangulation | Alignment quantified |

**Short Memos:**

| Score | Variant View | Evidence | Insider Behavior |
|-------|--------------|----------|------------------|
| 2 | Promotional attack | Public filings only | Not analyzed |
| 5 | Specific risk identified | Former employees OR site visits | Form 4s tracked |
| 8 | Multiple risks with quantification | 5+ source forensic analysis | Margin loans + pledges documented |

---

### D4) Feature Extraction Plan (v0.3.0)

**File:** `feature_extraction.md`

12 features (expanded from 8):

| Feature | Detection Method | v0.3.0 Status |
|---------|------------------|---------------|
| Variant view | Keywords + LLM classification | No change |
| Evidence specificity | Primary/secondary hierarchy | No change |
| Thesis conviction | Uncertainty phrase count | No change |
| Valuation methods | Regex for EV/EBITDA, P/E, DCF | No change |
| Kill conditions | Pattern matching for exit triggers | No change |
| Catalyst timing | Date/quarter pattern extraction | No change |
| Direct quote attribution | Quote + speaker pattern | No change |
| Decision readiness | Checklist of required elements | No change |
| **Source triangulation** | Count unique source types cited | **NEW** |
| **Insider behavior** | Form 4, proxy footnote parsing | **NEW** |
| **Competitive benchmarking** | Peer comparison extraction | **NEW** |
| **Thesis lifecycle** | Update/exit language detection | **NEW** |

**Gold labeling strategy:** 50 manually labeled examples (expanded from 30, including 10 shorts).

---

### D5) Writing Playbook (v0.3.0)

**File:** `playbook.md`

**Core principles (updated for shorts):**

| # | Long Memos | Short Memos |
|---|------------|-------------|
| 1 | Lead with edge—no hedging | Lead with the hidden risk |
| 2 | Prove don't assert—cite sources | Triangulate—verify from 3+ sources |
| 3 | Show work—decompose growth drivers | Show forensics—site visits, calls, litigation |
| 4 | Define failure—specific kill conditions | Define the catalyst—what forces revaluation |
| 5 | Enable action—target, timing, floor | Track insiders—Form 4s, pledges, margin loans |
| 6 | Compare to peers—show relative value | Compare to peers—flag metric deviations |

**Anti-patterns (11 total):**

| Anti-Pattern | Type | Example | Fix |
|--------------|------|---------|-----|
| Uncertainty closing | Both | "Tell me what I'm missing" | State thesis definitively |
| Vague valuation | Both | "Undervalued" | Show specific multiples |
| Generic risks | Both | "Competition could increase" | Specific kill condition |
| Missing floor | Long | Upside only | Define downside protection |
| Anonymous sources | Both | "Channel checks suggest..." | Name source type |
| Length padding | Both | 4,000+ words without density | Tight structure |
| Length poverty | Both | <500 words | Minimum 800 words |
| Confidence theater | Both | Certainty without evidence | Conditional confidence |
| Post-hoc rationalization | Both | Using subsequent performance | Score at time of writing |
| **(NEW)** Single-source reliance | Short | One disgruntled employee | Triangulate with 3+ sources |
| **(NEW)** Missing peer comparison | Short | "Metrics look bad" | Compare to peer median |

---

### D6) Validation Plan (v0.3.0)

**File:** `validation.md`

**(NEW) Short validation tests:**

1. **Forensic quality test**: Do memos with 5+ source types outperform single-source shorts?
2. **Insider signal test**: Do shorts identifying margin loans/pledges have higher hit rates?
3. **Peer deviation test**: Do companies with >20% metric deviation from peers underperform?

**(NEW) Lifecycle validation:**

4. **Exit timing test**: Did authors who recommended exits at specific prices/conditions outperform holds?

All other validation methods unchanged from v0.2.0.

---

### D7) Roadmap (v0.3.0)

**File:** `roadmap.md`

| Milestone | Status | Target |
|-----------|--------|--------|
| Short thesis taxonomy | **COMPLETE** | v0.3.0 |
| 50-memo gold labeled set | In Progress | v0.4.0 |
| Insider signal extraction pipeline | In Progress | v0.4.0 |
| Cross-validate on Kerrisdale/Muddy Waters | Planned | v0.4.0 |

---

## E) Latent Quality Discovery Module (v0.3.0)

**File:** `latent_quality_module.md`

### Current State

| Hypothesis | Status | Evidence | Change |
|------------|--------|----------|--------|
| First-paragraph thesis | **Core** | No change | - |
| Evidence quantification | **Core** | No change | - |
| Thesis conviction signaling | **Core** | No change | - |
| Falsification framing | Testing | Insufficient data | - |
| Primary research quotes | Testing | Directionally positive | - |
| Catalyst timing | Testing | No change | - |
| Exit criteria | Testing | No change | - |
| Downside floor articulation | Testing | No change | - |
| **Source triangulation** | **Testing (NEW)** | Hindenburg standard: 5+ sources | New |
| **Insider behavior tracking** | **Testing (NEW)** | Sezzle margin loan discovery | New |
| **Competitive metric deviation** | **Testing (NEW)** | Axos LTV vs peer median | New |
| Position sizing | Watchlist | No change | - |
| Management assessment | Watchlist | No change | - |

### v0.3.0 Hypothesis Bank Entries

```json
{
  "hypothesis_id": "HYP-014",
  "name": "Source Triangulation",
  "status": "testing",
  "definition": "Memos that verify key claims from 3+ independent source types are more reliable than single-source memos",
  "detection_cues": ["former employees", "site visits", "litigation records", "competitor calls"],
  "evidence": {
    "case_study": "Axos memo used 5 source types: former employees (21), property records, site visits, lease agent calls, litigation",
    "preliminary_correlation": "TBD"
  },
  "testing_version": "v0.3.0",
  "evidence_source": "Hindenburg Axos (72369e7dc276)"
}
```

```json
{
  "hypothesis_id": "HYP-016",
  "name": "Insider Behavior Signals",
  "status": "testing",
  "definition": "Shorts identifying margin loans, stock pledges, or concentrated Form 4 sales have higher conviction signals",
  "detection_cues": ["margin loan", "pledged shares", "Form 4", "insider sales"],
  "evidence": {
    "case_study": "Sezzle: $542M margin loan (30% of shares) found on pg 42 of proxy + $71M insider sales",
    "preliminary_correlation": "TBD"
  },
  "testing_version": "v0.3.0",
  "evidence_source": "Hindenburg Sezzle (f1d58f8e4977)"
}
```

---

## F) Pitfalls & Compliance

All items unchanged from v0.2.0, plus:

**(NEW) F9) Short Bias Warning**

- **Problem:** Hindenburg reports are professional short-seller content with inherent bias
- **Mitigation:** Weight evidence quality over conclusion; verify triangulation independently

**(NEW) F10) Lifecycle Stage Bias**

- **Problem:** Exit recommendations made after large gains may have hindsight bias
- **Mitigation:** Evaluate thesis quality at each stage independently

---

## G) Short vs Long Structural Comparison (NEW)

| Element | Elite Long Memo | Elite Short Memo |
|---------|-----------------|------------------|
| **Opening** | Thesis + upside quantification | Risk exposure + downside quantification |
| **Evidence Style** | Industry expertise, management calls | Forensic: litigation, site visits, ex-employees |
| **Peer Analysis** | Competitive moat vs competitors | Metric suspicion vs peer medians |
| **Insider Focus** | Alignment (ownership %, purchases) | Exodus (Form 4 sales, margin loans, pledges) |
| **Valuation** | Upside scenarios with floor | Fair value vs current with catalyst to reprice |
| **Word Count** | 1,500-3,000 optimal | 5,000-12,000 (forensic depth) |

---

## Supporting Files

| File | Purpose | v0.3.0 Update |
|------|---------|---------------|
| `SYNTHESIS_PROMPT.md` | Reusable synthesis prompt | No change |
| `sampling_report.md` | Detailed file list | Updated with 73 files |
| `schema.json` | Data schema | **Major update: insider signals, evidence sources** |
| `taxonomy.md` | Memo type taxonomy | **Added 3 short categories** |
| `rubric.md` | Scoring rubric | **Position-specific anchors** |
| `feature_extraction.md` | Feature detection | **Added 4 new features** |
| `playbook.md` | Writing guidance | **Split long/short guidance** |
| `validation.md` | Evaluation methodology | **Added short + lifecycle tests** |
| `roadmap.md` | Implementation timeline | Updated |
| `latent_quality_module.md` | Self-upgrade mechanism | **3 new testing hypotheses** |
| `short_long_comparison.md` | Structural comparison | **NEW** |

---

## PDF Layout Notes

No changes from v0.2.0.

---

*Generated by Buyside Memo Engine v0.3.0*
*Run ID: BME-v0.3.0-20260116*
*Previous version: v0.2.0*
*Files analyzed: 73 (vs 35 in v0.2.0)*
*Key changes: Short thesis taxonomy (3 categories); 3 new features (triangulation, insider signals, peer benchmarks); Position-specific rubric anchors*
