# Roadmap - Buyside Memo Engine v0.1.0

## Overview

This roadmap defines deliverables in 2-week increments, prioritized for speed and iteration.

---

## Sprint 1: Foundation (Weeks 1-2)

### Goal
Establish data pipeline and baseline analysis.

### Deliverables
1. **Data extraction pipeline**
   - [ ] Complete structured JSON extraction for all available memos
   - [ ] Validate schema compliance
   - [ ] Document extraction coverage (which fields populated)

2. **Sampling framework**
   - [ ] Implement stratified sampling by score, date, position type
   - [ ] Create reproducible sample for analysis
   - [ ] Document sample characteristics

3. **Baseline analysis**
   - [ ] Read 50+ rich memos manually
   - [ ] Initial pattern identification
   - [ ] Draft hypothesis bank (10+ candidates)

### Exit Criteria
- ≥500 memos with full content extracted
- Sampling framework tested and documented
- Initial hypothesis bank with 10+ candidate qualities

---

## Sprint 2: Core Framework (Weeks 3-4)

### Goal
Build taxonomy, rubric, and feature extraction foundation.

### Deliverables
1. **Memo taxonomy finalized**
   - [ ] 4+ categories defined with examples
   - [ ] Templates for each category
   - [ ] Decision readiness checklists

2. **Rubric v1.0**
   - [ ] 5 dimensions defined with anchors
   - [ ] Scoring function implemented
   - [ ] Gold-labeled calibration set (20 memos)

3. **Feature extraction v1.0**
   - [ ] Regex heuristics for all 6 features
   - [ ] Keyword counting implemented
   - [ ] Test on sample, document accuracy

### Exit Criteria
- Taxonomy covers ≥90% of sample memos
- Rubric inter-rater kappa ≥0.6 on calibration set
- Feature extraction runs on full dataset

---

## Sprint 3: Playbook and Templates (Weeks 5-6)

### Goal
Create usable writing guidance and validate against sample.

### Deliverables
1. **Playbook v1.0**
   - [ ] Drafting workflow documented
   - [ ] Anti-pattern list with examples
   - [ ] Self-critique checklist

2. **Templates**
   - [ ] Minimum viable memo template
   - [ ] Elite memo template
   - [ ] Category-specific templates

3. **Contrastive validation**
   - [ ] Score 20 memos using rubric
   - [ ] Compare rubric scores to VIC scores
   - [ ] Identify systematic gaps

### Exit Criteria
- Playbook usable by analyst agent
- Templates produce rubric score ≥6 when filled correctly
- Rubric correlates positively with VIC scores (r>0.3)

---

## Sprint 4: Validation Harness (Weeks 7-8)

### Goal
Establish evaluation framework for continuous improvement.

### Deliverables
1. **Evaluation infrastructure**
   - [ ] Blind evaluation protocol documented
   - [ ] Pairwise comparison tool built
   - [ ] Holdout sets created (time and author based)

2. **Bias handling**
   - [ ] Date stratification implemented
   - [ ] Author normalization implemented
   - [ ] Era calibration tested

3. **Baseline benchmark**
   - [ ] Generate 10 AI memos using playbook
   - [ ] Evaluate against rubric
   - [ ] Document baseline scores

### Exit Criteria
- Evaluation can run end-to-end
- Bias-adjusted scores computed for full dataset
- Baseline AI memo scores documented

---

## Sprint 5: Self-Upgrade Loop (Weeks 9-10)

### Goal
Implement latent quality discovery and promotion mechanism.

### Deliverables
1. **Hypothesis bank infrastructure**
   - [ ] Schema implemented
   - [ ] CRUD operations working
   - [ ] Current hypotheses documented

2. **Evaluation harness for hypotheses**
   - [ ] Predictive correlation test
   - [ ] Pairwise accuracy test
   - [ ] Ablation test framework

3. **Promotion pipeline**
   - [ ] Threshold criteria defined
   - [ ] Promotion decision log started
   - [ ] First hypothesis evaluated

### Exit Criteria
- Hypothesis bank populated with ≥15 candidates
- At least 3 hypotheses tested with results documented
- Promotion criteria working and logged

---

## Sprint 6: Scale and Polish (Weeks 11-12)

### Goal
Expand data coverage and refine based on learnings.

### Deliverables
1. **Data expansion**
   - [ ] Target: 5,000+ memos with full content
   - [ ] Re-run analysis on expanded set
   - [ ] Update sampling to include more diversity

2. **Instruction refinement**
   - [ ] Incorporate sprint 4-5 learnings
   - [ ] Update playbook based on failure analysis
   - [ ] Version bump if significant changes

3. **Documentation**
   - [ ] Full manual assembled
   - [ ] PDF rendering tested
   - [ ] Changelog complete

### Exit Criteria
- ≥5,000 memos analyzed
- Playbook v1.1 released
- Full documentation published

---

## Future Sprints (Weeks 13+)

### Nice-to-Have Items

**Data quality:**
- Short thesis coverage (currently zero)
- Sector stratification
- Author expertise tagging

**Model enhancement:**
- LLM-assisted feature extraction
- Embedding-based memo clustering
- Automated rubric scoring

**Integration:**
- API for memo scoring
- Agent integration testing
- Feedback collection system

**Advanced analysis:**
- Performance correlation (controlling for selection bias)
- Author track record analysis
- Temporal trend analysis

---

## Dependencies and Risks

### Dependencies
| Item | Dependency | Mitigation |
|------|------------|------------|
| Data expansion | Download completion | Work with available sample, iterate |
| LLM classification | API access | Use regex heuristics as fallback |
| Evaluator availability | Human time | Start with self-evaluation, expand later |

### Risks
| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| Insufficient data variety | Medium | High | Prioritize extraction of diverse memos |
| VIC scores too noisy | Medium | Medium | Use bias-adjusted scores, triangulate |
| Playbook doesn't generalize | Low | High | Test on out-of-sample companies |
| Overfitting to VIC style | Medium | High | Explicit guardrails in hypothesis promotion |

---

## Success Criteria by Phase

| Phase | Timeline | Success Criteria |
|-------|----------|------------------|
| Foundation | Weeks 1-2 | Data pipeline working, 500+ memos |
| Core | Weeks 3-4 | Taxonomy + rubric usable |
| Playbook | Weeks 5-6 | AI can generate score ≥6 memos |
| Validation | Weeks 7-8 | Evaluation infrastructure complete |
| Self-Upgrade | Weeks 9-10 | First hypothesis promoted or rejected |
| Scale | Weeks 11-12 | v1.1 released with expanded data |
