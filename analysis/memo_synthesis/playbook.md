# Writing Playbook - Buyside Memo Engine v0.1.0

## Overview

This playbook provides actionable rules, templates, and anti-patterns for writing decision-grade buyside memos.

---

## Core Principles

### Principle 1: Lead with the Edge
**Do:** Open with your variant view in the first paragraph.
**Why:** Decision-makers are busy. They need to know immediately why this opportunity exists.
**Verify:** Can a PM understand your thesis in 30 seconds?

### Principle 2: Prove, Don't Assert
**Do:** Every claim must have supporting evidence.
**Why:** Assertions without evidence are opinions, not analysis.
**Verify:** Highlight every claim—can you point to the evidence?

### Principle 3: Show Your Work
**Do:** Make assumptions explicit in valuation.
**Why:** Decision-makers need to stress-test your logic.
**Verify:** Could someone else reproduce your target price?

### Principle 4: Define Failure
**Do:** State what would prove your thesis wrong.
**Why:** Good investors are hypothesis-driven. Kill conditions show rigor.
**Verify:** Have you defined exit criteria?

### Principle 5: Enable Action
**Do:** End with clear, actionable recommendation.
**Why:** The memo exists to inform a decision.
**Verify:** Does the reader know what to do?

---

## Drafting Workflow

### Stage 1: Outline (Before Writing)

```
1. THESIS (1 sentence)
   What is the core bet? Long/short, target, catalyst.

2. VARIANT VIEW (1-2 sentences)
   What does the market believe? Why is the market wrong?

3. EVIDENCE LIST
   - What data supports your thesis?
   - What primary research do you have?
   - What would strengthen the case?

4. VALUATION APPROACH
   - What methods will you use?
   - What are the key assumptions?
   - What's the sensitivity on key drivers?

5. RISKS AND KILL CONDITIONS
   - What could go wrong?
   - What would change your mind?

6. CATALYST AND TIMING
   - What unlocks value?
   - When?
```

### Stage 2: Evidence Fill

For each evidence claim:
1. State the claim
2. Cite the source (filing, call, check)
3. Quantify where possible
4. Note confidence level

**Evidence quality hierarchy:**
```
BEST:   Primary research + quantified
GOOD:   Primary research OR public filing + quantified
OK:     Public filing, not quantified
WEAK:   Third-party source, not quantified
AVOID:  Assertion without source
```

### Stage 3: Valuation Section

**Minimum requirements:**
- Current trading level (price, multiple)
- Historical context (vs. own history)
- Target with explicit assumptions
- At least one sensitivity

**Template:**
```
Currently trading at $X / Y.Zx EV/EBITDA.

Historical average: A.Bx (range: C.Dx - E.Fx)
Peers trade at: G.Hx

Our target: $XX, based on:
- [Assumption 1]
- [Assumption 2]
- [Assumption 3]

Implies Ix EV/EBITDA, vs. J.Kx today.

Sensitivity: If [key driver] is X% better/worse,
target moves to $YY/$ZZ.
```

### Stage 4: Risk Section

**Structure each risk as:**
```
Risk: [Specific statement]
Impact: [What happens if risk materializes]
Probability: [High/Medium/Low or qualitative assessment]
Mitigant: [Why risk is acceptable or what monitors it]
Kill condition: [At what point does this invalidate thesis?]
```

**Avoid:**
- Generic risks (competition, macro, execution)
- Risks without impact assessment
- Risks without mitigants or acceptance rationale

### Stage 5: Decision Section

**Required elements:**
```
Recommendation: [Long/Short]
Target price: $XX (XX% upside/downside)
Time horizon: [Months/years]
Conviction: [High/Medium/Low or 1-5 scale]
Catalyst: [Event] by [Date]
Exit criteria: [Price-based] or [Event-based]
```

---

## Self-Critique Pass

After completing draft, score yourself on each rubric dimension:

### Checklist
- [ ] **Variant view**: Is it in the first paragraph? Is it proven?
- [ ] **Evidence**: Did I cite sources? Do I have primary research?
- [ ] **Valuation**: Are assumptions explicit? Did I show sensitivity?
- [ ] **Risks**: Are they specific? Did I define kill conditions?
- [ ] **Decision**: Can a PM act on this? Do they know when to exit?

### Red Flags to Catch
- Any paragraph without a specific data point
- Valuation section without assumptions stated
- Risk section with generic risks only
- No catalyst or vague timing
- Ending without clear recommendation

---

## Red Team Pass

Before finalizing, attack your own thesis:

### Bear Case Construction
1. What would a short seller say?
2. What's the strongest counter-argument?
3. What data would disprove your thesis?
4. Have you addressed the bear case in your memo?

### Questions to Answer
- Why hasn't the market figured this out?
- What do smart people on the other side believe?
- What would make me wrong?
- How would I know if I'm wrong?

### Evidence Challenge
For each key claim:
- What's the alternative explanation?
- Could this data be misleading?
- What would confirm/deny this?

---

## Anti-Pattern List

### Anti-Pattern 1: Burying the Thesis
**Bad:** Three paragraphs of background before stating the thesis.
**Good:** Thesis in sentence one.

### Anti-Pattern 2: Variant View Without Proof
**Bad:** "The market doesn't understand the company."
**Good:** "The market values this as a declining retailer, missing that same-store-sales turned positive in Q2 and the new loyalty program drives 15% higher ticket."

### Anti-Pattern 3: Generic Risks
**Bad:** "Competition could increase."
**Good:** "If Amazon enters this category (probability: Medium given [X]), margins could compress from 15% to 10%, reducing target to $X. Monitor Amazon's category page monthly."

### Anti-Pattern 4: Valuation Without Context
**Bad:** "Trades at 8x EBITDA, which is cheap."
**Good:** "Trades at 8x EBITDA vs. 10-year average of 11x and peers at 12x. Discount reflects market concern about [X], which our diligence suggests is [Y]."

### Anti-Pattern 5: No Catalyst
**Bad:** "Eventually the market will recognize the value."
**Good:** "Q3 earnings (Nov 14) will show 20%+ same-store growth, forcing Street to raise estimates."

### Anti-Pattern 6: Confidence Theater
**Bad:** "This is a slam dunk / no-brainer / can't lose."
**Good:** "High conviction based on [X], [Y], [Z]. Primary risk is [W]. Kill condition: exit if [V]."

### Anti-Pattern 7: Missing Exit Criteria
**Bad:** [Memo ends with target price]
**Good:** "Target $X within 12 months. Exit if: (1) price reaches $X, (2) catalyst doesn't materialize by Q2, or (3) [kill condition] occurs."

### Anti-Pattern 8: Ignoring the Bear Case
**Bad:** [No mention of what could go wrong]
**Good:** "Bears argue [X]. We disagree because [Y]. If bears are right, downside is [Z]."

---

## Minimum Viable Memo vs. Elite Memo

### Minimum Viable Memo (Score 6-7)

**Length:** 800-1,500 words
**Structure:**
1. Thesis with variant view (proven)
2. Business description (brief)
3. Investment merits (3-5 bullets with data)
4. Valuation (current vs. target with assumptions)
5. Catalyst (with timing)
6. Risks (specific, with kill conditions)
7. Recommendation

**Evidence:** At least SEC filings + one primary source or quantified analysis

### Elite Memo (Score 8+)

Everything in MVM, plus:
- Multiple primary research sources
- Sensitivity analysis on key drivers
- Bull/base/bear scenarios
- Anticipated counter-arguments addressed
- Clear position sizing guidance
- Monitoring framework (what to watch)
- Exit criteria (price and event-based)

**Length:** 1,500-3,000 words (substance-dense)

---

## Templates

### Quick Template (MVM)

```markdown
# [COMPANY] ([TICKER]) - [Long/Short]

## Summary
[One paragraph: Thesis, variant view, target, catalyst]

## Why Now
[What the market is missing and why]

## Business
[Brief description - 2-3 sentences]

## Investment Case
- [Merit 1 with data]
- [Merit 2 with data]
- [Merit 3 with data]

## Valuation
[Current multiple, historical, target with assumptions]

## Catalyst
[Event with timing]

## Risks
- [Risk 1]: [Impact]. Kill condition: [X].
- [Risk 2]: [Impact]. Kill condition: [Y].

## Recommendation
[Direction, target, conviction, timeline, exit criteria]
```

### Detailed Template (Elite)

```markdown
# [COMPANY] ([TICKER]) - [Long/Short] - [Target $X / X% Return]

## Executive Summary
[3-4 sentences: Thesis, variant view, catalyst, timing, conviction]

## Variant Perception
What market believes: [X]
What we believe: [Y]
Why we're right: [Evidence summary]

## Business Overview
[Description, segments, competitive position]

## Investment Thesis

### Point 1: [Thesis pillar]
[Supporting evidence with sources]

### Point 2: [Thesis pillar]
[Supporting evidence with sources]

### Point 3: [Thesis pillar]
[Supporting evidence with sources]

## Valuation

### Current Situation
[Price, multiple, market cap, context]

### Our View
[Target price derivation]
| Case | Assumption | Target |
|------|------------|--------|
| Bear | [X] | $XX |
| Base | [Y] | $YY |
| Bull | [Z] | $ZZ |

### Sensitivity
[Key driver impact on target]

## Catalyst Path
| Date | Event | Impact |
|------|-------|--------|
| [Q/Date] | [Event] | [Expected outcome] |

## Risks and Mitigants
| Risk | Probability | Impact | Mitigant | Kill Condition |
|------|-------------|--------|----------|----------------|
| [R1] | [P] | [I] | [M] | [K] |

## Recommendation
- Direction: [Long/Short]
- Target: $XX (XX% upside)
- Conviction: [High/Medium/Low]
- Time horizon: [X months/years]
- Position size: [Starter/Core/Full]
- Exit criteria: [Price and/or event]

## Monitoring
- Watch for: [Key metrics/events]
- Reassess if: [Trigger]
```
