# Memo Taxonomy - Buyside Memo Engine v0.1.0

## Overview

Investment memos fall into distinct categories, each requiring different structures, evidence standards, and risk frameworks. This taxonomy defines 6 core categories with templates.

---

## Category 1: Deep Value / Asset Play

### When to Use
- Stock trades below liquidation value or replacement cost
- Significant discount to book value or NAV
- Market ignores or misvalues balance sheet assets
- "Cigar butt" or margin-of-safety focused thesis

### Required Sections
1. **Asset Valuation** - What are the assets worth? (real estate, inventory, receivables, cash, IP)
2. **Discount Calculation** - Current price vs. asset value, with methodology
3. **Catalyst for Value Recognition** - Why will the gap close?
4. **Downside Protection** - What's the floor?
5. **Risks to Asset Values** - Impairment scenarios

### Decision Readiness Checklist
- [ ] Asset values independently verifiable (not management estimates)
- [ ] Discount exceeds 30% to provide margin of safety
- [ ] At least one catalyst identified within 12 months
- [ ] Liquidation scenario analyzed (what do you get?)
- [ ] Management alignment addressed (are they liquidating or empire-building?)

### Common Traps
- **Trap**: Relying on book value without assessing asset quality
- **Elite approach**: Independent valuation of each asset class
- **Trap**: Ignoring cash burn that erodes asset base
- **Elite approach**: Calculate months of runway and value destruction rate
- **Trap**: No catalyst = value trap
- **Elite approach**: Name specific event that forces value recognition

### Template Skeleton
```
# [COMPANY] - Deep Value at [X]% Discount to [NAV/Liquidation/Book]

## Summary
Trading at $X vs. conservative asset value of $Y (Z% discount).

## Asset Breakdown
| Asset | Book Value | Estimated Fair Value | Basis |
|-------|------------|---------------------|-------|
| Cash  | $XX        | $XX                 | 1:1   |
| ...   | ...        | ...                 | ...   |

## Discount Analysis
[Why is market wrong? What are they missing?]

## Catalyst
[What unlocks value? When?]

## Downside
[What's the floor? Liquidation scenario?]

## Risks
[What impairs the assets?]
```

---

## Category 2: Turnaround / Special Situation

### When to Use
- Company undergoing operational restructuring
- Post-bankruptcy or distressed situation
- New management or activist involvement
- Spin-off, merger arbitrage, or corporate event

### Required Sections
1. **Situation Overview** - What happened? Why is company distressed?
2. **Turnaround Thesis** - What's changing?
3. **Management Assessment** - Who's driving change? Track record?
4. **Normalized Earnings Power** - What does the business earn when fixed?
5. **Catalyst Timeline** - Event sequence and timing
6. **Kill Conditions** - What proves the thesis wrong?

### Decision Readiness Checklist
- [ ] Root cause of distress identified and addressable
- [ ] New management/strategy in place with track record
- [ ] Normalized earnings estimate with assumptions explicit
- [ ] Timeline of events with measurable milestones
- [ ] Defined exit: what price or event triggers sale
- [ ] Liquidity/solvency risk assessed

### Common Traps
- **Trap**: Assuming turnaround success because stock is down
- **Elite approach**: Identify specific operational changes and verify progress
- **Trap**: Ignoring balance sheet risk during turnaround period
- **Elite approach**: Model cash burn and debt maturities explicitly
- **Trap**: Trusting management promises without verification
- **Elite approach**: Channel checks and competitor commentary

### Template Skeleton
```
# [COMPANY] - Turnaround: [One-line thesis]

## What Went Wrong
[Explain the distress - be specific]

## What's Changing
[New management? Strategy shift? Cost cuts?]

## Normalized Economics
| Metric | Current | Normalized | Basis |
|--------|---------|------------|-------|
| Revenue | $X | $Y | [assumption] |
| Margins | X% | Y% | [assumption] |
| EPS | $X | $Y | [assumption] |

## Event Timeline
| Date | Event | Significance |
|------|-------|--------------|
| Q1 | ... | ... |

## Kill Conditions
- If [X happens], thesis is wrong → exit
- If [Y doesn't happen by Z], thesis is wrong → exit

## Valuation
[Multiple on normalized earnings]
```

---

## Category 3: Compounder / Quality Growth

### When to Use
- High-quality business with durable competitive advantage
- Strong reinvestment runway at attractive returns
- Management with proven capital allocation
- Long-term holding candidate

### Required Sections
1. **Business Quality Assessment** - Moat, ROIC, market position
2. **Growth Drivers** - What sustains growth?
3. **Reinvestment Opportunity** - Can they deploy capital at high returns?
4. **Management Quality** - Capital allocation track record
5. **Valuation Reasonableness** - Not necessarily cheap, but not expensive
6. **Long-term Ownership Case** - Why hold for years?

### Decision Readiness Checklist
- [ ] ROIC consistently above cost of capital (5+ year history)
- [ ] Competitive moat articulated and tested
- [ ] TAM and growth runway quantified
- [ ] Management incentives aligned with shareholders
- [ ] Valuation acceptable for long-term hold (not heroic assumptions)
- [ ] Business quality would survive management departure

### Common Traps
- **Trap**: Overpaying for quality (valuation still matters)
- **Elite approach**: Define max entry price, be patient
- **Trap**: Confusing cyclical upturn with structural growth
- **Elite approach**: Analyze through-cycle economics
- **Trap**: Ignoring competitive threats because "moat"
- **Elite approach**: Red-team the moat annually

### Template Skeleton
```
# [COMPANY] - Compounder at [X]% IRR

## Business Quality
[What makes this special? Why sustainable?]

## Competitive Advantage
[Moat type: network effects, switching costs, brand, scale, etc.]
[Evidence moat is real and durable]

## Growth Drivers
1. [Driver 1] - X% contribution
2. [Driver 2] - Y% contribution

## Capital Allocation
[How does management deploy capital? Track record?]

## Valuation
[Current multiple vs. history vs. growth rate]
[Long-term IRR calculation]

## Risks
[What degrades the moat?]
```

---

## Category 4: Short - Fraud / Accounting Issues

### When to Use
- Suspected financial statement manipulation
- Revenue recognition issues
- Related party transactions
- Auditor red flags

### Required Sections
1. **Fraud Indicators** - Specific accounting anomalies
2. **Evidence Compilation** - Documents, data, channel checks
3. **Management Red Flags** - Background, incentives, history
4. **Catalyst for Exposure** - What reveals the fraud?
5. **Timing and Position Sizing** - Shorts can be expensive to hold
6. **Borrow Availability and Cost**

### Decision Readiness Checklist
- [ ] Multiple independent fraud indicators (not just one anomaly)
- [ ] Primary research beyond public filings
- [ ] Management background checks completed
- [ ] Catalyst identified (audit, SEC inquiry, journalist, etc.)
- [ ] Borrow available and cost acceptable
- [ ] Position sized for potentially long wait

### Common Traps
- **Trap**: Shorting on valuation alone
- **Elite approach**: Focus on business/accounting issues, not multiple
- **Trap**: Underestimating how long fraud can persist
- **Elite approach**: Size position for multi-year hold
- **Trap**: Publishing before completing diligence
- **Elite approach**: Build full evidence file first

---

## Category 5: Short - Overearning / Peak Cycle

### When to Use
- Earnings above sustainable level due to cycle
- One-time benefits masking structural issues
- Industry peak that market treats as permanent
- Competitive threats not reflected in estimates

### Required Sections
1. **Normalized Earnings Analysis** - What are sustainable earnings?
2. **Peak Indicators** - Evidence we're at cycle top
3. **Competitive Dynamics** - What pressures earnings?
4. **Street Expectations** - What's priced in?
5. **Catalyst for Earnings Miss** - When does reality hit?

### Decision Readiness Checklist
- [ ] Historical earnings range analyzed (10+ years if available)
- [ ] Current margins vs. historical and competitor margins
- [ ] Industry capacity/demand analysis
- [ ] Competitor behavior and pricing trends
- [ ] Estimate revision catalyst identified
- [ ] Position sized for volatility

---

## Category 6: Short - Structural Decline

### When to Use
- Industry in secular decline
- Technology disruption affecting business model
- Regulatory headwinds
- Consumer preference shifts

### Required Sections
1. **Structural Thesis** - What's permanently broken?
2. **Rate of Decline** - How fast is deterioration?
3. **Management Response** - Are they adapting or denying?
4. **Street Optimism** - Why is market wrong?
5. **Catalyst** - What accelerates recognition?
6. **Timing Risk** - Decline can be slow

### Decision Readiness Checklist
- [ ] Secular trend identified with data (not just assertion)
- [ ] Decline rate quantified
- [ ] Management strategy assessed (pivoting or fighting tide?)
- [ ] Valuation implies growth that won't materialize
- [ ] Patience budgeted (structural shorts can take years)

---

## Cross-Category Requirements

All memo types must include:

1. **Variant View Statement** - What does the market believe? Why are they wrong?
2. **Evidence Specificity** - No claims without supporting data
3. **Valuation with Assumptions** - Show your work
4. **Risk Section with Kill Conditions** - What would change your mind?
5. **Position Sizing Guidance** - Conviction level and portfolio fit

---

## Decision Readiness Universal Checklist

Before finalizing any memo:

- [ ] Thesis stated in first paragraph
- [ ] Variant view articulated and proven (not just asserted)
- [ ] Valuation includes explicit assumptions and sensitivity
- [ ] At least one catalyst with timing
- [ ] Risks include specific kill conditions
- [ ] Author conviction level stated
- [ ] Exit criteria defined (price, time, or event)
