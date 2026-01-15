# Validation Plan - Buyside Memo Engine v0.1.0

## Overview

This document defines how to test whether the Buyside Memo Engine produces better analyst output and how to handle biases in VIC scores.

---

## Part 1: Evaluation Design

### 1.1 Blind Evaluation

**Setup:**
1. Generate AI memos using the engine
2. Sample human-written VIC memos
3. Strip identifying information (dates, specific VIC formatting)
4. Present pairs to evaluators without source labels

**Evaluator Instructions:**
```
You will see two investment memos on the same company or thesis type.
Rate each on a 1-10 scale using the provided rubric.
Do not consider which memo is AI-generated or human-written.
Focus only on memo quality as a decision document.
```

**Metrics:**
- Mean rubric score per memo source (AI vs. human)
- Score distribution comparison
- Inter-rater reliability (Cohen's kappa)

### 1.2 Pairwise Ranking (A/B Comparison)

**Setup:**
1. Present evaluators with two memos (AI and human) side by side
2. Ask: "Which memo would you rather receive before making an investment decision?"
3. Force a choice (no ties)

**Metrics:**
- Win rate: % of comparisons where AI memo preferred
- Target: AI win rate ≥ 50% initially, ≥ 60% after iteration

**Sample Size:**
- Minimum 50 pairwise comparisons
- Power analysis: 50 pairs detects 15% win rate difference at p<0.05

### 1.3 Holdout Sets

**Time-Based Split:**
- Training: Memos from 2000-2020
- Validation: Memos from 2021-2023
- Prevents temporal leakage (market conditions, writing norms evolve)

**Author-Based Split:**
- Training: 80% of authors
- Validation: 20% of authors (never seen)
- Prevents author-style overfitting

**Implementation:**
```python
def create_holdout(memos, split_type='time', val_fraction=0.2):
    if split_type == 'time':
        cutoff_year = 2021
        train = [m for m in memos if parse_year(m['date']) < cutoff_year]
        val = [m for m in memos if parse_year(m['date']) >= cutoff_year]
    elif split_type == 'author':
        authors = list(set(m['author'] for m in memos))
        val_authors = random.sample(authors, int(len(authors) * val_fraction))
        train = [m for m in memos if m['author'] not in val_authors]
        val = [m for m in memos if m['author'] in val_authors]
    return train, val
```

---

## Part 2: Handling Outcome Bias

### 2.1 The Problem

VIC scores conflate:
- Memo quality (what we want to measure)
- Perceived edge (varies by scorer knowledge)
- Outcome bias (scores influenced by stock performance after posting)

### 2.2 Date Stratification

**Approach:** Compare memos within the same time period only.

**Why:** Older memos have had more time to "prove out," potentially inflating scores of ideas that worked. Newer memos scored on quality alone.

**Implementation:**
- Bucket memos by year posted
- Calculate percentile rank within each bucket
- Compare percentile ranks, not raw scores

```python
def percentile_within_period(memo, all_memos):
    period = get_year(memo['date'])
    period_memos = [m for m in all_memos if get_year(m['date']) == period]
    period_scores = sorted([m['quality_score'] for m in period_memos if m['quality_score']])
    return percentile(memo['quality_score'], period_scores)
```

### 2.3 Vote-Weighting

**Problem:** Some memos have 5 votes, others have 50. More votes = more reliable signal.

**Approach:** Weight by vote count in aggregations.

```python
def weighted_mean_score(memos):
    total_votes = sum(m['quality_votes'] for m in memos if m['quality_votes'])
    weighted_sum = sum(m['quality_score'] * m['quality_votes']
                       for m in memos if m['quality_score'] and m['quality_votes'])
    return weighted_sum / total_votes if total_votes > 0 else None
```

### 2.4 Author Effects

**Problem:** Some authors are "celebrities" whose memos get high scores regardless of quality.

**Approach:**
1. Calculate author average score
2. Compute memo score relative to author average
3. Use relative score for analysis

```python
def author_adjusted_score(memo, author_memos):
    author_avg = mean([m['quality_score'] for m in author_memos if m['quality_score']])
    return memo['quality_score'] - author_avg
```

### 2.5 Score Calibration by Era

**Problem:** Scoring norms evolve. A "7" in 2005 may not equal a "7" in 2020.

**Approach:**
1. Calculate mean and std of scores by year
2. Z-score normalize within each year
3. Use normalized scores for comparison

```python
def era_normalized_score(memo, all_memos):
    year = get_year(memo['date'])
    year_scores = [m['quality_score'] for m in all_memos
                   if get_year(m['date']) == year and m['quality_score']]
    mu, sigma = mean(year_scores), std(year_scores)
    return (memo['quality_score'] - mu) / sigma if sigma > 0 else 0
```

---

## Part 3: Success Metrics

### 3.1 Primary Metrics

| Metric | Definition | Target |
|--------|------------|--------|
| **Rubric Score Uplift** | Mean AI memo score - Mean human memo score (on our rubric) | ≥ 0 initially, ≥ +1.0 after iteration |
| **Pairwise Win Rate** | % of A/B comparisons where AI preferred | ≥ 50% initially, ≥ 60% after iteration |
| **Inter-Rater Reliability** | Cohen's kappa across evaluators | ≥ 0.7 |

### 3.2 Secondary Metrics

| Metric | Definition | Target |
|--------|------------|--------|
| **Hallucination Rate** | % of AI memos with factually incorrect claims | ≤ 5% |
| **Decision Readiness** | % of AI memos with all required elements (target, catalyst, exit criteria) | ≥ 90% |
| **Variant View Clarity** | % of AI memos with proven (not just asserted) variant view | ≥ 80% |
| **Kill Condition Presence** | % of AI memos with explicit kill conditions | ≥ 90% |

### 3.3 Negative Metrics (Things to Avoid)

| Metric | Definition | Target |
|--------|------------|--------|
| **Phrase Memorization** | % of AI output with VIC-distinctive phrases | 0% |
| **Over-Length** | % of AI memos >3000 words without substance increase | ≤ 10% |
| **Generic Risk Rate** | % of AI memos with only generic risks | ≤ 10% |

---

## Part 4: Failure Analysis Loop

### 4.1 Error Taxonomy

When AI memos score poorly, classify the failure:

| Category | Description | Example |
|----------|-------------|---------|
| **Variant Failure** | Weak or missing variant view | "Stock is undervalued" without explanation |
| **Evidence Failure** | Vague claims, no sources | "Company has strong moat" |
| **Valuation Failure** | Missing assumptions or sensitivity | "Worth $50" with no derivation |
| **Risk Failure** | Generic risks, no kill conditions | "Competition could increase" |
| **Decision Failure** | Missing exit criteria or catalyst timing | "Buy" with no price or time |
| **Hallucination** | Factually incorrect claim | Wrong revenue number |

### 4.2 Root Cause Analysis

For each failure category:
1. Sample 10 failing memos
2. Identify common patterns
3. Trace to instruction/template gap
4. Update playbook or rubric

### 4.3 Feedback Loop

```
1. Generate AI memos
2. Evaluate against rubric
3. Identify failure categories
4. Analyze root causes
5. Update instructions/templates
6. Re-generate and re-evaluate
7. Track improvement over iterations
```

---

## Part 5: Evaluation Protocol

### 5.1 Evaluator Selection

**Criteria:**
- Investment experience (analyst, PM, or equivalent)
- Familiarity with memo format
- No conflict of interest

**Training:**
- Review rubric with examples
- Score 5 calibration memos together
- Discuss disagreements

### 5.2 Evaluation Session

**Per memo:**
1. Read full memo (no time limit)
2. Score each rubric dimension (1-10)
3. Note specific issues or strengths
4. Record overall impression

**Data collected:**
- Dimension scores (5 per memo)
- Overall score
- Qualitative comments
- Time spent

### 5.3 Statistical Analysis

**Tests:**
- Paired t-test for mean score comparison
- Binomial test for pairwise win rate
- Kappa for inter-rater reliability

**Reporting:**
- Mean ± std for each metric
- 95% confidence intervals
- Effect size (Cohen's d)

---

## Part 6: Iteration Cadence

### Weekly
- Generate sample AI memos
- Quick qualitative review
- Flag obvious issues

### Monthly
- Full evaluation round (10-20 memos)
- Update failure analysis
- Revise instructions if needed

### Quarterly
- Large-scale evaluation (50+ memos)
- Benchmark against baseline
- Version release decision
