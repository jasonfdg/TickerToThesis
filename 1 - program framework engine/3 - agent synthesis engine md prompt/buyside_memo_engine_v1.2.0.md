# Buyside Memo Engine - Instruction Manual

**Version:** v1.2.0
**Generated:** 2026-01-19T12:00:00
**Run ID:** input-spec-dual-source

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

## A.2) INPUT SPECIFICATION (NEW v1.2.0)

### Required Input
| Input | Required | Description |
|-------|----------|-------------|
| **Ticker** | YES | Stock ticker symbol (e.g., AAPL, MSFT) |

### Optional Inputs (Priority Order)
| Input | Priority | Description |
|-------|----------|-------------|
| **Prompt** | 1 (highest) | Specific research question or directive |
| **Research Director Feedback** | 2 | Prior iteration feedback from research director |
| **Analyst Reports** | 3 | Third-party analyst research (sell-side, buy-side) |
| **Source File** | 4 (lowest) | Pre-gathered web research: `[TICKER]_webSource.json` |

### Priority Rules
1. Higher-priority inputs override lower when conflicts arise
2. All provided inputs must be considered, regardless of priority
3. Absence of optional inputs does not degrade analysis quality
4. Ticker is the anchor—all analysis must relate to the specified company

### Source File Format
When provided, the source file is a single JSON file named `[TICKER]_webSource.json` containing pre-gathered web research for the ticker.

---

## B) DIFF VS v1.1.0

### Changes from v1.1.0 to v1.2.0

#### 1. Input Specification (NEW)
- **NEW:** Section A.2 defines required and optional inputs
- **NEW:** Priority hierarchy: Prompt > Research Director Feedback > Analyst Reports > Source File
- **NEW:** Source file format specification (`[TICKER]_webSource.json`)

#### 2. Source Documentation (NEW)
- **NEW:** Phase 6 requires source citation table at end of each memo iteration
- **NEW:** All sources must include: name, link, type, and 1-sentence summary
- **NEW:** Source types defined: Fact, Opinion, Primary, Source File

#### 3. Dual-Source Protocol (NEW)
- **NEW:** Section G defines mandatory cross-referencing when source file is provided
- **NEW:** Cannot cite source file without web verification
- **NEW:** Cannot make web search without first checking source file
- **NEW:** ANCHOR → EXTEND → RECONCILE workflow for each major claim

---

## C) DEFINING TRAITS OF ELITE BUYSIDE MEMOS

The following traits distinguish high-quality, decision-grade buyside memos based on analysis of **13,635 memos** (700 contest winners, 1,169 shorts, 11,766 regular longs):

### Structural Completeness (from full corpus)

1. **Contains explicit thesis statement** — 81% of memos include clear thesis articulation. Elite memos state the "why" in the first 2-3 sentences. *Testable: presence of "thesis," "investment case," "opportunity" keywords in opening section.*

2. **Includes quantified valuation framework** — 91% have valuation sections. Elite memos use 2+ methods (most common: NAV/Book Value 24%, EV/EBITDA 23%, P/E 21%). *Testable: count of distinct valuation method mentions.*

3. **Presents falsifiable risk factors** — 70% enumerate risks. Elite memos pair risks with quantified impact and kill conditions. *Testable: presence of conditional exit statements ("if X, then exit").*

4. **Identifies milestone-bound catalysts** — 77% include catalyst sections. Elite memos specify observable milestones with verification sources rather than arbitrary calendar dates. *Testable: presence of specific metrics/thresholds (e.g., "TVL >$500M") rather than dates alone ("by Q4 2026").* **(UPDATED v1.1.0)**

5. **Demonstrates variant view with evidence** — Only 19% explicitly articulate why market is wrong. This remains the clearest separator between average and elite memos. *Testable: "market misses," "consensus doesn't understand" patterns.* **(CRITICAL DIFFERENTIATOR)**

### Evidence Quality

6. **Uses primary data over secondary** — Elite memos cite channel checks, management conversations, or proprietary analysis. Secondary reliance correlates with lower decision-readiness.

6a. **Classifies and traces evidence sources** — Elite memos distinguish between: **(NEW v1.1.0)**

   **The Core Question:** "Is this where the information ORIGINATED, or where it was AGGREGATED/INTERPRETED?"

   | Source Type | Definition | Examples |
   |-------------|------------|----------|
   | **Facts** | Verifiable, auditable data from official records | SEC filings (10-K, 10-Q, proxy), earnings releases, on-chain data, court documents, patent filings |
   | **Opinions** | Interpretations, analysis, or predictions by observers | Sell-side research, news analysis, earnings call color commentary, price targets |
   | **Primary Sources** | Direct voice or behavior from participants in the story | See framework below |

   **Primary Source Categories (The Differentiator):**
   1. **Direct Voice** — Unfiltered statements from principals: CEO interviews, podcast appearances, conference presentations, direct quotes (not paraphrased), Twitter/X posts from executives
   2. **Stakeholder Signals** — Sentiment from those with direct experience: employee reviews (Glassdoor, Blind), customer reviews (App Store, Trustpilot, G2), supplier/partner statements
   3. **Behavioral Data** — Actions reveal intent better than words: GitHub commits/activity, job postings (what they're hiring for), patent filings, insider transactions, facility expansions
   4. **Community Discourse** — Discussion among actual participants: Reddit (employees, customers, industry), specialized forums, Discord servers, industry Slack channels

   **Search Strategy:** When searching, don't just accept the first news article. Ask: "Who is the original source? Can I find their direct statement?" Trace backward until you reach the origin.

   *Testable: explicit citation of source type and origin tracing.*

7. **Provides financial model sensitivity** — Elite memos show valuation ranges across key assumptions, not single-point estimates.

8. **Includes management quality assessment** — 87% discuss management. Elite memos evaluate capital allocation track record with specific examples.

9. **Maps competitive positioning** — Only 44% include competitive analysis. Elite memos quantify market share and moat durability. **(UNDERUTILIZED DIFFERENTIATOR)**

### Decision-Readiness

10. **Specifies position sizing rationale** — Best memos address appropriate position size given conviction and liquidity.

11. **Defines kill conditions** — Elite memos include explicit "exit if" criteria, not just risk enumeration.

12. **Provides actionable timing** — Elite memos indicate entry strategy (immediate vs scale-in vs wait).

### Content Metrics (Full Corpus)

13. **Optimal description length: 10,000-15,000 characters** — Corpus average: 13,396 chars. Median: 12,870 chars.

14. **Separate catalyst section correlates with quality** — 77% of memos have dedicated catalyst text.

15. **Full corpus decision-readiness: 0.755** — Winners score higher (0.791 average). **(BENCHMARK ESTABLISHED)**

### Emerging Patterns

16. **Long positions dominate (91.4%)** — Short ideas are scarce and require distinct analytical framework.

17. **Compounders are most common thesis (40%)** — Reflects community preference for quality businesses.

18. **Leverage/debt is most cited risk (64%)** — Suggests balance sheet analysis is table stakes.

19. **Earnings release is most common catalyst (70%)** — But over-reliance may indicate weak variant view.

20. **Variant view rarity (19%) indicates opportunity** — Memos with explicit variant view likely score higher.

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
- Entry price derivation: What price would I pay? (derive from valuation, not anchor to current)
- Scenarios: upside/base/downside with evidence-grounded probabilities

### Risks & Kill Conditions
- Competitive threats: [specific competitors and threat probability]
- Moat degradation indicators: [what to monitor]
- Kill condition: "Exit if [metric] [threshold] by [milestone], verified via [source]"
- Use milestone-based triggers, not arbitrary calendar dates

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
- [ ] Entry price derived from valuation (not anchored to current price)
- [ ] Kill condition specified with milestone and verification source
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
- Probability: High/Medium/Low with supporting rationale grounded in evidence
- Timeline: specific milestones with verification sources
- Confirmation signals: what validates thesis before catalyst
- Disconfirmation signals: what would reduce probability

### Valuation
- Current price vs catalyst-adjusted fair value
- Method: [Sum-of-parts / Takeout premium / Normalized earnings]
- Entry price derivation: What price would I pay? (derive from valuation)
- Risk-adjusted return: probability-weighted outcome (ground probabilities in evidence)

### Risks & Kill Conditions
- Catalyst failure scenario and impact
- Kill condition: "Exit if [metric] [threshold] by [milestone], verified via [source]"
- Execution risk: what could go wrong post-catalyst

### Position Sizing
- Conviction-appropriate size
- Entry strategy (immediate vs scale-in)
- Exit targets and timeline
```

**Decision Readiness Checklist:**
- [ ] Catalyst timing specified with milestone (not just date)
- [ ] Probability-weighted return calculated with grounded probabilities
- [ ] Downside quantified if catalyst fails
- [ ] Kill condition with specific milestone and verification source
- [ ] Position size justified relative to conviction

**Common Traps:**
- Catalyst timing slip without thesis update
- Overweighting low-probability events
- Ignoring opportunity cost during waiting period
- **Avoidance:** Hard "exit if [milestone] not achieved" rule

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
- Trigger for repricing (be specific with milestone)
- Timeline expectation with verification source
- Leading indicators to monitor

### Short-Specific Risks (CRITICAL)
- Short interest: [X]%, days to cover: [Y]
- Borrow: availability and cost
- Squeeze risk: assessment and mitigation
- M&A/takeout risk: probability
- Timing risk: how long can you be wrong?

### Kill Conditions
- Exit trigger: "Cover if [metric] [threshold] by [milestone], verified via [source]"
- Stop-loss: "[Price]" or "[% move against]"
- Use milestone-based triggers, not arbitrary calendar dates

### Position Sizing & Management
- Maximum position size (% of portfolio)
- Scaling plan if thesis strengthens/weakens
```

**Decision Readiness Checklist:**
- [ ] Variant view clearly articulated
- [ ] Evidence is primary (not derivative sell-side)
- [ ] Short squeeze risk assessed quantitatively
- [ ] Borrow confirmed available and cost known
- [ ] Position size appropriate for short (smaller than long conviction)
- [ ] Kill condition defined with milestone and verification source

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
- Near-term milestones to monitor (with verification sources)
- Quarterly checkpoints
- Why this timing vs earlier/later

### Long-Duration Short Risks
- "Value trap" reversal: probability and triggers
- Short squeeze during bear market rallies
- Management pivot potential
- Timing: secular shorts can take 3-5+ years

### Kill Conditions
- Exit trigger: "Cover if [metric] [threshold] by [milestone], verified via [source]"
- Use milestone-based triggers with observable verification

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
- [ ] Quarterly monitoring criteria defined with verification sources

**Common Traps:**
- Underestimating how long decline takes
- Getting squeezed during counter-trend rallies
- Management pivot surprising bears
- **Avoidance:** Small positions, put spreads, patience

---

#### Decision Requirements (NEW v1.1.0)

##### When Recommending a Position (Buy/Sell)

**Bucket Classification (REQUIRED):** Every position recommendation must classify into exactly one bucket:
- Bucket 1: Long-term Compounder (Long)
- Bucket 2: Mid-to-Short-term Trade (Long)
- Bucket 3: Mid-to-Short-term Trade (Short)
- Bucket 4: Long-term Secular Short

No hedging between buckets. The classification determines which template requirements apply and how the position should be sized and monitored. If unsure, default to the shorter-duration bucket (2 or 3) until conviction develops.

##### When Passing (Not Recommending Action)

A "pass" is a valid decision, but it must be actionable, not a deferral.

**Required Elements for Pass Memos:**
1. **Action Price** — At what price would you buy/sell? Derive from valuation, not anchored to current price.
2. **Information Trigger** — What news would make you act at current price?
3. **Thesis Preservation** — Document the thesis for future activation
4. **Archive Plan** — When to revisit; what to monitor

**Pass ≠ Watchlist.** A pass with no action price is not a decision.

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
| 6 | Public filings + explicit acknowledgment "No primary sources available" **(UPDATED v1.1.0 - ceiling without primary sources)** |
| 8 | Primary research (channel checks, management, customers, competitor analysis) |
| 10 | Multiple primary sources from different categories, cross-validated, quantified |

**Valuation Rigor (0-10):**
| Score | Description |
|-------|-------------|
| 2 | No valuation or vague ("it's cheap") |
| 5 | Single method with stated assumptions |
| 8 | Multiple methods + sensitivity analysis + scenario ranges with probabilities grounded in evidence + **entry price derived from valuation** **(UPDATED v1.1.0)** |
| 10 | Probability-weighted scenarios with probabilities **explicitly tied to historical precedent, base rates, or verifiable conditions** + entry price justified by fundamentals, not anchored to current price **(UPDATED v1.1.0)** |

**Probability Grounding Requirement (NEW v1.1.0):**
- If using probability weights, must cite evidence (e.g., "30% crypto winter probability based on 3 of last 10 years experiencing >50% drawdowns")
- Ungrounded probabilities (arbitrary percentages) should be replaced with qualitative descriptions
- Acceptable: "Bear case: historically occurs 2-3x per decade"
- Unacceptable: "Bear case: 25% probability" (without basis)

**Risk Framework (0-10):**
| Score | Description |
|-------|-------------|
| 2 | Risks not mentioned or generic |
| 5 | Risks enumerated but not quantified |
| 8 | Specific risks with impact quantification and milestone-based kill conditions |
| 10 | Risk-reward calculated with position sizing implications and verified monitoring sources |

**Decision Readiness (0-10):**
| Score | Description |
|-------|-------------|
| 2 | No guidance on timing, sizing, exits; or "watchlist" without action criteria **(UPDATED v1.1.0)** |
| 5 | Timing mentioned but vague; no sizing; pass without action price |
| 8 | Specific catalyst timing, position size, exit criteria; **pass includes derived action price** **(UPDATED v1.1.0)** |
| 10 | Complete framework: entry, scaling, exits, monitoring; **pass includes action price + information triggers** **(UPDATED v1.1.0)** |

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

#### Feature: Source Classification (NEW v1.1.0)

**The Hierarchy:**
```
Primary Sources (highest value)
    └── Direct Voice: "CEO said in interview..."
    └── Stakeholder Signals: "Glassdoor reviews indicate..."
    └── Behavioral Data: "GitHub activity shows..."
    └── Community Discourse: "Reddit thread from employee..."
Facts (baseline value)
    └── Official Filings: "Per 10-K..."
    └── Verified Data: "On-chain data shows..."
Opinions (lowest value, use cautiously)
    └── Analysis: "Analyst believes..."
    └── Predictions: "Consensus expects..."
```

**Detection Heuristics:**

| Looking For | Search Strategy |
|-------------|-----------------|
| Direct Voice | Search: "[company] CEO interview" "[exec name] podcast" "[company] conference presentation" |
| Stakeholder Signals | Search: "[company] glassdoor" "[product] reviews" "[company] reddit employees" |
| Behavioral Data | Search: "[company] github" "[company] hiring" "[company] patents 2024" |
| Community Discourse | Search: "site:reddit.com [company]" "[company] forum" |

**Competitor Research (Apply Same Framework):**
| Looking For | Search Strategy |
|-------------|-----------------|
| Competitor Facts | Search: "[competitor] 10-K" "[competitor] market share" "[competitor] pricing" |
| Competitor Opinions | Search: "[company] vs [competitor]" "analyst comparison [industry]" |
| Competitor Primary | Search: "[competitor] CEO interview" "[competitor] glassdoor" "switched from [competitor] to [company]" customer comparison threads |

**Origin Tracing Rule:** When a secondary source (news article, research report) cites interesting information, search for the original source. Example: "Per Bloomberg, the CEO said..." → Find the actual Bloomberg interview or transcript.

**Quality Signal:** Memos citing 2+ primary sources from different categories (including competitor sources) score higher on Evidence Quality.

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
4. **Gather evidence with source awareness:** **(UPDATED v1.1.0)**

   **For the Target Company:**
   - **Facts:** Collect from official filings, verified data sources
   - **Opinions:** Note but weight cautiously; these are interpretations, not truth
   - **Primary Sources:** Actively hunt for these—they are the differentiator:
     - Direct Voice: Find actual interviews, presentations, executive statements
     - Stakeholder Signals: Check employee/customer review sites
     - Behavioral Data: Look at GitHub, job postings, patent activity
     - Community Discourse: Search Reddit, forums for participant perspectives

   **For Competitors (equally important):**
   - **Competitor Facts:** Competitor filings, market share data, pricing, product specs
   - **Competitor Opinions:** Analyst comparisons, industry reports positioning competitors
   - **Competitor Primary Sources:** Competitor exec interviews, their employee reviews, customer comparisons ("I switched from X to Y because...")

   - **Origin Tracing:** When you find an interesting claim in a news article, trace it back to the original source
   - **Requirement:** Cite at least 1 primary source OR explicitly note "No primary sources found; analysis based on facts + opinions only" (this caps Evidence Quality score at 6)

5. Select appropriate valuation method(s)
6. Enumerate top 3 risks with kill conditions

**Phase 2: Drafting**
1. **Open with thesis** — First paragraph states opportunity
2. **Business overview** — What company does, competitive position
3. **Investment thesis** — Why attractive now, variant view
4. **Valuation** — Multiple methods, assumptions explicit, scenarios **(UPDATED v1.1.0)**
   - **Entry price derivation (REQUIRED):** Derive target entry from valuation framework FIRST, then compare to current price. Flag if entry is anchored to "X% pullback from current" rather than fundamentally derived.
   - Entry price must answer: "What would I pay for this business?" not "How much discount do I want?"
   - If using scenario probabilities, ground them in:
     - Historical base rates ("crypto winter has occurred 3 of last 10 years")
     - Observable conditions ("if BTC <$50K, which has happened X times")
     - Verifiable triggers ("management has missed guidance 2 of last 8 quarters")
   - If you cannot ground a probability, use qualitative language instead
5. **Catalysts** — Milestone-bound with observable verification sources **(UPDATED v1.1.0)**
   - Prefer: "Exit if TVL <$500M at 12 months post-launch" (verifiable via L2BEAT)
   - Avoid: "Exit if no traction by Q4 2026" (arbitrary calendar)
   - Each catalyst needs: milestone, verification source, action if hit/missed
6. **Risks** — Specific, quantified, kill conditions
7. **Decision framework** — Sizing, timing, exit **(UPDATED v1.1.0)**
   - **"Where Would You Act?" (REQUIRED):** Every memo must answer:
     - If recommending: Entry price, position size, exit targets
     - If passing: The specific price at which you WOULD buy/sell + what information would change your mind at current price
   - This section is non-negotiable. "Watchlist" without action criteria is not a decision.

**Phase 3: Self-Critique**
Apply rubric (D3):
- [ ] Thesis Clarity: Falsifiable? Variant view explicit?
- [ ] Evidence Quality: Primary or just filings?
- [ ] Valuation Rigor: Multiple methods? Sensitivity? Entry price derived?
- [ ] Risk Framework: Specific kill conditions with milestones?
- [ ] Decision Readiness: Sizing, timing, exits? Action price if passing?

**Target: Score 7+ before finalizing**

**Phase 4: Red Team**
- What's the strongest bear case?
- What would make you exit immediately?
- What evidence would falsify thesis?
- Who's on the other side and why?

**Phase 4.5: Response to Research Director Critique (Iterations 2-5 ONLY) (NEW v1.2.0)**

For iterations 2-5, you MUST begin your memo with an explicit response section addressing each point from the Research Director's feedback. This creates an audit trail of your analytical evolution.

**Required Format:**

```markdown
## Response to Research Director Critique

### Critique: "[Quote the exact RD critique]"
**Verdict:** Accept / Reject / Partially Accept
**Response:** [1-2 sentences explaining how this changes or doesn't change your analysis]
**Evidence:** [Cite new sources or reasoning that supports your response]

[Repeat for each RD critique]

### What I Got Wrong in v[N-1] (if applicable)
1. [Specific error or blind spot]
2. [Another error]

---
```

**Verdict Guidelines:**
- **Accept**: RD was right, your analysis changes materially
- **Reject**: RD's point doesn't hold after investigation, explain why with evidence
- **Partially Accept**: Valid concern but limited impact, specify what changes

**Why This Matters:**
- Forces explicit engagement with critique (no silent updates)
- Creates visibility for human reviewers into analytical rigor
- Thesis reversals with error acknowledgment demonstrate strength, not weakness
- RD will score your engagement quality—shallow responses lower your credibility

**Phase 5: Pre-Submission Checklist (NEW v1.1.0)**

Before finalizing, answer these questions honestly:

1. **Entry Price Test:** "If I removed the current stock price from this memo, could I still derive my entry price from the valuation analysis?"
   - If no → Entry is anchored, not derived. Revise valuation section.

2. **Action Test:** "Where exactly would I act—buy or sell—and at what price?"
   - If unclear → Decision framework incomplete. Add specific action price.

3. **Milestone Test:** "What specific, observable milestone would prove my thesis right or wrong?"
   - If only calendar dates → Convert to milestone-based triggers with verification sources.

4. **Primary Source Test:** "Did I cite at least one primary source, or is this entirely facts + opinions?"
   - If no primary sources → Acknowledge limitation explicitly; consider what primary research would add.

5. **Probability Test:** "If I used probability weights, can I cite the evidence basis for each?"
   - If no → Replace with qualitative descriptions or add evidence basis.

6. **Immediate Action Test:** "What news tomorrow would make me a buyer/seller at today's price?"
   - If nothing → Either conviction is low or you haven't thought through information triggers.

**Minimum passing: 4 of 6 answered affirmatively. Target: 6 of 6.**

**Phase 6: Source Documentation (REQUIRED) (NEW v1.2.0)**

At the end of each memo iteration, include a Sources Used section:

| # | Source | Link | Type | Summary (1 sentence) |
|---|--------|------|------|----------------------|
| 1 | [Source name] | [URL] | Fact / Opinion / Primary / Source File | What this source contributed |

**Source Type Definitions:**
- **Fact**: SEC filings, earnings releases, on-chain data, court documents
- **Opinion**: Analyst research, news analysis, price targets
- **Primary**: CEO interviews, employee reviews, GitHub activity, customer feedback
- **Source File**: Pre-gathered research from `[TICKER]_webSource.json`

**Link Requirements:**
- Full URL for all web sources (e.g., `https://sec.gov/...`)
- SEC filings: EDGAR link
- Source file entries: `[TICKER]_webSource.json`
- Paywalled sources: Note `[paywalled]` after URL

**Example:**
| # | Source | Link | Type | Summary |
|---|--------|------|------|---------|
| 1 | AAPL 10-K FY2024 | https://sec.gov/cgi-bin/browse-edgar?action=getcompany&CIK=0000320193 | Fact | Revenue mix showing 52% services vs hardware shift |
| 2 | Tim Cook WWDC 2024 keynote | https://youtube.com/watch?v=xyz | Primary | Direct statement on AI strategy: "Privacy is a fundamental human right" |
| 3 | Goldman Sachs initiation | https://gs.com/research/... [paywalled] | Opinion | $210 PT based on 28x P/E, highlights services margin expansion |
| 4 | Competitor margin data | AAPL_webSource.json | Source File | Apple leads industry at 46% gross margin |

**Minimum requirement:** At least 3 sources cited with links. If link unavailable, explain why.

#### Anti-Pattern List (from corpus analysis)

| Anti-Pattern | Frequency | How Elite Memos Avoid |
|--------------|-----------|----------------------|
| Thesis-free narrative | ~20% | Lead with thesis in first paragraph |
| Valuation-free optimism | ~9% | Always include target with methodology |
| Risk-free conviction | ~30% | Enumerate risks with kill conditions |
| Catalyst-free hope | ~23% | Specify milestone-bound catalysts |
| Evidence-free assertion | ~15% | Cite specific sources, quantify |
| Consensus-echo | ~81% | Explicitly state variant view |
| Length-without-depth | ~5% | Target 10-15K chars with substance |
| Confidence theater | ~10% | Acknowledge uncertainty, show scenarios |

#### Minimum Viable vs Elite Memo

| Aspect | Minimum Viable (5-6) | Elite (8-10) |
|--------|---------------------|--------------|
| Thesis | Clear statement | Falsifiable with variant view |
| Valuation | Single method | Multiple methods + sensitivity + derived entry price |
| Risks | Generic list | Specific with milestone-based kill conditions |
| Catalyst | Vague mention | Milestone-bound with verification source |
| Decision | Basic recommendation | Full framework (sizing, timing, exits) or pass with action price |
| Evidence | Public filings | Primary research cited (target + competitors) |
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
| H009 | Source Classification | **NEW v1.1.0 - candidate** | Primary source citation correlates with quality |
| H010 | Derived Entry Price | **NEW v1.1.0 - candidate** | Entry price derived vs anchored |
| H011 | Dual-Source Integration | **NEW v1.2.0 - candidate** | Source file + web verification produces superior analysis |

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

### Ungrounded Probability Theater (NEW v1.1.0)
- **Risk:** Arbitrary probability weights (e.g., "25% bear, 50% base, 25% bull") create false precision
- **Mitigation:** Require probabilities to cite historical base rates or observable conditions; otherwise use qualitative descriptions
- **Example (bad):** "Bear case: 25% probability" (no basis)
- **Example (good):** "Bear case: historically occurs 2-3x per decade based on last 30 years of data"

### Data Leakage
- Comments contain outcome information → Train on description_text only
- Updates may reference post-pitch events → Validate date consistency

### Memorization Risk
- Risk: AI reproduces source phrasing
- Mitigation: Extract patterns not text, similarity threshold check

---

## G) DUAL-SOURCE PROTOCOL (NEW v1.2.0)

### Rule: Source File + Web Search Handshake

When a source file (`[TICKER]_webSource.json`) is provided, the following protocol is MANDATORY:

**The Constraint:**
- You CANNOT cite the source file without a web search to verify or extend it
- You CANNOT make a web search without first checking what the source file says

**Rationale:**
- Source files may be outdated—web searches verify currency
- Web searches alone miss context the user already gathered
- Integration produces superior analysis

### Implementation

For each major claim in your analysis:

| Step | Action | Output |
|------|--------|--------|
| 1. ANCHOR | Check source file for relevant information | Quote or note absence |
| 2. EXTEND | Web search to verify, update, or expand | Fresh data point |
| 3. RECONCILE | Compare and synthesize | Your conclusion with both citations |

### Example

**Claim:** "AAPL trades at 28x forward P/E"

| Step | Source File Says | Web Search Found | Reconciled |
|------|------------------|------------------|------------|
| ANCHOR | "AAPL at 26x P/E (as of Nov 2024)" | — | Starting point |
| EXTEND | — | "Current P/E 28.3x per Yahoo Finance" | Updated data |
| RECONCILE | — | — | "AAPL trades at 28x forward P/E (up from 26x in Nov 2024 source file, confirmed via Yahoo Finance Jan 2025)" |

### Exceptions

The protocol applies ONLY when `[TICKER]_webSource.json` is provided. If no source file:
- Web searches proceed normally
- No anchoring step required

### Anti-Patterns

| Anti-Pattern | Problem | Fix |
|--------------|---------|-----|
| Source-only analysis | "Per the source file, revenue grew 10%" with no verification | Add web search to confirm/update |
| Web-only analysis | Fresh search ignoring provided context | Check source file first |
| Parallel tracks | Citing source and web separately without reconciliation | Explicitly reconcile in conclusion |

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
- Header: "Buyside Memo Engine v1.2.0"
- Footer: Page number, "Generated: 2026-01-19"

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

*End of v1.2.0 Instruction Manual*

**Changes from v1.1.0:** Input specification (required/optional inputs with priority), source documentation requirement (Phase 6), dual-source protocol (Section G).
