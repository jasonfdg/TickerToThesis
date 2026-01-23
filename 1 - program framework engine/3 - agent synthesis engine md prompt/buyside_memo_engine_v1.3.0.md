# Buyside Memo Engine v1.3.0

**Related Agent:** Source Scout — runs after RD review each iteration to gather primary sources for gaps identified by analysts and RD.

---

## A) INPUT SPECIFICATION

### Required Input
| Input | Required | Description |
|-------|----------|-------------|
| **Ticker** | YES | Stock ticker symbol (e.g., AAPL, MSFT) |

### Optional Inputs (Priority Order)
| Input | Priority | Description |
|-------|----------|-------------|
| **Prompt** | 1 (highest) | Specific research question or directive |
| **Research Director Feedback** | 2 | Prior iteration feedback from research director |
| **Analyst Reports** | 3 | Third-party analyst research |
| **Source File** | 4 (lowest) | Pre-gathered web research: `[TICKER]_webSource.json` |

**Priority Rules:** Higher-priority inputs override lower when conflicts arise. All provided inputs must be considered.

---

## B) TRAITS OF ELITE MEMOS

**Structural Requirements:**
0. **Key Forces identification** — What 1-3 forces will materially move the needle? (Must be explicit in first paragraph)
1. Explicit thesis in first 2-3 sentences
2. Quantified valuation (2+ methods)
3. Falsifiable risks with kill conditions
4. Milestone-bound catalysts (not calendar dates)
5. **Variant view — why market is wrong** ← CRITICAL DIFFERENTIATOR (only 19% of corpus)

**Evidence Quality:**
6. Primary sources over secondary (see hierarchy below)
7. Financial model sensitivity (ranges, not point estimates)
8. Management capital allocation with examples
9. Competitive positioning quantified (only 44% of corpus)

**Decision-Readiness:**
10. Position sizing rationale
11. Kill conditions (explicit "exit if")
12. Actionable timing (entry strategy)

**Benchmarks:**
- **Total Report:** 20,000-30,000 characters (including RD Response & Sources)
- **Body Content (CRITICAL):** 12,000-20,000 characters of substantive analysis
  - Body = everything from first `#` header after RD Response to Sources table
  - For v1 reports: Body = entire report minus Sources table
  - **This is non-negotiable**—compressed bodies (<12K chars) cannot achieve >7.0 scores
- Target score: >7.0

**Body Content Self-Check:**
Before finalizing, verify your analytical body contains 12,000+ characters. If short, your report lacks institutional depth. Expand:
- Each key force needs 2,000-3,000 characters of evidence-backed analysis
- Valuation section needs full sensitivity table + methodology (2,000+ chars)
- Variant view needs complete evidence chain (1,500+ chars)
- Risks section needs 3+ quantified risks with specific kill conditions (1,500+ chars)

**Anti-Pattern Examples:**
- Business Quality section under 500 words → insufficient competitive analysis
- Valuation with only one method and no sensitivity → unrigorous
- Kill conditions like "revenue declines" without thresholds → unspecific
- Variant view stated without evidence chain → unsubstantiated

### Evidence Hierarchy (The Differentiator)

**The Core Question:** "Is this where the information ORIGINATED, or where it was AGGREGATED/INTERPRETED?"

| Source Type | Definition | Examples |
|-------------|------------|----------|
| **Primary Sources** | Direct voice or behavior from participants | See categories below |
| **Facts** | Verifiable, auditable data from official records | SEC filings, earnings releases, court documents |
| **Opinions** | Interpretations by observers | Sell-side research, news analysis, price targets |

**Primary Source Categories:**
1. **Direct Voice** — CEO interviews, podcasts, conference presentations, executive quotes
2. **Stakeholder Signals** — Glassdoor, Blind, customer reviews (App Store, Trustpilot, G2)
3. **Behavioral Data** — GitHub activity, job postings, patents, insider transactions
4. **Community Discourse** — Reddit, forums, Discord from actual participants

**Competitor Research (Apply Same Framework):**
- Competitor filings, market share, pricing
- Competitor exec interviews, employee reviews
- Customer comparisons ("switched from X to Y because...")

**Source Requirements:**
| Type | Minimum | Purpose |
|------|---------|---------|
| Primary Sources | 3+ | Anchor evidence (the differentiator) |
| Total Sources | 8-10+ | Comprehensive research coverage |

Each primary source must be formatted as a quote block with attribution. If fewer than 3 primary sources, explicitly acknowledge the gap and request Source Scout follow-up. Fewer than 3 caps Evidence Quality at 6.

**CRITICAL — NEVER FABRICATE QUOTES:** Only use quotes that actually exist in source materials. Do not invent, simulate, or create hypothetical quotes attributed to executives, analysts, or any source. If you cannot find a real quote, paraphrase and cite without quotation marks. Fabricated quotes are grounds for memo rejection.

---

## C) DELIVERABLES

### C1) Style Taxonomy (4 Buckets)

#### Bucket 1: Long-term Compounder
*Quality businesses with durable advantages, multi-year hold*

**Template Structure:**
- Business model + sustainable competitive advantage
- Thesis: why this compounds at above-market rates
- Management track record + capital allocation
- Valuation: DCF with explicit assumptions + scenarios
- Risks with kill conditions
- **Variant view (REQUIRED)**

**Required:** ROIC trend 5+ years, moat evidence, DCF assumptions explicit, entry price derived from valuation (not anchored to current).

---

#### Bucket 2: Catalyst-Driven Long
*Event-driven, 6-18 month horizon*

**Template Structure:**
- Situation + specific catalyst
- Price gap: current vs post-catalyst fair value
- Catalyst analysis: probability, timeline, confirmation/disconfirmation signals
- Risk-adjusted return (probability-weighted)
- Kill conditions

**Required:** Catalyst timing with milestone, probability-weighted return, downside if catalyst fails.

---

#### Bucket 3: Short Position
*Overvaluation, broken thesis, negative catalyst*

**Template Structure:**
- Bear thesis + variant view (what bulls believe that's wrong)
- Evidence hierarchy: business deterioration → accounting red flags → competitive threats
- Valuation gap
- Short-specific risks: squeeze, borrow, timing
- Stop-loss

**Required:** Squeeze risk quantified, borrow confirmed, position size limits (max 3%), kill condition defined.

---

#### Bucket 4: Secular Short
*Structural decline, 3-5+ year horizon*

**Template Structure:**
- Secular force destroying business
- Multi-year decline evidence (3+ years)
- Terminal value / endgame analysis
- Long-duration risks: value trap reversal, squeeze during rallies
- Quarterly monitoring criteria

**Required:** Secular force quantified, trend evidence, small position (max 1-2%).

---

#### Decision Requirements

**Position Recommendation:** Classify into exactly one bucket. No hedging between buckets.

**Pass Decision:** Must include:
1. **Action Price** — At what price would you buy/sell?
2. **Information Trigger** — What news would make you act at current price?

**Pass ≠ Watchlist.** A pass without action price is not a decision.

---

### C2) Scoring Rubric

| Dimension | Weight | Score 5 | Score 8-10 |
|-----------|--------|---------|------------|
| **Thesis Clarity** | 25% | Clear but no variant view | Falsifiable + variant view + "wrong if" conditions |
| **Evidence Quality** | 25% | Public filings only (ceiling: 6) | Primary research from multiple categories |
| **Valuation Rigor** | 20% | Single method | Multiple methods + sensitivity + derived entry price |
| **Risk Framework** | 15% | Risks listed but not quantified | Specific kill conditions with milestones |
| **Decision Readiness** | 15% | Vague timing, no sizing | Entry/exit/sizing + action price if passing |

**Probability Grounding:** If using probability weights, must cite evidence basis (e.g., "Bear case historically occurs 2-3x per decade"). Ungrounded probabilities → use qualitative descriptions instead.

---

### C3) Writing Playbook

**Phase 1: Pre-Writing**
1. Classify bucket (1-4)
2. Draft thesis in 2-3 sentences
3. Identify variant view (if none, acknowledge consensus)
4. Gather evidence: **Primary Sources (the differentiator)** → Facts → Opinions. If primary sources are lacking, flag for Source Scout in next iteration.
5. Select 2+ valuation methods
6. Enumerate top 3 risks with kill conditions

**Phase 2: Draft Structure**
1. **Open with thesis** — First paragraph states opportunity
2. **Business overview** — What company does, how it makes money, competitive position
3. **Investment thesis** — Why attractive now, variant view
4. **Valuation** — Multiple methods, assumptions explicit, entry price derived
5. **Catalysts** — Milestone-bound with verification sources
6. **Risks** — Specific, quantified, kill conditions
7. **Decision framework** — Sizing, timing, exit

**Phase 3: Self-Critique (Apply Rubric)**
- [ ] Thesis falsifiable? Variant view explicit?
- [ ] Evidence primary or just filings?
- [ ] Multiple valuation methods? Entry derived, not anchored?
- [ ] Kill conditions with milestones?
- [ ] Sizing, timing, exits specified?

**Target: Score 7+ before finalizing.**

**Phase 4: Red Team**
- Strongest bear case?
- Immediate exit trigger?
- Falsifying evidence?
- Who's on the other side and why?

**Phase 4.5: RD Response (After Iteration 1 ONLY)**

```markdown
## Response to Research Director Critique

### Critique: "[Quote exact RD critique]"
**Verdict:** Accept / Reject / Partially Accept
**Response:** [1-2 sentences]
**Evidence:** [Citation supporting response]

[Repeat for each critique]

### What I Got Wrong in v[N-1]
1. [Specific error]
2. [Another error]
```

**Verdict Guidelines:**
- **Accept**: RD was right, analysis changes materially
- **Reject**: RD's point doesn't hold after investigation (explain with evidence)
- **Partially Accept**: Valid concern but limited impact

**Phase 5: Pre-Submission Checklist**
1. Entry price derivable without current price? → If no, revise
2. Action price specified? → If no, add
3. Observable milestone defined? → If calendar only, convert
4. Primary source cited? → If no, flag for Source Scout follow-up and acknowledge ceiling
5. Probabilities grounded? → If no, use qualitative
6. What news would trigger action today? → If nothing, low conviction
7. Body content ≥12,000 characters? → If no, expand analysis depth (see Benchmarks)

**Minimum passing: 5/7. Target: 7/7.**

**Phase 6: Source Documentation (REQUIRED)**

| # | Source | Link | Type | Summary |
|---|--------|------|------|---------|
| 1 | [Name] | [URL] | Fact/Opinion/Primary/Source File | [1 sentence] |

**Cite ALL relevant sources. No limit.** Minimum: 3 sources with links. If unavailable, explain why.

---

## D) DUAL-SOURCE PROTOCOL

When source file (`[TICKER]_webSource.json`) is provided:

| Step | Action |
|------|--------|
| **ANCHOR** | Check source file first for relevant info |
| **EXTEND** | Web search to verify/update |
| **RECONCILE** | Synthesize both with citations |

**Rule:** Cannot cite source file without web verification. Cannot web search without checking source file first.

**Anti-Patterns:**
- Source-only analysis (no verification) → Flag for Source Scout and add web search
- Web-only analysis (ignoring context) → Check source file first
- Parallel tracks (no reconciliation) → Explicitly reconcile

---

*End of v1.3.0*
