# Latent Quality Discovery Module - Buyside Memo Engine v0.1.0

## Overview

This module implements explicit mechanisms to discover latent qualities of strong buyside memos and upgrade the instruction manual over time.

---

## Part 1: Hypothesis Bank

### 1.1 Schema

```json
{
  "hypothesis_id": "HYP-001",
  "name": "Falsification Framing",
  "category": "risk_articulation",
  "status": "experimental",
  "definition": "Memo explicitly states conditions under which the thesis would be proven wrong, not just risks that could occur.",
  "detection_cues": [
    "would exit if",
    "thesis is wrong if",
    "kill condition",
    "would change our mind if"
  ],
  "test_plan": {
    "predictive": "Correlate presence with VIC score (adjusted for date/author)",
    "pairwise": "Present two memos differing only in this feature, ask which is more decision-ready",
    "ablation": "Remove kill conditions from memo, evaluate quality degradation"
  },
  "evidence": {
    "predictive_correlation": null,
    "pairwise_accuracy": null,
    "ablation_result": null
  },
  "promotion_threshold": {
    "predictive_r": 0.3,
    "pairwise_accuracy": 0.65
  },
  "created_at": "2026-01-15T17:45:00",
  "last_tested": null,
  "promoted_at": null,
  "notes": "Initial hypothesis from contrastive analysis. High-score memos tend to have explicit exit criteria."
}
```

### 1.2 Initial Hypothesis Bank

| ID | Name | Category | Status | Basis |
|----|------|----------|--------|-------|
| HYP-001 | Falsification Framing | risk | experimental | High-score memos have kill conditions |
| HYP-002 | Primary Research Citation | evidence | experimental | Channel checks correlate with scores |
| HYP-003 | Quantified Variant View | variant | experimental | "X% mispriced" vs "undervalued" |
| HYP-004 | Scenario Analysis | valuation | experimental | Bull/base/bear vs single target |
| HYP-005 | Author Engagement | meta | watchlist | Follow-up comments correlate with score |
| HYP-006 | First-Paragraph Thesis | structure | core | Thesis in opening predicts quality |
| HYP-007 | Catalyst Timing Specificity | catalyst | experimental | "Q3" vs "eventually" |
| HYP-008 | Counter-Argument Handling | variant | experimental | Addressing bear case explicitly |
| HYP-009 | Position Sizing Mention | decision | watchlist | High-score memos discuss sizing |
| HYP-010 | Exit Criteria Definition | decision | experimental | "Sell at $X" vs no exit guidance |
| HYP-011 | Evidence Quantification | evidence | core | Numbers vs qualitative claims |
| HYP-012 | Management Assessment | diligence | watchlist | Background check on management |

### 1.3 Status Definitions

| Status | Definition |
|--------|------------|
| **experimental** | Hypothesis defined, not yet tested |
| **watchlist** | Tested but results inconclusive, needs more data |
| **core** | Passed promotion criteria, included in instruction |
| **rejected** | Tested and failed criteria, documented why |

---

## Part 2: Evaluation Harness

### 2.1 Predictive Correlation Test

**Goal:** Determine if feature presence correlates with memo quality.

**Method:**
1. Extract feature presence for all memos
2. Calculate correlation with quality score
3. Control for confounds (date, length, author)

**Implementation:**
```python
def predictive_test(hypothesis, memos):
    # Extract feature
    has_feature = [detect_feature(m, hypothesis) for m in memos]

    # Get scores (bias-adjusted)
    scores = [adjusted_score(m) for m in memos]

    # Control variables
    lengths = [m['word_count'] for m in memos]
    dates = [parse_year(m['date']) for m in memos]

    # Partial correlation controlling for length and date
    r = partial_correlation(has_feature, scores, [lengths, dates])

    return {
        'correlation': r,
        'passes': abs(r) >= hypothesis['promotion_threshold']['predictive_r']
    }
```

**Threshold:** r ≥ 0.30 (medium effect size) after controlling for length/date/author

### 2.2 Pairwise Accuracy Test

**Goal:** Can evaluators reliably identify better memo using this feature?

**Method:**
1. Select memo pairs that differ primarily on this feature
2. Present to evaluators (blind to hypothesis)
3. Ask which is more decision-ready
4. Calculate accuracy of hypothesis in predicting preference

**Implementation:**
```python
def pairwise_test(hypothesis, memo_pairs, evaluator_responses):
    # For each pair, hypothesis predicts memo with feature is better
    predictions = [pair[0] if has_feature(pair[0], hypothesis)
                   else pair[1] for pair in memo_pairs]

    # Compare to evaluator preferences
    correct = sum(1 for pred, resp in zip(predictions, evaluator_responses)
                  if pred == resp)

    accuracy = correct / len(memo_pairs)

    return {
        'accuracy': accuracy,
        'n_pairs': len(memo_pairs),
        'passes': accuracy >= hypothesis['promotion_threshold']['pairwise_accuracy']
    }
```

**Threshold:** ≥65% accuracy (significantly above chance)

### 2.3 Ablation Test

**Goal:** Does removing the feature degrade memo quality?

**Method:**
1. Take high-quality memos with the feature
2. Create ablated versions (feature removed)
3. Have evaluators score both versions (blind)
4. Compare scores

**Implementation:**
```python
def ablation_test(hypothesis, memos):
    results = []
    for memo in memos:
        if has_feature(memo, hypothesis):
            ablated = remove_feature(memo, hypothesis)
            original_score = evaluate(memo)
            ablated_score = evaluate(ablated)
            results.append({
                'original': original_score,
                'ablated': ablated_score,
                'degradation': original_score - ablated_score
            })

    mean_degradation = mean([r['degradation'] for r in results])

    return {
        'mean_degradation': mean_degradation,
        'n_tested': len(results),
        'passes': mean_degradation > 0.5  # At least 0.5 point drop
    }
```

**Threshold:** Mean degradation > 0.5 points on 10-point scale

---

## Part 3: Promotion Criteria

### 3.1 Promotion Decision Matrix

| Predictive | Pairwise | Ablation | Decision |
|------------|----------|----------|----------|
| Pass | Pass | Pass | **Promote to Core** |
| Pass | Pass | Fail | Promote (ablation optional) |
| Pass | Fail | Pass | **Watchlist**, needs more pairs |
| Fail | Pass | Pass | **Watchlist**, investigate correlation |
| Any 2 Fail | - | - | **Reject** |

### 3.2 Promotion Process

1. **Test sequentially:** Predictive → Pairwise → Ablation
2. **Document results:** All test results logged
3. **Review meeting:** Discuss borderline cases
4. **Update instruction:** Promoted hypotheses added to playbook
5. **Version bump:** Promotion triggers version increment

### 3.3 Rejection Criteria

A hypothesis is rejected if:
- Predictive r < 0.10 (no signal)
- Pairwise accuracy < 55% (near chance)
- Signal is confounded (disappears when controlling for length)

Rejected hypotheses are documented with reason and retained for future analysis.

---

## Part 4: Changelog Discipline

### 4.1 Version Numbering

**Format:** vX.Y.Z

| Bump | Trigger | Example |
|------|---------|---------|
| X.0.0 (Major) | Schema change, taxonomy overhaul | New memo category added |
| X.Y.0 (Minor) | Latent quality promoted to core | New feature in rubric |
| X.Y.Z (Patch) | Bug fix, wording improvement | Clarification in template |

### 4.2 Changelog Format

```markdown
## v0.2.0 - 2026-02-01

### Promoted to Core
- **HYP-007: Catalyst Timing Specificity**
  - Evidence: Predictive r=0.35, Pairwise 71%, Ablation -0.8 points
  - Added to: Rubric (Dimension 5), Playbook (Catalyst section), Template

### Watchlist Updates
- HYP-005: Author Engagement moved to watchlist (r=0.22, inconclusive)

### Rejected
- HYP-012: Management Assessment (r=0.08, no predictive signal)

### Other Changes
- Clarified valuation sensitivity requirements in playbook
- Fixed typo in taxonomy template
```

### 4.3 Evidence Requirements for Changelog

Every change must cite:
- Which test (predictive/pairwise/ablation)
- Sample size
- Result with threshold comparison
- Files/memos analyzed

---

## Part 5: Guardrails Against Overfitting

### 5.1 VIC House Style Risk

**Risk:** Promoting features that are VIC-specific, not generalizable to buyside memos.

**Guardrails:**
- Compare to non-VIC memo samples (when available)
- Exclude VIC-distinctive phrasing from feature definitions
- Review promoted features with external investors

### 5.2 Spurious Correlation Risk

**Risk:** Features that correlate with score due to confounds, not quality.

**Guardrails:**
- Always control for length in predictive tests
- Always control for date (era effects)
- Always control for author (celebrity effects)
- Require pairwise confirmation (not just correlation)

### 5.3 Memorization Risk

**Risk:** Engine reproduces VIC phrasing instead of learning patterns.

**Guardrails:**
- Grep output for distinctive VIC phrases
- Test: Can engine apply to non-VIC company?
- Regular audit of output for copied language

### 5.4 Overfitting to Top Authors

**Risk:** Learning style of top-scoring authors, not generalizable quality.

**Guardrails:**
- Test features across author subgroups
- Ensure feature works for low-frequency authors
- Don't use author as feature

---

## Part 6: Operational Workflow

### 6.1 Weekly Hypothesis Review

**Agenda:**
1. Review new contrastive observations
2. Formalize as hypotheses (or discard)
3. Prioritize next hypothesis for testing
4. Log decisions

### 6.2 Monthly Promotion Review

**Agenda:**
1. Review hypothesis test results
2. Make promotion/rejection/watchlist decisions
3. Update changelog
4. Update playbook if promotion occurred

### 6.3 Quarterly Audit

**Agenda:**
1. Review all promoted features for continued validity
2. Check for confound creep
3. Test on new data (if available)
4. Consider feature removal if no longer valid

---

## Part 7: Current State

### Promoted to Core (v0.1.0 baseline)
- HYP-006: First-Paragraph Thesis
- HYP-011: Evidence Quantification

### In Testing Queue
- HYP-001: Falsification Framing
- HYP-002: Primary Research Citation
- HYP-007: Catalyst Timing Specificity
- HYP-010: Exit Criteria Definition

### On Watchlist
- HYP-005: Author Engagement
- HYP-009: Position Sizing Mention
- HYP-012: Management Assessment

### Not Yet Tested
- HYP-003: Quantified Variant View
- HYP-004: Scenario Analysis
- HYP-008: Counter-Argument Handling
