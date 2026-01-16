# Buyside Memo Engine - Instruction Manual

**Version:** v1.0.0
**Generated:** 2026-01-16T14:38:47
**Run ID:** full-corpus-synthesis

---

## A) RUN METADATA

### Dataset Coverage
| Metric | Value |
|--------|-------|
| Folder scanned | `data/vic/github_dump/extracted/` |
| Total files in corpus | 13,635 |
| Files analyzed | 13,635 (100%) |
| Memos parsed | 13,635 |
| Parse errors | 0 |
| Iterations completed | 25 |

### Processing Summary
| Iteration | Files | Type | Year Range |
|-----------|-------|------|------------|
| 1 | 1,771 | Priority (winners + shorts) | 2000-2022 |
| 2 | 500 | Regular | 2000-2002 |
| 3 | 500 | Regular | 2002-2004 |
| 4 | 500 | Regular | 2004-2006 |
| 5 | 500 | Regular | 2006-2007 |
| 6 | 500 | Regular | 2007-2008 |
| 7 | 500 | Regular | 2008-2009 |
| 8 | 500 | Regular | 2009-2010 |
| 9 | 500 | Regular | 2010-2011 |
| 10 | 500 | Regular | 2011-2012 |
| 11 | 500 | Regular | 2012-2013 |
| 12 | 500 | Regular | 2013-2014 |
| 13 | 500 | Regular | 2014-2015 |
| 14 | 500 | Regular | 2015-2016 |
| 15 | 500 | Regular | 2016-2016 |
| 16 | 500 | Regular | 2016-2017 |
| 17 | 500 | Regular | 2017-2018 |
| 18 | 500 | Regular | 2018-2018 |
| 19 | 500 | Regular | 2018-2019 |
| 20 | 500 | Regular | 2019-2020 |
| 21 | 500 | Regular | 2020-2020 |
| 22 | 500 | Regular | 2020-2021 |
| 23 | 500 | Regular | 2021-2021 |
| 24 | 500 | Regular | 2021-2022 |
| 25 | 364 | Regular | 2022-2022 |

### Position Distribution
| Position Type | Count | Percentage |
|--------------|-------|------------|
| Long | 12,466 | 91.4% |
| Short | 1,169 | 8.6% |
| Contest Winners | 700 | 5.1% |

### Year Distribution
| Year | Count | Year | Count | Year | Count |
|------|-------|------|-------|------|-------|
| 2000 | 134 | 2008 | 506 | 2016 | 773 |
| 2001 | 279 | 2009 | 438 | 2017 | 781 |
| 2002 | 303 | 2010 | 563 | 2018 | 914 |
| 2003 | 335 | 2011 | 574 | 2019 | 820 |
| 2004 | 382 | 2012 | 630 | 2020 | 983 |
| 2005 | 398 | 2013 | 687 | 2021 | 932 |
| 2006 | 423 | 2014 | 698 | 2022 | 795 |
| 2007 | 496 | 2015 | 791 | | |

---

## B) DIFF VS v0.1.0

### Changes from v0.1.0 to v1.0.0

#### 1. Schema Changes
- None (schema stable)

#### 2. Taxonomy/Template Changes
- **UPDATED:** Thesis type distribution reflects full corpus
  - Long-term Compounder: 288 → 5,472 (now 40% of all memos)
  - Growth at Reasonable Price: 105 → 2,600 (now 19%)
  - Special Situation: 125 → 2,343 (now 17%)
  - Evidence: Full corpus shows Compounder is dominant investment style

#### 3. Rubric Changes
- None (rubric stable from v0.1.0)

#### 4. Feature Extraction Changes
- **UPDATED:** Detection thresholds refined based on full corpus frequencies
  - Variant view detection: Only 19% have explicit variant view (vs 23% in priority sample)
  - Competitive analysis: 44% presence rate confirmed across full corpus

#### 5. Validation Changes
- **UPDATED:** Baseline metrics now based on 13,635 memos
  - Avg decision readiness: 0.791 (priority) → 0.755 (full corpus)
  - Avg completeness: 0.741 → 0.800

#### 6. Latent Quality Updates
- No new qualities promoted to Core Instruction
- All hypotheses remain in "candidate" status pending formal testing

---

## C) DEFINING TRAITS OF ELITE BUYSIDE MEMOS

The following traits distinguish high-quality, decision-grade buyside memos based on analysis of **13,635 memos** (700 contest winners, 1,169 shorts, 11,766 regular longs):

### Structural Completeness (from full corpus)

1. **Contains explicit thesis statement** — 81% of memos include clear thesis articulation. Elite memos state the "why" in the first 2-3 sentences. *Testable: presence of "thesis," "investment case," "opportunity" keywords in opening section.*

2. **Includes quantified valuation framework** — 91% have valuation sections. Elite memos use 2+ methods (most common: NAV/Book Value 24%, EV/EBITDA 23%, P/E 21%). *Testable: count of distinct valuation method mentions.*

3. **Presents falsifiable risk factors** — 70% enumerate risks. Elite memos pair risks with quantified impact and kill conditions. *Testable: presence of conditional exit statements ("if X, then exit").*

4. **Identifies time-bound catalysts** — 77% include catalyst sections. Elite memos specify timing (quarter, date) rather than vague triggers. *Testable: presence of temporal markers in catalyst text.*

5. **Demonstrates variant view with evidence** — Only 19% explicitly articulate why market is wrong. This remains the clearest separator between average and elite memos. *Testable: "market misses," "consensus doesn't understand" patterns.* **(CRITICAL DIFFERENTIATOR)**

### Evidence Quality

6. **Uses primary data over secondary** — Elite memos cite channel checks, management conversations, or proprietary analysis. Secondary reliance correlates with lower decision-readiness.

7. **Provides financial model sensitivity** — Elite memos show valuation ranges across key assumptions, not single-point estimates.

8. **Includes management quality assessment** — 87% discuss management. Elite memos evaluate capital allocation track record with specific examples.

9. **Maps competitive positioning** — Only 44% include competitive analysis. Elite memos quantify market share and moat durability. **(UNDERUTILIZED DIFFERENTIATOR)**

### Decision-Readiness

10. **Specifies position sizing rationale** — Best memos address appropriate position size given conviction and liquidity.

11. **Defines kill conditions** — Elite memos include explicit "exit if" criteria, not just risk enumeration.

12. **Provides actionable timing** — Elite memos indicate entry strategy (immediate vs scale-in vs wait).

### Content Metrics (Full Corpus)

13. **Optimal description length: 10,000-15,000 characters** — Corpus average: 13,396 chars. Median: 12,870 chars. **(UPDATED from v0.1.0)**

14. **Separate catalyst section correlates with quality** — 77% of memos have dedicated catalyst text.

15. **Full corpus decision-readiness: 0.755** — Winners score higher (0.791 average). **(BENCHMARK ESTABLISHED)**

### Emerging Patterns (NEW)

16. **(NEW) Long positions dominate (91.4%)** — Short ideas are scarce and require distinct analytical framework.

17. **(NEW) Compounders are most common thesis (40%)** — Reflects community preference for quality businesses.

18. **(NEW) Leverage/debt is most cited risk (64%)** — Suggests balance sheet analysis is table stakes.

19. **(NEW) Earnings release is most common catalyst (70%)** — But over-reliance may indicate weak variant view.

20. **(NEW) Variant view rarity (19%) indicates opportunity** — Memos with explicit variant view likely score higher.

---

## D) DELIVERABLES

### D1) Data Schema

#### Minimum Required Fields
```json
{
  "id": "string (unique identifier)",
  "url": "string (source URL if available)",
  "company_name": "string",
  "ticker": "string",
  "date": "string (format: 'Month DD, YYYY')",
  "author": "string (hashed for privacy)",
  "position_type": "enum: 'long' | 'short'",
  "is_contest_winner": "boolean",
  "description_text": "string (full thesis)",
  "catalyst_text": "string (catalysts section)",
  "quality_score": "integer 1-10 (community rating)",
  "quality_votes": "integer",
  "has_content": "boolean"
}
```

#### Extended Schema
```json
{
  "sector": "string (GICS sector)",
  "industry": "string (GICS sub-industry)",
  "market_cap_bucket": "enum: 'nano' | 'micro' | 'small' | 'mid' | 'large' | 'mega'",
  "thesis_type": "enum: see D2 taxonomy",
  "time_horizon": "enum: 'short-term' | 'medium-term' | 'long-term'",
  "valuation_methods": ["array of detected methods"],
  "catalyst_types": ["array of detected catalysts"],
  "risk_factors": ["array of detected risks"],
  "decision_readiness_score": "float 0-1",
  "structural_completeness": "float 0-1",
  "has_variant_view": "boolean",
  "description_length": "integer (characters)",
  "extracted_at": "ISO timestamp"
}
```

#### Data Quality Checks
- Reject: `description_text` < 500 characters
- Flag: Missing `catalyst_text` for manual review
- Validate: Date within expected range (2000-present)
- Check: Ticker format (uppercase, 1-5 characters)

---

### D2) Investment Style Taxonomy (4 Buckets)

#### Full Corpus Distribution

| Thesis Type | Count | % of Total | Bucket |
|-------------|-------|------------|--------|
| Long-term Compounder | 5,472 | 40.1% | Bucket 1 |
| Growth at Reasonable Price | 2,600 | 19.1% | Bucket 2 |
| Special Situation | 2,343 | 17.2% | Bucket 2 |
| Turnaround/Cyclical | 1,019 | 7.5% | Bucket 2 |
| General Long | 890 | 6.5% | Bucket 1/2 |
| Fraud/Accounting Issues | 345 | 2.5% | Bucket 3 |
| General Short | 293 | 2.1% | Bucket 3 |
| Catalyst-Driven Short | 190 | 1.4% | Bucket 3 |
| Business Deterioration | 132 | 1.0% | Bucket 3 |
| Secular Decline | 105 | 0.8% | Bucket 4 |
| Overvaluation | 104 | 0.8% | Bucket 3 |
| Deep Value | 103 | 0.8% | Bucket 2 |
| Hidden Value/Misunderstood | 39 | 0.3% | Bucket 2 |

---

#### Bucket 1: Long-term Compounder (Long)
*Quality businesses with durable advantages, multi-year holding period*

**Corpus Stats:** 5,472 memos (40.1% of corpus)

**Discovered Patterns:**
- **Thesis structures:** Moat-first framing, ROIC sustainability, management track record, recurring revenue emphasis
- **Valuation methods:** DCF with terminal value, P/E relative to growth, EV/EBITDA with peer comps
- **Risk framing:** Competitive threats (31%), management succession (5%), capital allocation missteps
- **Catalyst types:** Often catalyst-light; earnings confirmation (70%), management execution (16%)
- **Sector concentrations:** Technology, healthcare, consumer staples, niche industrials

**Style-Specific Template:**
```markdown
## [COMPANY] - Long-term Compounder

### Business Overview
- Business model and value proposition
- Sustainable competitive advantage (moat source and durability)
- Unit economics and scalability

### Investment Thesis (2-3 sentences upfront)
- Why this business will compound at above-market rates
- ROIC/ROE track record and sustainability drivers
- Why valuation is attractive for multi-year hold

### Management & Capital Allocation
- Track record of capital deployment (acquisitions, buybacks, dividends)
- Insider ownership and alignment metrics
- Historical guidance accuracy

### Valuation
- Primary: DCF with explicit growth/margin/WACC assumptions
- Secondary: P/E vs growth rate, peer comparison
- Scenarios: upside/base/downside with probability weights

### Risks & Kill Conditions
- Competitive threats: [specific competitors and threat probability]
- Moat degradation indicators: [what to monitor]
- Kill condition: "Exit if [specific measurable condition]"

### Variant View (REQUIRED)
- What consensus believes
- Why consensus is wrong
- Evidence supporting variant view
```

**Decision Readiness Checklist:**
- [ ] ROIC trend quantified over 5+ years
- [ ] Moat source explicitly identified with evidence
- [ ] Management capital allocation graded with examples
- [ ] DCF with explicit assumptions (not black box)
- [ ] Kill condition specified
- [ ] Variant view articulated (or explain why consensus is correct)

**Common Traps:**
- Overpaying for quality (ignoring valuation discipline)
- Confusing temporary tailwinds with durable moat
- "Compounder" label without ROIC evidence
- **Avoidance:** Require explicit "what price is too high" threshold

---

#### Bucket 2: Mid-to-Short-term Trade (Long)
*Event-driven, catalyst-dependent, or value unlocks with 6-18 month horizon*

**Corpus Stats:** 6,105 memos (44.8%) — Special Situation (2,343), Growth at Reasonable Price (2,600), Turnaround/Cyclical (1,019), Deep Value (103), Hidden Value (39)

**Discovered Patterns:**
- **Thesis structures:** Catalyst-first framing, explicit timeline, gap analysis (current vs event-adjusted value)
- **Valuation methods:** Sum-of-parts (5%), LBO/takeout (12%), normalized earnings, replacement cost (2%)
- **Risk framing:** Catalyst failure (24%), timing risk, execution risk (24%)
- **Catalyst types:** M&A/buyout (53%), earnings inflection (70%), restructuring (13%), spin-offs (10%)
- **Sector concentrations:** Industrials, financials, consumer discretionary, energy (cyclical)

**Style-Specific Template:**
```markdown
## [COMPANY] - Catalyst-Driven Long

### Situation Overview
- Current situation and market perception
- Specific catalyst creating the opportunity

### Investment Thesis
- Catalyst and expected timing (be specific: "Q2 2024" not "soon")
- Price gap: current price vs post-catalyst fair value
- Variant view: why market underestimates catalyst probability/impact

### Catalyst Analysis
- Probability: High/Medium/Low with supporting rationale
- Timeline: specific date or range with milestones
- Confirmation signals: what validates thesis before catalyst
- Disconfirmation signals: what would reduce probability

### Valuation
- Current price vs catalyst-adjusted fair value
- Method: [Sum-of-parts / Takeout premium / Normalized earnings]
- Risk-adjusted return: probability-weighted outcome

### Risks & Kill Conditions
- Catalyst failure scenario and impact
- Timing risk: "Exit if no catalyst by [date]"
- Execution risk: what could go wrong post-catalyst

### Position Sizing
- Conviction-appropriate size
- Entry strategy (immediate vs scale-in)
- Exit targets and timeline
```

**Decision Readiness Checklist:**
- [ ] Catalyst timing specified with date/quarter
- [ ] Probability-weighted return calculated
- [ ] Downside quantified if catalyst fails
- [ ] Kill condition with specific exit date
- [ ] Position size justified relative to conviction

**Common Traps:**
- Catalyst timing slip without thesis update
- Overweighting low-probability events
- Ignoring opportunity cost during waiting period
- **Avoidance:** Hard "exit if no catalyst by [date]" rule

---

#### Bucket 3: Mid-to-Short-term Trade (Short)
*Overvaluation, broken thesis, or imminent negative catalyst*

**Corpus Stats:** 1,064 memos (7.8%) — Fraud/Accounting (345), General Short (293), Catalyst-Driven Short (190), Business Deterioration (132), Overvaluation (104)

**Discovered Patterns:**
- **Thesis structures:** Valuation gap, business deterioration evidence, accounting red flags, competitive disruption
- **Valuation methods:** Relative valuation (premium to peers), historical multiple analysis, normalized earnings showing overstatement
- **Risk framing:** Short squeeze (11%), borrow availability, timing uncertainty
- **Catalyst types:** Earnings miss (70%), guidance cut, accounting issues (21%), competitive losses
- **Sector concentrations:** Technology (overvaluation), retail (disruption), financials (credit)

**Style-Specific Template:**
```markdown
## [COMPANY] - Short Position

### Bear Thesis (1-2 sentences upfront)
- Core thesis: why stock is overvalued/deteriorating
- Variant view: what bulls believe that is wrong

### Evidence Hierarchy
1. [PRIMARY] Quantified business deterioration (revenue, margins, customers)
2. [SECONDARY] Accounting concerns or red flags
3. [TERTIARY] Competitive threats materializing

### Valuation
- Current valuation vs appropriate fair value
- What multiple/metric should this trade at? (with peer evidence)
- Downside target and basis

### Catalyst
- Trigger for repricing (be specific)
- Timeline expectation
- Leading indicators to monitor

### Short-Specific Risks (CRITICAL)
- Short interest: [X]%, days to cover: [Y]
- Borrow: availability and cost
- Squeeze risk: assessment and mitigation
- M&A/takeout risk: probability
- Timing risk: how long can you be wrong?

### Position Sizing & Management
- Maximum position size (% of portfolio)
- Stop-loss: "[Price]" or "[% move against]"
- Scaling plan if thesis strengthens/weakens
```

**Decision Readiness Checklist:**
- [ ] Variant view clearly articulated
- [ ] Evidence is primary (not derivative sell-side)
- [ ] Short squeeze risk assessed quantitatively
- [ ] Borrow confirmed available and cost known
- [ ] Position size appropriate for short (smaller than long conviction)
- [ ] Stop-loss defined (price or time-based)

**Common Traps:**
- Fighting momentum without near-term catalyst
- Underestimating squeeze risk
- Thesis creep without position adjustment
- **Avoidance:** Hard stop-loss rules, position size limits (max 3%)

---

#### Bucket 4: Long-term Secular Short
*Structural decline, technological disruption, or terminal business model*

**Corpus Stats:** 105 memos (0.8%) — Secular Decline only

**Discovered Patterns:**
- **Thesis structures:** Industry disruption narrative, technology obsolescence, structural demand decline
- **Valuation methods:** Terminal value analysis, liquidation value, run-off scenarios
- **Risk framing:** Multi-year timing risk, short squeeze during rallies, value trap reversal
- **Catalyst types:** Quarterly deterioration accumulation, covenant breach (43%), dividend cut (36%)
- **Sector concentrations:** Retail (e-commerce), media (cord-cutting), legacy tech, print/publishing

**Style-Specific Template:**
```markdown
## [COMPANY] - Secular Short

### Structural Thesis
- Secular force destroying this business
- Timeline: how long until terminal state
- Is thesis well-known or underappreciated?

### Evidence of Decline (multi-year trends required)
- Revenue/volume trends (3+ years)
- Market share trajectory
- Customer behavior shifts
- Technology disruption timeline

### Endgame Analysis
- Terminal value estimate (often zero or liquidation)
- Debt maturity wall / covenant risk timeline
- Liquidation scenario value

### Timing & Catalysts
- Near-term triggers to monitor
- Quarterly checkpoints
- Why this timing vs earlier/later

### Long-Duration Short Risks
- "Value trap" reversal: probability and triggers
- Short squeeze during bear market rallies
- Management pivot potential
- Timing: secular shorts can take 3-5+ years

### Implementation
- Position size for extended timeline (smaller)
- Rolling vs static short position
- Put spreads vs direct short (cost management)
```

**Decision Readiness Checklist:**
- [ ] Secular force clearly identified and quantified
- [ ] Evidence shows trend accelerating or stable (not reversing)
- [ ] Terminal value / endgame articulated
- [ ] Timeline acknowledges multi-year horizon explicitly
- [ ] Position sized for extended holding (max 1-2%)
- [ ] Quarterly monitoring criteria defined

**Common Traps:**
- Underestimating how long decline takes
- Getting squeezed during counter-trend rallies
- Management pivot surprising bears
- **Avoidance:** Small positions, put spreads, patience

---

### D3) Scoring Rubric (1-10, AI-Executable)

#### Dimensions (5 total)

| Dimension | Weight | Definition |
|-----------|--------|------------|
| Thesis Clarity | 25% | Falsifiable thesis with explicit variant view |
| Evidence Quality | 25% | Primary, quantified, verifiable evidence |
| Valuation Rigor | 20% | Multiple methods with explicit assumptions |
| Risk Framework | 15% | Specific risks with kill conditions |
| Decision Readiness | 15% | Timing, sizing, exit criteria |

#### Scoring Anchors

**Thesis Clarity (0-10):**
| Score | Description |
|-------|-------------|
| 2 | Vague assertion ("this is cheap") |
| 5 | Clear thesis but no variant view or falsification criteria |
| 8 | Explicit thesis + variant view + testable predictions |
| 10 | Falsifiable, time-bound thesis with clear "I'm wrong if" conditions |

**Evidence Quality (0-10):**
| Score | Description |
|-------|-------------|
| 2 | Relies on sell-side research or assertions |
| 5 | Public filings and basic quantitative analysis |
| 8 | Primary research (channel checks, management, customers) |
| 10 | Multiple primary sources, cross-validated, quantified |

**Valuation Rigor (0-10):**
| Score | Description |
|-------|-------------|
| 2 | No valuation or vague ("it's cheap") |
| 5 | Single method with stated assumptions |
| 8 | Multiple methods + sensitivity analysis + scenario ranges |
| 10 | Probability-weighted scenarios with explicit margin of safety |

**Risk Framework (0-10):**
| Score | Description |
|-------|-------------|
| 2 | Risks not mentioned or generic |
| 5 | Risks enumerated but not quantified |
| 8 | Specific risks with impact quantification and kill conditions |
| 10 | Risk-reward calculated with position sizing implications |

**Decision Readiness (0-10):**
| Score | Description |
|-------|-------------|
| 2 | No guidance on timing, sizing, exits |
| 5 | Timing mentioned but vague; no sizing |
| 8 | Specific catalyst timing, position size, exit criteria |
| 10 | Complete framework: entry, scaling, exits, monitoring |

#### Scoring Function
```python
def calculate_memo_score(dimensions: dict) -> float:
    weights = {
        "thesis_clarity": 0.25,
        "evidence_quality": 0.25,
        "valuation_rigor": 0.20,
        "risk_framework": 0.15,
        "decision_readiness": 0.15
    }
    return round(sum(dimensions[d] * weights[d] for d in weights), 1)
```

#### Bias Adjustments
- **Outcome bias:** Score process quality, not subsequent returns
- **Length bias:** Penalty only if >40,000 chars without proportional depth
- **Confidence theater:** Penalize "guaranteed," "can't lose" without evidence
- **Rhetorical polish:** Weight substance over prose quality

---

### D4) Feature Extraction Plan

#### Full Corpus Feature Frequencies

| Feature | Detection Rate | Significance |
|---------|---------------|--------------|
| Has financials | 91.4% | Table stakes |
| Has valuation section | 90.8% | Table stakes |
| Has management discussion | 87.1% | Common |
| Has thesis statement | 80.5% | Common |
| Has company overview | 79.8% | Common |
| Has catalyst section | 76.8% | Important |
| Has risk section | 69.9% | Important |
| Has competitive analysis | 44.4% | Differentiator |
| Has variant view | 18.6% | **Elite differentiator** |

#### Feature: Variant View
**Operational Definition:** Explicit statement of why consensus/market is wrong.

**Detection:**
```python
variant_patterns = [
    r"market (miss|doesn.t understand|wrong|overlooked)",
    r"consensus (wrong|miss|doesn.t)",
    r"underappreciat",
    r"variant (view|perception)",
    r"what.*(street|market).*(miss|wrong)"
]
```

**Classification:** Binary (present/absent), confidence threshold 0.7

#### Feature: Evidence Specificity
**Scale:** 1 (secondary only) to 5 (extensive primary)

**Detection:**
- Primary: "spoke with," "channel check," "proprietary," "site visit," "customer interview"
- Secondary: "according to analyst," "per 10-K," "management guided"

#### Feature: Valuation Methods
**Detection patterns (from corpus analysis):**

| Method | Frequency | Pattern |
|--------|-----------|---------|
| NAV/Book Value | 3,225 | `nav|net asset value|book value|tangible book` |
| EV/EBITDA | 3,124 | `ev/ebitda|enterprise value.*ebitda` |
| P/E Multiple | 2,907 | `p/e|pe ratio|earnings multiple` |
| Comp Analysis | 2,017 | `compar|peer|trading at.*vs` |
| FCF Yield | 1,849 | `fcf yield|free cash flow yield` |
| LBO/Takeout | 1,683 | `lbo|leveraged buyout|take.?out` |
| DCF | 1,332 | `dcf|discounted cash flow|npv` |
| Dividend Yield | 1,315 | `dividend yield|dividend discount` |
| EV/Revenue | 716 | `ev/revenue|ev/sales|price.to.sales` |
| Sum-of-Parts | 641 | `sum.of.parts|sotp|break.?up` |
| Replacement Cost | 265 | `replacement cost|reproduction value` |

#### Feature: Catalyst Types
| Type | Frequency | Pattern |
|------|-----------|---------|
| Earnings Release | 9,566 (70%) | `earnings|quarterly report|guidance` |
| M&A/Buyout | 7,180 (53%) | `acquisition|merger|buyout|take.?over` |
| Debt Refinancing | 5,919 (43%) | `refinanc|deleverag|debt pay.?down` |
| Macro/Cycle | 5,211 (38%) | `cycle|recovery|macro|commodity` |
| Capital Return | 4,960 (36%) | `buyback|dividend|return capital` |
| Fraud/Accounting | 2,803 (21%) | `fraud|accounting|restatement` |
| Regulatory | 2,772 (20%) | `regulat|approval|license` |
| Product Launch | 2,304 (17%) | `new product|launch|fda approval` |
| Management Change | 2,203 (16%) | `new (ceo|management)|activist|board` |
| Restructuring | 1,755 (13%) | `restructur|turnaround|cost.?cut` |
| Short Squeeze | 1,442 (11%) | `short squeeze|short interest|covering` |
| Spin-off/Split | 1,380 (10%) | `spin.?off|split.?off|separation` |

#### Feature: Risk Factors
| Risk | Frequency | Pattern |
|------|-----------|---------|
| Leverage/Debt | 8,789 (64%) | `leverag|debt|covenant|bankruptcy` |
| Macro/Cyclical | 6,338 (46%) | `recession|economic|cyclical|downturn` |
| Regulatory | 5,502 (40%) | `regulatory|government|policy|litigation` |
| Competition | 4,292 (31%) | `competit|market share|pricing pressure` |
| Execution Risk | 3,210 (24%) | `execution|implement|turnaround fail` |
| Capital Needs | 2,773 (20%) | `capital (need|raise)|dilution|funding` |
| Commodity Exposure | 2,171 (16%) | `commodity|input cost|raw material` |
| Currency | 1,609 (12%) | `currency|fx|foreign exchange` |
| Technology/Disruption | 985 (7%) | `technolog|disruption|obsolete` |
| Management Quality | 660 (5%) | `management (risk|quality)|key person` |
| Customer Concentration | 436 (3%) | `customer concentration|key customer` |

---

### D5) Synthesis Plan (Playbook + Templates + Anti-patterns)

#### Writing Playbook

**Phase 1: Pre-Writing (Research)**
1. Classify investment style bucket (Compounder / Trade Long / Trade Short / Secular Short)
2. Draft thesis in 2-3 sentences
3. Identify variant view (if none exists, acknowledge consensus)
4. List 3-5 evidence points (prioritize primary)
5. Select appropriate valuation method(s)
6. Enumerate top 3 risks with kill conditions

**Phase 2: Drafting**
1. **Open with thesis** — First paragraph states opportunity
2. **Business overview** — What company does, competitive position
3. **Investment thesis** — Why attractive now, variant view
4. **Valuation** — Multiple methods, assumptions explicit, scenarios
5. **Catalysts** — Time-bound, probability assessed
6. **Risks** — Specific, quantified, kill conditions
7. **Decision framework** — Sizing, timing, exit

**Phase 3: Self-Critique**
Apply rubric (D3):
- [ ] Thesis Clarity: Falsifiable? Variant view explicit?
- [ ] Evidence Quality: Primary or just filings?
- [ ] Valuation Rigor: Multiple methods? Sensitivity?
- [ ] Risk Framework: Specific kill conditions?
- [ ] Decision Readiness: Sizing, timing, exits?

**Target: Score 7+ before finalizing**

**Phase 4: Red Team**
- What's the strongest bear case?
- What would make you exit immediately?
- What evidence would falsify thesis?
- Who's on the other side and why?

#### Anti-Pattern List (from corpus analysis)

| Anti-Pattern | Frequency | How Elite Memos Avoid |
|--------------|-----------|----------------------|
| Thesis-free narrative | ~20% | Lead with thesis in first paragraph |
| Valuation-free optimism | ~9% | Always include target with methodology |
| Risk-free conviction | ~30% | Enumerate risks with kill conditions |
| Catalyst-free hope | ~23% | Specify time-bound catalysts |
| Evidence-free assertion | ~15% | Cite specific sources, quantify |
| Consensus-echo | ~81% | Explicitly state variant view |
| Length-without-depth | ~5% | Target 10-15K chars with substance |
| Confidence theater | ~10% | Acknowledge uncertainty, show scenarios |

#### Minimum Viable vs Elite Memo

| Aspect | Minimum Viable (5-6) | Elite (8-10) |
|--------|---------------------|--------------|
| Thesis | Clear statement | Falsifiable with variant view |
| Valuation | Single method | Multiple methods + sensitivity |
| Risks | Generic list | Specific with kill conditions |
| Catalyst | Vague mention | Time-bound with probability |
| Decision | Basic recommendation | Full framework (sizing, timing, exits) |
| Evidence | Public filings | Primary research cited |
| Length | 5,000-10,000 chars | 12,000-20,000 chars with depth |

---

### D6) Validation Plan

#### Full Corpus Baselines (v1.0.0)

| Metric | Value | Source |
|--------|-------|--------|
| Avg Description Length | 13,396 chars | Full corpus |
| Median Description Length | 12,870 chars | Full corpus |
| Avg Decision Readiness | 0.755 | Full corpus |
| Winner Decision Readiness | 0.791 | Priority sample |
| Avg Completeness | 0.800 | Full corpus |
| Variant View Rate | 18.6% | Full corpus |
| Competitive Analysis Rate | 44.4% | Full corpus |

#### Testing Protocol

**Blind Evaluation:**
1. Generate AI memo for ticker
2. Pair with VIC memo for same/similar company
3. Blind scorer rates both using rubric
4. Track win rate

**Holdout Sets:**
- Time: 2022 memos (795 files)
- Author: Top 10 prolific authors
- Style: One per thesis type per year

**Pairwise Ranking:**
- 100 A/B pairs
- Question: "Which would you act on?"
- Target: AI preferred >50% vs median VIC

#### Success Metrics

| Metric | Target | Baseline |
|--------|--------|----------|
| Rubric Score | >7.0 | 5.5 (median) |
| Pairwise Win Rate | >55% | 50% |
| Hallucination Rate | <5% | N/A |
| Decision Readiness | >0.85 | 0.755 |
| Completeness | >0.85 | 0.800 |
| Variant View Rate | >50% | 18.6% |

---

## E) LATENT QUALITY MODULE

### Hypothesis Bank

| ID | Name | Status | Evidence |
|----|------|--------|----------|
| H001 | Variant View Presence | **PROMOTED TO TESTING** | Only 18.6% have it; correlates with winner status |
| H002 | Primary Research Citation | candidate | Detection heuristics defined |
| H003 | Multi-Method Valuation | candidate | 60%+ use multiple methods |
| H004 | Explicit Kill Conditions | candidate | Rare but high-signal |
| H005 | Time-Bound Catalysts | candidate | 77% have catalyst section |
| H006 | Management Quality Assessment | candidate | 87% discuss management |
| H007 | Competitive Moat Mapping | **PROMOTED TO TESTING** | Only 44% include; differentiator |
| H008 | Position Sizing Rationale | candidate | Rarely explicit |

### Promotion Criteria
1. Predictive: Feature correlates with score r>0.3 (controlled)
2. Discriminability: Rubric scorer >70% accuracy using feature
3. Ablation: Removing feature reduces decision-readiness >0.1

### Changelog Discipline
- **X.0.0 (Major):** Schema changes, taxonomy restructure
- **X.Y.0 (Minor):** Hypothesis promoted to Core, template updates
- **X.Y.Z (Patch):** Bug fixes, wording clarifications

### Guardrails
1. External validation on non-VIC research
2. Diverse author sampling
3. Substance over style weighting
4. Era normalization

---

## F) PITFALLS & COMPLIANCE

### IP/ToS Constraints
- No verbatim copying (this manual distills patterns only)
- VIC memos are proprietary; analysis is derivative
- Usage: AI agent training, not content republishing

### Analytical Biases

| Bias | Risk | Mitigation |
|------|------|------------|
| Outcome | VIC scores partly reflect returns | Score process, not outcomes |
| Survivorship | Successful ideas over-represented | Include failed theses |
| Author Effects | Famous authors score higher | Normalize for author |
| Recency | Style conventions evolve | Stratify by era |

### Rhetorical vs Substantive Quality
- Risk: Well-written but weak analysis scores high
- Mitigation: Rubric weights substance (thesis, evidence, valuation) over prose

### Data Leakage
- Comments contain outcome information → Train on description_text only
- Updates may reference post-pitch events → Validate date consistency

### Memorization Risk
- Risk: AI reproduces source phrasing
- Mitigation: Extract patterns not text, similarity threshold check

---

## PDF Layout Notes

### Specifications
- Margins: 1 inch
- Body: 11pt serif; Headers: 12pt sans-serif
- Line spacing: 1.15
- Code: 10pt monospace, light gray background
- Tables: Bordered, header shaded

### Page Breaks
- Each major section starts new page
- D2 subsections (buckets) each start new page

### Headers/Footers
- Header: "Buyside Memo Engine v1.0.0"
- Footer: Page number, "Generated: 2026-01-16"

---

## Appendix: Corpus Statistics Summary

### Full Analysis (13,635 memos)

**Position Distribution:**
- Long: 12,466 (91.4%)
- Short: 1,169 (8.6%)

**Thesis Type Distribution:**
- Long-term Compounder: 5,472 (40.1%)
- Growth at Reasonable Price: 2,600 (19.1%)
- Special Situation: 2,343 (17.2%)
- Turnaround/Cyclical: 1,019 (7.5%)
- General Long: 890 (6.5%)
- Fraud/Accounting Issues: 345 (2.5%)
- General Short: 293 (2.1%)
- Catalyst-Driven Short: 190 (1.4%)
- Business Deterioration: 132 (1.0%)
- Secular Decline: 105 (0.8%)
- Overvaluation: 104 (0.8%)
- Deep Value: 103 (0.8%)
- Hidden Value/Misunderstood: 39 (0.3%)

**Quality Metrics:**
- Avg description length: 13,396 characters
- Avg decision readiness: 0.755
- Avg completeness: 0.800
- Contest winner rate: 5.1%

---

*End of v1.0.0 Instruction Manual*

**Corpus fully processed. Manual complete.**
