# Buyside Memo Engine - Instruction Manual v0.5.0

---

## A) Run Metadata

| Field | Value |
|-------|-------|
| **Timestamp** | 2026-01-16T18:00:00 (local) |
| **Run ID** | BME-v0.5.0-20260116-pershing |
| **Output Version** | v0.5.0 |
| **Folders Scanned** | `data/vic/`, `data/buyside_notes/`, `data/short_seller_research/structured/pershing_square_*` |
| **Previous Version Found** | `buyside_memo_engine_v0.4.0.md` (v0.4.0, 2026-01-16T15:45:00) |

### Files Analyzed

| Source | Count | Position Types | Date Range | Notable Patterns |
|--------|-------|----------------|------------|------------------|
| GitHub VIC | 13,635 | 91% long / 9% short | 2000-2022 | Contest winners (700) |
| Structured VIC | 73 | 86% long / 14% short | 2000-2024 | Quality scores |
| Buyside Notes | 50 | Mixed | Various | Berkshire letters |
| **Pershing Square** | **12** | **75% long / 17% activist / 8% short** | **2012-2025** | **Outcome tracking, concentrated positions, activist campaigns** |
| **Total** | **13,770** | - | 2000-2025 | - |

### Summary Statistics

| Metric | v0.5.0 | v0.4.0 | Delta |
|--------|--------|--------|-------|
| **Total files analyzed** | 13,770 | 13,758 | +12 |
| **Activist positions** | 2 (new) | 0 | **NEW CATEGORY** |
| **Outcome-tracked memos** | 12 | 0 | **NEW FEATURE** |
| **Concentrated ($1B+) positions** | 10 | N/A | **NEW METRIC** |
| **Political catalyst memos** | 1 | 0 | **NEW CATEGORY** |

### Key Finding: Pershing Square's Differentiated Approach

Pershing Square memos exhibit patterns rare in VIC corpus:
1. **Outcome documentation** - Every memo tracks win/loss with specific P&L
2. **Named executive catalysts** - Management changes with specific individuals proposed
3. **Concentrated conviction** - $1-4B positions signal extreme conviction
4. **Multi-year lifecycle** - Same positions tracked across 3-6 years
5. **Public campaign mechanics** - Different structure from private memos

---

## B) Diff vs v0.4.0

### 1. Schema Changes

- **(NEW)** Added `position_outcome{}` object: Win/loss tracking with P&L
- **(NEW)** Added `activist_campaign{}` object: Proxy contest mechanics, nominee slate
- **(NEW)** Added `position_sizing{}` object: Dollar amount, % of portfolio
- **(UPDATED)** Enhanced `thesis.type` enum with 4 new categories from Pershing Square
- **(NEW)** Added `catalyst.political_regulatory` boolean flag
- **(NEW)** Added `management_change_catalyst{}` object: Named executives, track record

**Evidence:** CP memo named Hunter Harrison as CEO candidate with specific track record (CN operating ratio). CMG memo tracked Brian Niccol appointment as catalyst.

### 2. Taxonomy Changes

- **(NEW)** Added **4 thesis categories** from Pershing Square analysis:
  - **Long - Activist / Management Change**: Proxy contest to install new leadership (CP, ADP)
  - **Long - Holding Company Discount**: Sum-of-parts below market value (BN, HHH)
  - **Long - Political / Regulatory Catalyst**: Government action unlocks value (FNMA/FMCC)
  - **Long - Crisis Recovery**: Contrarian entry during temporary crisis (CMG, GOOG)

- **(NEW)** Added **position_type: activist** as distinct from long/short

**Evidence:** CP explicitly labeled "activist" in source memo. BN thesis centers on 38% discount to sum-of-parts.

### 3. Rubric Changes

- **(NEW)** Added **"Outcome Documentation" dimension** (applicable to historical analysis): Does memo track actual P&L and lessons learned?
- **(NEW)** Added **"Position Sizing Conviction"** sub-dimension: Is dollar commitment commensurate with thesis quality?
- **(UPDATED)** "Catalyst Quality" now includes **political/regulatory catalysts** as valid category
- **(NEW)** Added **"Management Change Specificity"**: Named individual with track record vs generic "new management"

**Evidence:** Pershing Square's $2.6B profit on CP and ~$1B loss on HLF demonstrate outcome tracking value.

### 4. Feature Extraction Changes

- **(NEW)** Added "Outcome Tracking Detection": P&L disclosure, win/loss language
- **(NEW)** Added "Activist Campaign Detection": Proxy contest, nominee slate, vote threshold patterns
- **(NEW)** Added "Political Catalyst Detection": Administration, regulatory, legislation patterns
- **(NEW)** Added "Position Size Extraction": Dollar amounts, portfolio percentage
- **(NEW)** Added "Named Executive Detection": Specific individual + track record patterns
- **(NEW)** Added "Holding Company Analysis": NAV, sum-of-parts, discount language

**Evidence:** HLF memo explicitly stated "$1 billion short position." CP stated "$2.6 billion profit."

### 5. Validation/Milestones Changes

- **(NEW)** Added Pershing Square outcome validation: Do memos predict actual outcomes?
- **(NEW)** Added activist success correlation: Do specific patterns predict proxy success?
- **(NEW)** Added position sizing validation: Does size correlate with conviction quality?

### 6. Latent Quality Promotions

- **(PROMOTED to Testing)** "Named Executive Catalyst": Specific person + track record correlates with higher thesis quality
- **(PROMOTED to Testing)** "Outcome Documentation": Win/loss tracking enables learning loop
- **(NEW to Watchlist)** "Position Sizing as Signal": Concentrated positions may indicate higher conviction
- **(NEW to Watchlist)** "Political Catalyst Specificity": Administration-specific timing vs vague "regulatory change"

---

## C) 12 Defining Traits of Elite Buyside Memos (Updated)

### v0.4.0 Traits (1-10) + v0.5.0 Additions (11-12)

1-10. **[UNCHANGED from v0.4.0]** - See v0.4.0 for full descriptions

11. **(NEW)** **Named executive catalyst with track record**: Elite activist memos name specific individuals. "Hunter Harrison, retired CEO of CN, achieved industry-leading operating ratio of 60" (CP). Not "experienced management candidate."

12. **(NEW)** **Outcome tracking with lessons learned**: Elite investors document wins and losses. "$2.6 billion profit" (CP), "~$1 billion loss" (HLF), "substantial loss as Valeant's business practices came under scrutiny" (VRX). Enables continuous improvement.

### Pershing Square Pattern Frequencies

| Trait | Pershing Square (n=12) | v0.4.0 Winner Baseline |
|-------|------------------------|----------------------|
| First-paragraph thesis with valuation | 100% | 89% |
| Explicit "why mispriced" section | 83% | 76% |
| Asymmetric framing quantified | 75% | 78% |
| Named executive catalyst | 42% | N/A (new) |
| Outcome documentation | 100% | 0% (new) |
| Position size disclosed | 92% | ~5% |
| Political/regulatory catalyst | 8% | ~2% |
| Holding company NAV analysis | 25% | ~3% |

---

## D) Deliverables

### D1) Data Schema (v0.5.0)

**File:** `schema.json`

```json
{
  // ... [ALL v0.4.0 fields retained] ...

  "position_outcome": {
    "status": "win | loss | mixed | ongoing",
    "realized_pnl_usd": "number | null",
    "realized_pnl_pct": "number | null",
    "exit_date": "ISO date | null",
    "outcome_notes": "string | null",
    "lessons_learned": "string | null"
  },

  "activist_campaign": {
    "is_activist": "boolean",
    "campaign_type": "proxy_contest | public_letter | settlement | private_engagement",
    "nominee_slate": ["string"],
    "proposed_changes": ["management_change", "operational_improvement", "capital_return", "strategic_restructuring"],
    "vote_threshold_required": "string | null",
    "campaign_outcome": "won | lost | settled | withdrawn | ongoing"
  },

  "position_sizing": {
    "initial_size_usd": "number | null",
    "initial_size_shares": "number | null",
    "portfolio_pct": "number | null",
    "conviction_tier": "concentrated | core | starter",
    "sizing_rationale": "string | null"
  },

  "management_change_catalyst": {
    "is_primary_catalyst": "boolean",
    "proposed_executive": "string | null",
    "executive_track_record": "string | null",
    "prior_company": "string | null",
    "prior_outcome_metric": "string | null"
  },

  "holding_company_analysis": {
    "is_holding_company": "boolean",
    "nav_per_share": "number | null",
    "discount_to_nav_pct": "number | null",
    "sum_of_parts_components": [
      {
        "component": "string",
        "value_usd": "number",
        "ownership_pct": "number"
      }
    ]
  },

  "political_catalyst": {
    "has_political_catalyst": "boolean",
    "catalyst_type": "administration_change | legislation | regulatory_action | privatization | other",
    "administration_dependency": "string | null",
    "timing_estimate": "string | null"
  }
}
```

### D2) Memo Taxonomy (v0.5.0)

**File:** `taxonomy.md`

18 categories (expanded from 14):

| Category | Position | When to Use | Key Template Elements | Corpus Examples |
|----------|----------|-------------|----------------------|-----------------|
| **[14 categories from v0.4.0]** | - | - | - | - |
| **Long - Activist / Management Change** | Activist | Proxy contest to install new leadership | Nominee slate, operating metrics target, vote mechanics | CP (2012), ADP (2017) |
| **Long - Holding Company Discount** | Long | Sum-of-parts exceeds market value | NAV calculation, discount %, catalyst to close gap | BN (2024), HHH (2025) |
| **Long - Political / Regulatory Catalyst** | Long | Government action unlocks value | Administration analysis, regulatory timeline, policy risk | FNMA/FMCC (2025) |
| **Long - Crisis Recovery** | Long | Contrarian entry during temporary crisis | Brand durability, recovery timeline, new management | CMG (2016), GOOG (2023) |

#### Activist / Management Change Template
```
1. THESIS (1-2 paragraphs)
   - Current management failure (specific metrics)
   - Proposed solution (named executive + track record)
   - Target outcome (operating ratio, margin, etc.)

2. UNDERPERFORMANCE ANALYSIS
   - Peer comparison (e.g., CP vs CN operating ratios)
   - Shareholder returns vs index/peers
   - Missed opportunities under current leadership

3. MANAGEMENT SOLUTION
   - Proposed executive: [Name]
   - Track record: [Prior company, specific achievements]
   - Why this person is the solution

4. OPERATIONAL IMPROVEMENTS
   - Specific initiatives (with quantified targets)
   - Timeline for implementation
   - Cost savings / margin expansion potential

5. PROXY MECHANICS
   - Current ownership position
   - Vote threshold required
   - Likely shareholder support analysis

6. VALUATION
   - Current vs transformed valuation
   - Peer multiples at target operating metrics
   - Downside protection if proxy fails

7. RISKS
   - Board entrenchment
   - Execution risk on turnaround
   - Union/operational disruption
```

#### Holding Company Discount Template
```
1. THESIS
   - Current market price vs NAV
   - Discount % and why it exists
   - Catalyst to close discount

2. SUM-OF-PARTS ANALYSIS
   - Component 1: [Asset] - Value: $X, Ownership: Y%
   - Component 2: [Asset] - Value: $X, Ownership: Y%
   - Total NAV vs current market cap

3. WHY DOES THIS DISCOUNT EXIST?
   - Complexity/opacity
   - Forced selling dynamics
   - Governance concerns
   - Lack of analyst coverage

4. CROWN JEWEL ANALYSIS
   - Identify highest-value component
   - Comparable company analysis
   - Growth trajectory

5. CATALYST TO CLOSE GAP
   - Simplification/spinoff potential
   - Improved disclosure
   - Share buyback at discount
   - Strategic alternatives

6. VALUATION
   - Bear: Discount persists
   - Base: Partial discount closure
   - Bull: Full NAV realization

7. RISKS
   - Discount widens
   - NAV impairment
   - Governance/related party issues
```

#### Political / Regulatory Catalyst Template
```
1. THESIS
   - Specific government action required
   - Probability assessment
   - Timeline to resolution

2. POLITICAL LANDSCAPE
   - Current administration position
   - Key decision-makers and their views
   - Legislative/regulatory pathway

3. SCENARIO ANALYSIS
   - Base: Most likely outcome
   - Bull: Favorable resolution
   - Bear: Unfavorable or no action

4. VALUATION BY SCENARIO
   - Value if favorable action
   - Value if status quo
   - Value if adverse action

5. CATALYSTS & TIMELINE
   - Key decision dates
   - Election/appointment impacts
   - Regulatory process steps

6. RISKS
   - Political risk (administration change)
   - Timeline slippage
   - Adverse outcome
   - Legal challenges
```

---

### D3) Scoring Rubric (v0.5.0)

**File:** `rubric.md`

#### Dimension Weights (Updated for v0.5.0)

| Dimension | Weight | What It Measures | v0.5.0 Change |
|-----------|--------|------------------|---------------|
| **Variant View Clarity** | 28% | Is the edge articulated and proven? | -2% (to accommodate new dimensions) |
| **Evidence Quality** | 18% | Primary vs secondary, triangulation | -2% |
| **Opportunity Articulation** | 10% | Why does this mispricing exist? | No change |
| **Valuation Rigor** | 14% | Method, assumptions, scenarios | -1% |
| **Risk Honesty** | 10% | Specific risks with kill conditions | No change |
| **Decision Readiness** | 14% | Actionable: sizing, timing, floor | -1% |
| **Catalyst Specificity** | 6% | Named events, timing, mechanism | **NEW (expanded from sub-dimension)** |

**Activist-Specific Scoring Adjustments:**

| Sub-Dimension | Activist Memo Weight | Standard Memo Weight |
|---------------|---------------------|---------------------|
| Named executive with track record | 15% | N/A |
| Proxy mechanics analysis | 10% | N/A |
| Operational improvement quantification | 15% | N/A |
| Peer underperformance evidence | 10% | N/A |

#### Scoring Anchors (Activist Memos - NEW)

| Score | Management Solution | Proxy Mechanics | Operational Targets |
|-------|--------------------|-----------------|--------------------|
| 2 | "New management needed" | Not discussed | Vague "improvements" |
| 5 | Named candidate, general experience | Vote threshold mentioned | Category targets (margins) |
| 8 | Named candidate + specific track record + prior outcome metrics | Full proxy analysis with shareholder support mapping | Specific metrics (OR from 81 to 65) |

#### Scoring Anchors (Holding Company - NEW)

| Score | NAV Analysis | Discount Explanation | Catalyst to Close |
|-------|--------------|---------------------|------------------|
| 2 | "Trades below parts" | Not discussed | "Market will realize" |
| 5 | Components listed | Category named | General timeline |
| 8 | Full sum-of-parts with comparables | Multiple factors with remedies | Specific mechanism + timing |

---

### D4) Feature Extraction Plan (v0.5.0)

**File:** `feature_extraction.md`

22 features (expanded from 16):

| Feature | Detection Method | v0.5.0 Status | Validation |
|---------|------------------|---------------|------------|
| [16 features from v0.4.0] | - | Unchanged | - |
| **Outcome tracking** | P&L, profit/loss, win/success/failure patterns | **NEW** | Pershing Square: 100% |
| **Activist campaign detection** | Proxy, nominee, board seat, vote patterns | **NEW** | CP, ADP validation |
| **Named executive extraction** | [Name] + CEO/CFO + prior company patterns | **NEW** | CP: Hunter Harrison |
| **Position size extraction** | $X billion/million + stake/position patterns | **NEW** | Pershing Square: 92% |
| **Political catalyst detection** | Administration, privatization, regulation patterns | **NEW** | FNMA/FMCC validation |
| **Holding company NAV** | NAV, sum-of-parts, discount patterns | **NEW** | BN, HHH validation |

**New Extraction Heuristics:**

**Outcome Tracking Detection:**
```
PATTERNS = [
  "profit of",
  "loss of",
  "gained",
  "returned",
  "exited with",
  "outcome:",
  "result:",
  "ultimately successful",
  "ultimately unsuccessful"
]
```

**Activist Campaign Detection:**
```
PATTERNS = [
  "proxy contest",
  "proxy fight",
  "nominee slate",
  "board seat",
  "shareholder vote",
  "dissident slate",
  "activist campaign"
]
```

**Named Executive Extraction:**
```
PATTERNS = [
  "[Name], (former|retired|ex-) (CEO|COO|CFO) of",
  "recruited [Name]",
  "proposed [Name] as",
  "[Name]'s track record at [Company]"
]
```

**Political Catalyst Detection:**
```
PATTERNS = [
  "administration",
  "privatization",
  "conservatorship",
  "regulatory action",
  "legislation",
  "Treasury",
  "FHFA",
  "government action"
]
```

---

### D5) Writing Playbook (v0.5.0)

**File:** `playbook.md`

#### Universal Principles (Updated)

| # | Principle | Do This | Not This |
|---|-----------|---------|----------|
| 1-8 | [From v0.4.0] | - | - |
| 9 | **(NEW)** Name the executive | "Hunter Harrison, retired CEO of CN, achieved 60.7 OR" | "Experienced operator" |
| 10 | **(NEW)** Document outcomes | "CP: $2.6B profit, exited Aug 2016" | Silent on results |
| 11 | **(NEW)** Size positions deliberately | "$2.3B position, 20.25% of portfolio" | "Significant stake" |
| 12 | **(NEW)** Analyze political dynamics | "Trump committed to privatization. Bessent indicated tax reform first." | "Government may act" |

#### Activist Memo Drafting Workflow (NEW)

```
PHASE 1: UNDERPERFORMANCE DOCUMENTATION
□ Identify specific metric gaps vs peers (operating ratio, margins, ROIC)
□ Quantify shareholder value destruction vs index/peers
□ Document management missteps with specifics

PHASE 2: MANAGEMENT SOLUTION
□ Identify candidate with proven track record
□ Document prior achievements with metrics
□ Explain why this person is credible for this situation

PHASE 3: OPERATIONAL ROADMAP
□ List specific initiatives (not generic "cost cuts")
□ Quantify targets (OR from 81 to 65, margins +500bps)
□ Estimate timeline for implementation

PHASE 4: PROXY MECHANICS
□ Current ownership position
□ Required vote threshold
□ Map likely shareholder support (institutions, index, arb)
□ Identify potential opposition

PHASE 5: VALUATION AT TRANSFORMATION
□ Current multiple vs transformed multiple
□ Peer trading at target operating metrics
□ Downside if proxy fails (floor protection)

PHASE 6: RISK MAPPING
□ Board entrenchment tactics
□ Execution risk on turnaround
□ Operational disruption during transition
□ What if proxy loses? (ADP outcome)
```

#### Anti-Patterns (15 total, +2 from v0.4.0)

| Anti-Pattern | Type | Example | Fix |
|--------------|------|---------|-----|
| [13 from v0.4.0] | - | - | - |
| **(NEW)** Generic management solution | Activist | "Need new leadership" | Name candidate with track record |
| **(NEW)** Undocumented outcomes | All | Silent on win/loss | Track P&L and lessons learned |

---

## E) Latent Quality Discovery Module (v0.5.0)

### Current State

| Hypothesis | Status | Evidence | v0.5.0 Change |
|------------|--------|----------|---------------|
| [All v0.4.0 hypotheses] | - | - | - |
| **Named executive catalyst** | **Testing (NEW)** | CP: 100%, ADP: 100% of activist memos | Specific person + track record |
| **Outcome documentation** | **Testing (NEW)** | Pershing Square: 100% | Enables learning loop |
| **Position sizing disclosure** | **Watchlist (NEW)** | Pershing Square: 92% | May signal conviction |
| **Political catalyst specificity** | **Watchlist (NEW)** | FNMA/FMCC: administration-specific | vs vague "regulatory" |
| **Holding company NAV disclosure** | **Watchlist (NEW)** | BN: 38% discount, HHH: Berkshire model | Sum-of-parts methodology |

### v0.5.0 Hypothesis Bank Additions

```json
{
  "hypothesis_id": "HYP-023",
  "name": "Named Executive Catalyst",
  "status": "testing",
  "definition": "Activist memos that name specific executives with track records demonstrate higher thesis quality",
  "detection_cues": ["[Name], former CEO of", "recruited [Name]", "track record at"],
  "evidence": {
    "pershing_square_activist": "100% (2/2)",
    "vic_activist_sample": "TBD"
  },
  "testing_version": "v0.5.0",
  "evidence_sources": ["CP (2012) - Hunter Harrison", "ADP (2017) - Bill Ackman nominee slate"]
}
```

```json
{
  "hypothesis_id": "HYP-024",
  "name": "Outcome Documentation",
  "status": "testing",
  "definition": "Memos that track realized P&L and lessons learned enable continuous improvement",
  "detection_cues": ["profit of $", "loss of $", "exited with", "outcome:"],
  "evidence": {
    "pershing_square": "100% (12/12)",
    "vic_corpus": "~0%"
  },
  "testing_version": "v0.5.0",
  "evidence_sources": ["CP ($2.6B profit)", "HLF (~$1B loss)", "VRX (substantial loss)"]
}
```

```json
{
  "hypothesis_id": "HYP-025",
  "name": "Position Sizing as Signal",
  "status": "watchlist",
  "definition": "Concentrated positions ($1B+) may indicate higher conviction and thesis quality",
  "detection_cues": ["$X billion position", "X% of portfolio"],
  "evidence": {
    "pershing_square": "92% (11/12) disclose size",
    "correlation_with_outcome": "TBD"
  },
  "testing_version": "v0.5.0",
  "evidence_sources": ["HLF ($1B short)", "UBER ($2.3B)", "BN ($2.6B)"]
}
```

---

## F) Pitfalls & Compliance (v0.5.0)

All items from v0.4.0, plus:

**(NEW) F14) Survivorship Bias in Outcome Tracking**

- **Problem:** Pershing Square selectively publishes outcomes; losses may be underreported in public materials
- **Mitigation:** Cross-reference with 13F filings and third-party tracking

**(NEW) F15) Activist Strategy Not Universally Applicable**

- **Problem:** CP/ADP patterns require significant capital and public platform not available to all investors
- **Mitigation:** Flag activist patterns as institutional-specific; separate rubric for retail-applicable memos

**(NEW) F16) Political Catalyst Unpredictability**

- **Problem:** FNMA/FMCC thesis depends entirely on government action; impossible to model reliably
- **Mitigation:** Political catalysts should have explicit probability discounting in valuation

---

## G) Pershing Square Case Studies (NEW)

### Case Study 1: Canadian Pacific Railway (CP) - Activist Success

| Element | Detail |
|---------|--------|
| **Entry** | Sept 2011 @ $47.72 |
| **Position** | 14.2% of voting shares, largest shareholder |
| **Thesis Category** | Long - Activist / Management Change |
| **Named Executive** | Hunter Harrison (retired CEO of CN) |
| **Key Metric Target** | Operating ratio: 81.3 → 65 |
| **Proxy Outcome** | Won (90% shareholder support) |
| **Financial Outcome** | $2.6B profit, stock $47.72 → $241 |
| **Lessons** | Named executive with specific track record + quantified target = credible thesis |

### Case Study 2: Herbalife (HLF) - Short Failure

| Element | Detail |
|---------|--------|
| **Entry** | Dec 2012 @ ~$42-45 |
| **Position** | $1B short position |
| **Thesis Category** | Short - Hidden Risk (Pyramid Scheme) |
| **Public Campaign** | 334-slide, 3-hour presentation |
| **Counterparty** | Carl Icahn, Daniel Loeb took opposing long positions |
| **Regulatory Outcome** | FTC required restructuring + $200M settlement, NOT classified as pyramid |
| **Financial Outcome** | ~$1B loss, exited 2018 |
| **Lessons** | Short thesis requires regulatory cooperation; public campaign invites opposition |

### Case Study 3: Chipotle (CMG) - Crisis Recovery Success

| Element | Detail |
|---------|--------|
| **Entry** | Q3-Q4 2016 @ ~$405 |
| **Position** | ~10% of float, $1.19B |
| **Thesis Category** | Long - Crisis Recovery |
| **Crisis** | 2015 E. coli outbreaks; stock from $748 → $375 |
| **Key Catalyst** | Brian Niccol appointed CEO (March 2018) |
| **Financial Outcome** | 770% stock increase during Niccol tenure |
| **Lessons** | Brand durability + management change = crisis recovery thesis |

### Case Study 4: Alphabet (GOOG) - Contrarian Success

| Element | Detail |
|---------|--------|
| **Entry** | Early 2023 @ ~$94-95 (16x P/E) |
| **Position** | 18.5%+ of portfolio |
| **Thesis Category** | Long - Crisis Recovery (AI fears) |
| **Contrarian View** | Market wrong about AI disruption; Google is AI winner |
| **Financial Outcome** | +30% since entry |
| **Lessons** | Temporary fear creates opportunity in high-quality businesses |

---

## H) Summary of v0.5.0 Changes

### Schema Additions
| Object | Purpose | Source Evidence |
|--------|---------|-----------------|
| `position_outcome{}` | Win/loss tracking | All 12 Pershing Square |
| `activist_campaign{}` | Proxy mechanics | CP, ADP |
| `position_sizing{}` | Dollar amounts | 11/12 Pershing Square |
| `management_change_catalyst{}` | Named executives | CP, CMG |
| `holding_company_analysis{}` | NAV methodology | BN, HHH |
| `political_catalyst{}` | Government action | FNMA/FMCC |

### Taxonomy Additions
| Category | Position Type | Examples |
|----------|--------------|----------|
| Activist / Management Change | activist | CP, ADP |
| Holding Company Discount | long | BN, HHH |
| Political / Regulatory Catalyst | long | FNMA/FMCC |
| Crisis Recovery | long | CMG, GOOG |

### Rubric Updates
- Catalyst Specificity promoted to standalone dimension (6%)
- Activist-specific scoring adjustments
- Holding company-specific scoring adjustments

### Feature Additions
- Outcome tracking detection
- Activist campaign detection
- Named executive extraction
- Position size extraction
- Political catalyst detection
- Holding company NAV extraction

---

## Supporting Files

| File | Purpose | v0.5.0 Update |
|------|---------|---------------|
| `schema.json` | Data schema | **6 new objects** |
| `taxonomy.md` | Memo type taxonomy | **4 new categories** |
| `rubric.md` | Scoring rubric | **Activist/holding company adjustments** |
| `feature_extraction.md` | Feature detection | **6 new features** |
| `playbook.md` | Writing guidance | **4 new principles, 2 anti-patterns, activist workflow** |
| `pershing_square_case_studies.md` | Case studies | **NEW** |

---

*Generated by Buyside Memo Engine v0.5.0*
*Run ID: BME-v0.5.0-20260116-pershing*
*Previous version: v0.4.0*
*Files analyzed: 13,770 (13,758 from v0.4.0 + 12 Pershing Square)*
*Key changes: Position outcome tracking; Activist thesis category; Holding company analysis; Political catalyst; Named executive extraction; 4 case studies with lessons learned*
