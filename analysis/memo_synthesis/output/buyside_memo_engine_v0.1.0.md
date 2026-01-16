# Buyside Memo Engine - Instruction Manual

**Version:** v0.1.0
**Generated:** 2026-01-16T14:32:28
**Run ID:** iteration-001-priority

---

## A) RUN METADATA

### Dataset Coverage
| Metric | Value |
|--------|-------|
| Folder scanned | `data/vic/github_dump/extracted/` |
| Total files in corpus | 13,635 |
| Files analyzed this iteration | 1,771 |
| Memos parsed | 1,771 |
| Parse errors | 0 |

### Files Analyzed
- **Contest Winners:** 700 files
- **Short Positions:** 1,169 files
- **Union (priority set):** 1,771 unique files

### Sampling Plan
This iteration used a **priority sampling strategy**:
1. All contest winners (proxy for community-validated quality)
2. All short positions (underrepresented category requiring distinct analysis)
3. Union of both sets to capture overlap

### Date Distribution (files analyzed)
| Year | Count | Year | Count |
|------|-------|------|-------|
| 2000 | 2 | 2012 | 88 |
| 2001 | 50 | 2013 | 90 |
| 2002 | 67 | 2014 | 84 |
| 2003 | 71 | 2015 | 110 |
| 2004 | 86 | 2016 | 98 |
| 2005 | 78 | 2017 | 85 |
| 2006 | 88 | 2018 | 94 |
| 2007 | 86 | 2019 | 86 |
| 2008 | 84 | 2020 | 102 |
| 2009 | 62 | 2021 | 68 |
| 2010 | 80 | 2022 | 47 |
| 2011 | 65 | | |

---

## B) DIFF VS LATEST VERSION

**No prior version found. This is v0.1.0 baseline.**

---

## C) DEFINING TRAITS OF ELITE BUYSIDE MEMOS

The following traits distinguish high-quality, decision-grade buyside memos based on analysis of 1,771 memos (700 contest winners + 1,169 shorts):

### Structural Completeness
1. **Contains explicit thesis statement** — 84% of analyzed memos include a clear "why" section that articulates the investment case in 2-3 sentences. Testable: presence of keywords like "thesis," "investment case," "opportunity," or explicit summary section.

2. **Includes quantified valuation framework** — 92% have dedicated valuation sections with specific target prices or fair value estimates. Elite memos use multiple methods (EV/EBITDA + DCF + comps) rather than single-point estimates.

3. **Presents falsifiable risk factors** — 77% enumerate specific risks with potential impact quantification. Elite memos phrase risks as testable conditions: "If X happens, thesis breaks."

4. **Identifies time-bound catalysts** — 84% include catalyst sections. Elite memos specify catalyst timing ("Q2 earnings," "post-merger integration") rather than vague triggers.

5. **Demonstrates variant view with evidence** — Only 23% explicitly articulate why the market is wrong. This is the clearest separator between average and elite memos. Testable: presence of "market misses," "consensus doesn't understand," or direct refutation of bear/bull case.

### Evidence Quality
6. **Uses primary data over secondary** — Elite memos cite channel checks, management conversations, customer interviews, or proprietary analysis rather than relying solely on sell-side research or public filings.

7. **Provides financial model sensitivity** — Rather than single-point estimates, elite memos show how valuation changes across key assumptions (revenue growth rates, margin scenarios, multiple ranges).

8. **Includes management quality assessment** — 86% discuss management. Elite memos evaluate capital allocation track record, insider ownership alignment, and historical guidance accuracy.

9. **Maps competitive positioning explicitly** — Only 44% include competitive analysis. Elite memos quantify market share, identify moat sources, and assess competitive threat probability.

### Decision-Readiness
10. **Specifies position sizing rationale** — Elite memos address why a particular position size is appropriate given conviction level, liquidity, and portfolio context.

11. **Defines kill conditions** — Best memos include explicit "I would exit if" criteria, not just risks but specific falsification triggers.

12. **Provides actionable timing** — Elite memos indicate whether to build position immediately, scale in, or wait for specific entry points.

### Content Metrics (from analysis)
13. **Optimal description length: 10,000-20,000 characters** — Median description length: 12,870 chars. Too short (<5,000) suggests insufficient depth; too long (>40,000) often indicates unfocused analysis.

14. **Separate catalyst section** — 93% of analyzed memos have dedicated catalyst text. This structural separation improves decision-readiness.

15. **Average decision-readiness score: 0.79** — Based on presence of key structural elements weighted by importance.

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
  "date": "string (original format: 'Month DD, YYYY')",
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

#### Extended Schema (proposed)
```json
{
  "sector": "string (GICS sector classification)",
  "industry": "string (GICS sub-industry)",
  "market_cap_bucket": "enum: 'nano' | 'micro' | 'small' | 'mid' | 'large' | 'mega'",
  "thesis_type": "enum: see taxonomy below",
  "time_horizon": "enum: 'short-term (<6mo)' | 'medium-term (6-18mo)' | 'long-term (>18mo)'",
  "valuation_methods": "array of strings",
  "catalyst_types": "array of strings",
  "risk_factors": "array of strings",
  "decision_readiness_score": "float 0-1",
  "structural_completeness": "float 0-1",
  "has_variant_view": "boolean",
  "description_length": "integer (characters)",
  "extracted_at": "ISO timestamp"
}
```

#### Extraction Notes
- **Date parsing:** Regex pattern `([A-Z][a-z]+ \d{1,2}, \d{4})` captures VIC date format
- **Position type:** Check `is_short` boolean or regex for "short" in position field
- **Thesis type:** Model-assisted classification using keyword detection (see D4)
- **Valuation methods:** Keyword extraction for DCF, P/E, EV/EBITDA, etc.

#### Data Quality Checks
- Reject memos with `description_text` < 500 characters
- Flag memos without catalyst_text for manual review
- Validate date falls within expected range (2000-present)
- Check ticker format (uppercase, 1-5 characters typical)

---

### D2) Investment Style Taxonomy (4 Buckets)

#### Bucket 1: Long-term Compounder (Long)
*Quality businesses with durable advantages, multi-year holding period*

**Discovered Patterns (from 288 memos):**
- **Common thesis structures:** Moat-first framing, emphasis on ROIC sustainability, management track record of capital allocation, recurring revenue or high switching costs
- **Typical valuation methods:** DCF with terminal value, P/E relative to growth (PEG), EV/EBITDA with peer comps
- **Risk framing:** Focus on competitive threats, management succession, capital allocation missteps
- **Catalyst types:** Often catalyst-light; relies on compounding returns rather than event triggers
- **Sector concentrations:** Technology, healthcare, consumer staples, industrials with niche dominance

**Style-Specific Template:**
```markdown
## [COMPANY] - Long-term Compounder

### Business Overview
- What does the company do?
- What is the sustainable competitive advantage (moat)?
- How durable is the moat (quantify if possible)?

### Investment Thesis
- Why will this business compound capital at above-average rates?
- What is the ROIC/ROE track record and driver?
- Why is current valuation attractive for a multi-year hold?

### Management & Capital Allocation
- Track record of capital deployment
- Insider ownership and alignment
- Historical guidance accuracy

### Valuation
- Primary method: DCF with explicit assumptions
- Sanity check: P/E vs growth, peer comparison
- Upside/base/downside scenarios

### Risks
- Competitive threats
- Secular industry changes
- Management/key person risk

### Why Now? (if applicable)
- Entry point rationale
- Why market underappreciates the asset
```

**Decision Readiness Checklist:**
- [ ] ROIC trend quantified over 5+ years
- [ ] Moat source explicitly identified and defended
- [ ] Management capital allocation graded (A/B/C/F)
- [ ] Valuation shows >15% annualized return expectation
- [ ] Competitive positioning mapped vs peers
- [ ] Kill condition: moat degradation indicators specified

**Common Traps:**
- Overpaying for quality (ignoring valuation discipline)
- Confusing temporary tailwinds with durable moat
- Insufficient attention to capital allocation changes
- Elite memos avoid this by: requiring explicit "what price is too high" threshold

---

#### Bucket 2: Mid-to-Short-term Trade (Long)
*Event-driven, catalyst-dependent, or value unlocks with 6-18 month horizon*

**Discovered Patterns (from 280 memos: Special Situations + Turnaround/Cyclical + Growth at Reasonable Price):**
- **Common thesis structures:** Catalyst-first framing, explicit timeline, gap between current price and event-driven fair value
- **Typical valuation methods:** Sum-of-parts, LBO/takeout analysis, normalized earnings, replacement cost
- **Risk framing:** Catalyst failure scenarios, timing risk, execution risk
- **Catalyst types:** M&A/buyout (929 mentions), earnings inflection (1,308), restructuring (204), spin-offs (184)
- **Sector concentrations:** Industrials, financials, consumer discretionary, energy (cyclical plays)

**Style-Specific Template:**
```markdown
## [COMPANY] - Catalyst-Driven Long

### Situation Overview
- What is the current situation?
- What event/catalyst creates the opportunity?

### Investment Thesis
- What is the specific catalyst and expected timing?
- What is the gap between current price and post-catalyst value?
- Why is the market missing this opportunity?

### Catalyst Analysis
- Probability of catalyst occurring (high/medium/low with rationale)
- Timeline: specific date or range
- What confirms/disconfirms catalyst thesis?

### Valuation
- Current price vs catalyst-adjusted fair value
- Method: [Sum-of-parts / Takeout / Normalized earnings]
- Risk-adjusted return calculation

### Risks & Kill Conditions
- What kills the thesis? (be specific)
- Timing risk: what if catalyst delays?
- Execution risk: what could go wrong?

### Position Sizing
- Conviction level and appropriate size
- Entry/exit strategy
```

**Decision Readiness Checklist:**
- [ ] Catalyst timing specified (not "eventually")
- [ ] Probability-weighted return calculated
- [ ] Downside quantified if catalyst fails
- [ ] Kill conditions explicitly stated
- [ ] Position sizing justified

**Common Traps:**
- Catalyst timing slip without thesis update
- Overweighting low-probability catalysts
- Ignoring opportunity cost during waiting period
- Elite memos avoid this by: specifying "exit if no catalyst by [date]"

---

#### Bucket 3: Mid-to-Short-term Trade (Short)
*Overvaluation, broken thesis, or imminent negative catalyst*

**Discovered Patterns (from 631 memos: Overvaluation + Business Deterioration + Catalyst-Driven Short + General Short):**
- **Common thesis structures:** Valuation gap framing, business deterioration evidence, accounting red flags, competitive disruption
- **Typical valuation methods:** Relative valuation (showing premium to peers), historical multiple analysis, normalized earnings showing overstatement
- **Risk framing:** Short squeeze risk, position sizing, borrow availability, timing
- **Catalyst types:** Earnings miss (primary), guidance cut, debt refinancing issues, competitive losses, fraud exposure
- **Sector concentrations:** Technology (overvaluation), retail (disruption), financials (credit cycle)

**Style-Specific Template:**
```markdown
## [COMPANY] - Short Position

### Bear Thesis
- Why is this stock overvalued/deteriorating?
- What does the market believe that is wrong?

### Evidence
- [PRIMARY] Quantified business deterioration metrics
- [SECONDARY] Accounting concerns or red flags
- [TERTIARY] Competitive threats materializing

### Valuation
- Current valuation vs appropriate fair value
- What multiple/metric should this trade at? Why?
- Downside target and basis

### Catalyst
- What triggers the repricing?
- Timeline expectation
- Leading indicators to monitor

### Risks (critical for shorts)
- Short squeeze potential (short interest, days to cover)
- Borrow availability and cost
- M&A/takeout risk
- Timing risk

### Position Sizing & Management
- Maximum position size (% of portfolio)
- Stop-loss discipline
- Scaling plan
```

**Decision Readiness Checklist:**
- [ ] Variant view clearly articulated (why market is wrong)
- [ ] Evidence is primary, not derivative
- [ ] Short squeeze risk assessed (short interest %, days to cover)
- [ ] Borrow confirmed available
- [ ] Position sizing appropriate for short (smaller than long conviction)
- [ ] Stop-loss or exit trigger defined

**Common Traps:**
- Fighting momentum without catalyst
- Underestimating squeeze risk
- Thesis creep ("it's more overvalued now" without re-evaluating)
- Elite memos avoid this by: hard stop-loss rules, position size limits

---

#### Bucket 4: Long-term Secular Short
*Structural decline, technological disruption, or terminal business model*

**Discovered Patterns (from 105 memos: Secular Decline):**
- **Common thesis structures:** Industry disruption narrative, technology obsolescence, structural demand decline, regulatory headwinds
- **Typical valuation methods:** Terminal value analysis, liquidation value, run-off scenarios
- **Risk framing:** Timing (can take years), short squeeze, value trap reversal
- **Catalyst types:** Quarterly deterioration accumulation, debt covenant breach, dividend cut, management departure
- **Sector concentrations:** Retail (e-commerce disruption), media (cord-cutting), legacy tech, print/publishing

**Style-Specific Template:**
```markdown
## [COMPANY] - Secular Short

### Structural Thesis
- What secular force is destroying this business?
- Is this thesis well-known or underappreciated?

### Evidence of Decline
- Revenue/volume trends (3+ years)
- Market share losses
- Customer behavior shifts
- Technology disruption timeline

### Endgame Analysis
- What is terminal value?
- Liquidation scenario
- Debt maturity wall / covenant risk

### Timing & Catalysts
- Near-term triggers to monitor
- Why now vs earlier/later?
- Quarterly checkpoints

### Risks
- "Value trap" reversal potential
- Short squeeze in bear market rallies
- Timing (secular shorts can take 3-5+ years)
- Position sizing for extended timeline

### Implementation
- Optimal position sizing for secular short
- Rolling vs static short position
- Use of puts vs direct short
```

**Decision Readiness Checklist:**
- [ ] Secular force clearly identified and quantified
- [ ] Evidence shows trend is accelerating or stable (not reversing)
- [ ] Terminal value / endgame articulated
- [ ] Timing framework acknowledges multi-year horizon
- [ ] Position sized for extended holding period
- [ ] Quarterly monitoring criteria defined

**Common Traps:**
- Underestimating how long decline can take
- Getting squeezed during bear market rallies
- Management pivot surprising bears
- Elite memos avoid this by: smaller position sizes, put spreads, patience

---

### D3) Scoring Rubric (1-10, AI-Executable)

#### Dimensions (5 total)

| Dimension | Weight | Definition |
|-----------|--------|------------|
| Thesis Clarity | 25% | Is the investment thesis clearly stated and falsifiable? |
| Evidence Quality | 25% | Is evidence primary, quantified, and verifiable? |
| Valuation Rigor | 20% | Are multiple valuation methods used with explicit assumptions? |
| Risk Framework | 15% | Are risks specific, quantified, and paired with kill conditions? |
| Decision Readiness | 15% | Does memo include timing, sizing, and exit criteria? |

#### Scoring Anchors

**Thesis Clarity (0-10):**
- **2:** Vague assertion without supporting logic ("this is cheap")
- **5:** Clear thesis but lacks falsification criteria or variant view
- **8:** Explicit thesis with variant view and testable predictions
- **10:** Thesis is falsifiable, time-bound, and articulates exactly what would prove it wrong

**Evidence Quality (0-10):**
- **2:** Relies on sell-side research or general assertions
- **5:** Uses public filings and basic quantitative analysis
- **8:** Includes primary research (channel checks, management, customers)
- **10:** Multiple primary sources with quantified findings and cross-validation

**Valuation Rigor (0-10):**
- **2:** No valuation or single vague metric ("it's cheap")
- **5:** Single valuation method with stated assumptions
- **8:** Multiple methods with sensitivity analysis and scenario ranges
- **10:** Comprehensive valuation with probability-weighted scenarios and explicit margin of safety

**Risk Framework (0-10):**
- **2:** Risks not mentioned or generic ("competition")
- **5:** Risks enumerated but not quantified or paired with responses
- **8:** Specific risks with impact quantification and kill conditions
- **10:** Risk-reward explicitly calculated with position sizing implications

**Decision Readiness (0-10):**
- **2:** No guidance on timing, sizing, or exits
- **5:** Timing mentioned but vague; no sizing guidance
- **8:** Specific catalyst timing, suggested position size, exit criteria
- **10:** Complete decision framework: entry, sizing, scaling, exit triggers, and monitoring plan

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

    weighted_sum = sum(
        dimensions[dim] * weights[dim]
        for dim in weights
    )

    return round(weighted_sum, 1)
```

#### Bias Handling
- **Outcome bias:** Score based on process quality at time of writing, not subsequent returns
- **Length bias:** Apply length penalty only if >40,000 chars without proportional depth
- **Confidence theater:** Penalize unsupported conviction language ("guaranteed," "can't lose")
- **Rhetorical polish:** Separate writing quality from analytical substance; weight substance

---

### D4) Feature Extraction Plan

#### Feature: Variant View
**Operational Definition:** Explicit articulation of why consensus/market is wrong about the investment.

**Detection Heuristics:**
- Keywords: "market misses," "consensus doesn't understand," "overlooked," "misperceived," "underappreciated"
- Pattern: Direct refutation of bull/bear case
- Section markers: "Why the Market is Wrong," "Variant Perception"

**Model Classification:**
- Binary: has_variant_view (true/false)
- Confidence threshold: 0.7 for positive classification
- Training: Label 200 memos manually, use for few-shot prompting

**Gold-Labeling Strategy:**
- Sample 100 high-quality memos (decision_readiness > 0.9)
- Manual label for variant view presence and quality
- Inter-rater reliability target: Cohen's kappa > 0.8

#### Feature: Evidence Specificity
**Operational Definition:** Whether evidence is primary (direct observation) or secondary (derived from public sources).

**Detection Heuristics:**
- Primary indicators: "spoke with management," "channel checks," "proprietary survey," "site visit," "customer interview"
- Secondary indicators: "according to analyst," "per 10-K," "management guided"

**Classification:**
- Scale: 1 (entirely secondary) to 5 (extensive primary research)
- Weight primary evidence terms higher in scoring

#### Feature: Valuation Framing
**Operational Definition:** Methods used and rigor of valuation analysis.

**Detection Heuristics:**
```python
valuation_patterns = {
    "DCF": r'\b(dcf|discounted cash flow|npv)\b',
    "P/E Multiple": r'\b(p/e|pe ratio|earnings multiple)\b',
    "EV/EBITDA": r'\b(ev/ebitda|enterprise value.*ebitda)\b',
    "Sum-of-Parts": r'\b(sum.of.parts|sotp|break.?up)\b',
    "NAV": r'\b(nav|net asset value|book value)\b',
    "Comp Analysis": r'\b(compar|peer|trading at.*vs)\b',
}
```

**Classification:**
- Count: number of distinct methods used
- Quality: presence of sensitivity analysis keywords

#### Feature: Risk/Kill Conditions
**Operational Definition:** Explicit conditions under which the thesis would be falsified.

**Detection Heuristics:**
- Keywords: "thesis breaks if," "would exit if," "kill condition," "stop loss"
- Pattern: Conditional statements about position exit

**Classification:**
- Binary: has_kill_conditions
- Quality: specificity of conditions (vague vs quantified)

#### Feature: Catalyst Timing
**Operational Definition:** Whether catalysts are time-bound or vague.

**Detection Heuristics:**
- Time-bound: specific dates, quarters, "within X months"
- Vague: "eventually," "over time," "when market realizes"

**Classification:**
- Score 1-5: vague to specific timing

#### Feature: Decision Readiness
**Operational Definition:** Presence of actionable investment guidance.

**Detection Heuristics:**
- Position sizing: "1-3% position," "small position," "full position"
- Entry timing: "building position now," "waiting for pullback"
- Exit criteria: "would sell at," "target price," "exit trigger"

**Classification:**
- Composite score from sub-features (0-1 scale)

---

### D5) Synthesis Plan (Playbook + Templates + Anti-patterns)

#### Writing Playbook

**Phase 1: Research & Outline (before writing)**
1. Define investment style bucket (Compounder / Trade Long / Trade Short / Secular Short)
2. Articulate thesis in 2-3 sentences
3. Identify variant view (why market is wrong)
4. List 3-5 key evidence points
5. Select valuation methodology appropriate to style
6. Enumerate top 3 risks and kill conditions

**Phase 2: Drafting**
1. **Open with thesis** — First paragraph should state the opportunity clearly
2. **Business overview** — What the company does, competitive position
3. **Investment thesis deep-dive** — Why this is attractive now
4. **Valuation** — Multiple methods, explicit assumptions, scenario range
5. **Catalysts** — Time-bound triggers with probability assessment
6. **Risks** — Specific, quantified, paired with kill conditions
7. **Decision framework** — Sizing, timing, exit criteria

**Phase 3: Self-Critique Pass**
Apply the scoring rubric (D3) to your own draft:
- [ ] Thesis Clarity: Is it falsifiable? Is variant view explicit?
- [ ] Evidence Quality: Is it primary or just public filings?
- [ ] Valuation Rigor: Multiple methods? Sensitivity shown?
- [ ] Risk Framework: Specific kill conditions?
- [ ] Decision Readiness: Sizing, timing, exit criteria?

Target: Score 7+ before submission

**Phase 4: Red Team Pass**
Attack your own thesis:
- What's the strongest bear case?
- What would make you exit immediately?
- What evidence would falsify the thesis?
- Who's on the other side of this trade and why?

Document the red team analysis; elite memos include this.

#### Anti-Pattern List

| Anti-Pattern | Description | How Elite Memos Avoid |
|--------------|-------------|----------------------|
| Thesis-free narrative | Long description without clear "why invest" statement | Lead with thesis in first paragraph |
| Valuation-free optimism | "This is a great company" without fair value | Always include target price with methodology |
| Risk-free conviction | No discussion of what could go wrong | Enumerate risks with kill conditions |
| Catalyst-free hope | "Market will eventually recognize value" | Specify time-bound catalysts |
| Evidence-free assertion | Claims without supporting data | Cite specific sources, quantify claims |
| Consensus-echo | Restating sell-side thesis without variant view | Explicitly state what market misses |
| Length-without-depth | 30,000 words saying little | Target 10,000-20,000 chars with substance |
| Confidence theater | "Can't lose," "guaranteed" language | Acknowledge uncertainty, show scenarios |

#### Minimum Viable Memo vs Elite Memo

**Minimum Viable (score 5-6):**
- Clear thesis statement
- Single valuation method
- Generic risk list
- Vague catalyst mention
- 5,000-10,000 characters

**Elite Memo (score 8-10):**
- Falsifiable thesis with variant view
- Multiple valuation methods with sensitivity
- Specific risks with kill conditions
- Time-bound catalysts with probability
- Decision framework (sizing, timing, exits)
- Primary research evidence
- Red team analysis included
- 12,000-25,000 characters with depth

---

### D6) Validation Plan

#### Testing AI Memo Quality

**Blind Evaluation Design:**
1. Generate AI memo for ticker
2. Pair with human-written VIC memo for same ticker (if exists) or comparable company
3. Blind evaluator (human or AI) scores both using rubric (D3)
4. Compare scores; track win rate

**Holdout Sets:**
- **Time-based:** 2022 memos held out for testing (not seen during training)
- **Author-based:** Top 10 prolific authors held out
- **Style-based:** One example per thesis type per year held out

**Pairwise Ranking:**
- Present two memos (A/B) to evaluator
- Ask: "Which memo would you act on?"
- Track AI vs human win rate
- Target: AI memos preferred >50% of time against median VIC memo

#### Handling VIC Score Bias

**Date Stratification:**
- Compare memos within same year buckets (market conditions vary)
- Normalize for era-specific writing styles

**Vote-Weighting:**
- Higher weight to memos with more votes (signal strength)
- But recognize: low-vote memos may be quality but obscure

**Author Effects:**
- Track author-level quality consistency
- Some authors consistently high-rated; normalize for author

**Score Calibration:**
- VIC scores 6-7 are modal (regression to mean)
- Scores 8+ are rare (~10%); use as quality benchmark
- Scores 1-4 indicate problems; analyze for anti-patterns

#### Success Metrics

| Metric | Target | Measurement |
|--------|--------|-------------|
| Rubric Score Uplift | +1.5 points vs baseline | Compare AI v0.1 memos to average VIC memo |
| Pairwise Win Rate | >55% | Blind A/B comparison |
| Hallucination Rate | <5% | Fact-check sample of 50 claims per memo |
| Decision Readiness | >0.85 | Automated scoring using D4 features |
| Structural Completeness | >0.80 | All required sections present |

#### Failure Analysis Loop

When AI memo scores poorly:
1. Identify which rubric dimension failed
2. Trace to specific training data gap or prompt issue
3. Add targeted examples to training set
4. Re-run and compare
5. Document in version changelog

---

## E) LATENT QUALITY MODULE

### Hypothesis Bank Schema

```json
{
  "hypothesis_id": "string",
  "name": "string",
  "operational_definition": "string",
  "detection_cues": ["array of patterns/keywords"],
  "test_plan": "string (how to validate)",
  "status": "enum: 'candidate' | 'testing' | 'validated' | 'rejected' | 'core'",
  "evidence": {
    "predictive_correlation": "float (0-1)",
    "pairwise_discriminability": "float (0-1)",
    "sample_size": "integer"
  },
  "version_added": "semver string",
  "last_updated": "ISO timestamp"
}
```

### Current Hypothesis Bank

| ID | Name | Status | Evidence Strength |
|----|------|--------|------------------|
| H001 | Variant View Presence | candidate | Not yet tested |
| H002 | Primary Research Citation | candidate | Not yet tested |
| H003 | Multi-Method Valuation | candidate | Not yet tested |
| H004 | Explicit Kill Conditions | candidate | Not yet tested |
| H005 | Time-Bound Catalysts | candidate | Not yet tested |
| H006 | Management Quality Assessment | candidate | Not yet tested |
| H007 | Competitive Moat Mapping | candidate | Not yet tested |
| H008 | Position Sizing Rationale | candidate | Not yet tested |

### Promotion Criteria

A hypothesis is promoted to "Core Instruction" when:
1. **Predictive validity:** Feature presence correlates with score >0.3 after controlling for length/date/author
2. **Pairwise discriminability:** Rubric scorer correctly ranks memos 70%+ of time using this feature
3. **Ablation impact:** Removing feature from draft reduces decision-readiness score by >0.1

### Evaluation Harness

**Contrastive Analysis:**
- Sample: Top decile vs bottom decile memos within same year and sector
- Control: Match on memo length (+/- 20%)
- Measure: Feature presence rate in each group

**Predictive Testing:**
- Regression: Score ~ features + length + date + author_random_effect
- Target: Feature coefficient significant at p<0.05

**Pairwise Testing:**
- Present 100 memo pairs
- Ask scorer to identify higher-quality memo
- Measure: Accuracy when using feature vs not

### Changelog Discipline

**Version Bumps:**
- **X.0.0 (Major):** Schema changes, new required fields, taxonomy restructure
- **X.Y.0 (Minor):** New hypothesis promoted to Core, template updates, rubric refinements
- **X.Y.Z (Patch):** Bug fixes, wording clarifications, example additions

### Guardrails Against VIC House Style Overfitting

1. **External validation:** Test templates on non-VIC research (10-Ks, sell-side reports)
2. **Diverse author sampling:** Don't over-index on top VIC authors' style
3. **Substance over style:** Weight analytical completeness over prose quality
4. **Era normalization:** Compare within time periods, not across

---

## F) PITFALLS & COMPLIANCE

### Terms of Service / IP Constraints
- **No verbatim copying:** This manual distills patterns, not text
- **Attribution:** VIC memos are proprietary; this analysis is derivative
- **Usage:** For training AI agents, not republishing source content

### Analytical Biases

**Outcome Bias:**
- VIC scores partially reflect subsequent returns
- Address: Focus on process quality indicators, not outcomes
- Mitigation: Exclude memos with <6 months seasoning from scoring analysis

**Survivorship Bias:**
- Successful ideas more likely to be remembered/referenced
- Address: Include failed theses in training set
- Mitigation: Analyze shorts that worked and failed

**Author Effects:**
- Some authors have following regardless of quality
- Address: Normalize for author when analyzing score correlations
- Mitigation: Blind evaluation of memo quality

**Recency Bias:**
- Recent memos may have different style conventions
- Address: Stratify analysis by year
- Mitigation: Balance training set across time periods

### Rhetorical Polish vs Analytical Substance

**Risk:** Well-written but analytically weak memos may score high on readability.

**Mitigation:**
- Scoring rubric weights substance (thesis, evidence, valuation) over style
- Explicitly penalize confidence theater without supporting evidence
- Require quantification for claims to count as evidence

### Data Leakage

**Comments/Updates:**
- VIC comments often discuss thesis evolution, outcomes
- Risk: Training on comments leaks outcome information
- Mitigation: Primary training on description_text only; comments for sentiment analysis only

**Subsequent Filings:**
- Some memos reference events that occurred after pitch date
- Mitigation: Validate date consistency; flag anachronistic references

### Memorization Risk

**Risk:** AI reproduces distinctive phrasing from source memos.

**Mitigation:**
1. Extract patterns and rules, not text
2. Use abstract examples without company names
3. Test generated memos for verbatim overlap with training set
4. Implement similarity threshold check before output

---

## PDF Layout Notes

### Rendering Specifications
- **Margins:** 1 inch all sides
- **Font:** Body: 11pt serif (Times New Roman or equivalent); Headers: 12pt sans-serif (Helvetica)
- **Line spacing:** 1.15
- **Code blocks:** 10pt monospace, light gray background
- **Tables:** Bordered, header row shaded

### Page Breaks
- Section A (Metadata): Start new page
- Section C (Traits): Start new page
- Each D subsection: Start new page
- Section E (Latent Quality): Start new page
- Section F (Pitfalls): Start new page

### Headers/Footers
- Header: "Buyside Memo Engine v0.1.0"
- Footer: Page number, "Generated: 2026-01-16"

---

*End of v0.1.0 Instruction Manual*

**Next Steps:** Run iterations 2-25 to analyze remaining 11,864 memos and refine patterns.
