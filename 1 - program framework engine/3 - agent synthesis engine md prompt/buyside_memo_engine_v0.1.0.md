# Buyside Memo Engine - Instruction Manual v0.1.0

---

## A) Run Metadata

| Field | Value |
|-------|-------|
| **Timestamp** | 2026-01-15T17:45:00 (local) |
| **Run ID** | BME-v0.1.0-20260115 |
| **Output Version** | v0.1.0 (baseline) |
| **Folder Scanned** | `/Users/chaukam/Developer/Analyst_framework_buildout/data/structured/` |
| **Previous Version Found** | None (this is v0.1.0 baseline) |

### Files Analyzed

| Metric | Value |
|--------|-------|
| Total structured files in folder | 1,244 |
| Files with rich content (>500 chars) | 20 |
| Files read in detail | 6 |
| Total data size | 1.06 MB |

**Full file list:** See `sampling_report.md`

### Sampling Plan Used

Due to limited data (extraction in progress toward 17,160 target):
- Analyzed all 20 memos with rich content
- Deep-read 6 memos for contrastive analysis
- Stratified by: score (3.2-7.0), date (2000-2023), word count (327-4,213)

**Limitations:**
- No short positions in current sample
- Alphabetical bias (companies starting with numbers/A-B)
- Score distribution skewed toward 4-6 range

---

## B) Diff vs Latest Version

**No prior version found. This is v0.1.0 baseline.**

All components are new:
- Schema: Initial definition
- Taxonomy: 6 memo categories established
- Rubric: 5 dimensions defined
- Feature extraction: 6 features specified
- Playbook: Initial templates and anti-patterns
- Validation plan: Framework established
- Latent quality module: 12 hypotheses seeded

---

## C) 10 Defining Traits of Elite Buyside Memos

1. **(NEW)** **First-paragraph thesis clarity**: Elite memos state the core thesis, target, and variant view within the first 3 sentences. Score 8+ memos: 100% compliance. Score <5 memos: <50% compliance.

2. **(NEW)** **Variant view is proven, not asserted**: Elite memos explain *why* the market is wrong with specific evidence. Weak memos say "undervalued" without explaining their edge.

3. **(NEW)** **Primary research citation**: Elite memos cite channel checks, management calls, or industry experts. Weak memos rely solely on SEC filings.

4. **(NEW)** **Quantified evidence**: Elite memos use specific numbers (margins, revenue breakdown, unit economics). Weak memos use vague qualitative claims ("strong brand").

5. **(NEW)** **Explicit valuation assumptions**: Elite memos show their work—assumptions are stated, not hidden. Readers can stress-test the logic.

6. **(NEW)** **Sensitivity analysis**: Elite memos show bull/base/bear or key driver sensitivity. Weak memos give single-point targets.

7. **(NEW)** **Specific risks with kill conditions**: Elite memos define "if X happens, thesis is wrong—exit." Weak memos list generic risks ("competition could increase").

8. **(NEW)** **Catalyst with timing**: Elite memos identify specific events with dates. Weak memos hope for "eventual market recognition."

9. **(NEW)** **Decision-ready conclusions**: Elite memos end with actionable guidance—target, conviction, sizing, exit criteria. Weak memos end with "this is interesting."

10. **(NEW)** **Author engagement and updates**: Elite memo authors respond to comments, update with new information, and acknowledge when wrong. Weak memo authors disappear when challenged.

---

## D) Deliverables

### D1) Data Schema

**File:** `schema.json`

Key fields beyond basic metadata:
- `thesis_type`: Classified memo category (model-assisted)
- `catalysts[]`: Structured with type, timing, measurability
- `risk_factors[]`: With kill condition flags
- `evidence_types[]`: Primary vs secondary classification
- `has_variant_view`: Boolean
- `variant_view_proven`: Whether evidence supports the claim
- `has_exit_criteria`: Decision readiness indicator

**Extraction notes:** Regex + keyword for most fields; LLM classification for thesis_type and variant_view_proven.

---

### D2) Memo Taxonomy

**File:** `taxonomy.md`

6 categories defined:

| Category | When to Use |
|----------|-------------|
| **Deep Value / Asset Play** | Stock below liquidation value, balance sheet focus |
| **Turnaround / Special Situation** | Restructuring, post-bankruptcy, activist, event |
| **Compounder / Quality Growth** | Durable moat, reinvestment runway, long-term hold |
| **Short - Fraud** | Accounting manipulation, related party issues |
| **Short - Overearning** | Peak cycle, unsustainable margins |
| **Short - Structural Decline** | Secular headwinds, disruption |

Each category includes: required sections, decision checklist, common traps.

---

### D3) Scoring Rubric

**File:** `rubric.md`

5 dimensions (weights in parentheses):

| Dimension | Weight | What It Measures |
|-----------|--------|------------------|
| **Variant View Clarity** | 25% | Is the edge articulated and proven? |
| **Evidence Quality** | 25% | Primary vs secondary, specific vs vague |
| **Valuation Rigor** | 20% | Method, assumptions, sensitivity |
| **Risk Honesty** | 15% | Specific risks with kill conditions |
| **Decision Readiness** | 15% | Actionable: sizing, timing, exit |

**Scoring function:** Weighted average with tie-breakers favoring variant view.

**Bias handling:** Score on memo quality at time of writing, not subsequent performance.

---

### D4) Feature Extraction Plan

**File:** `feature_extraction.md`

6 features with operational definitions:

| Feature | Detection Method |
|---------|------------------|
| Variant view | Keywords + LLM classification |
| Evidence specificity | Primary/secondary keyword hierarchy |
| Valuation methods | Regex for EV/EBITDA, P/E, DCF, etc. |
| Kill conditions | Pattern matching for exit triggers |
| Catalyst timing | Date/quarter pattern extraction |
| Decision readiness | Checklist of required elements |

**Gold labeling strategy:** 20-30 manually labeled examples for calibration.

---

### D5) Writing Playbook

**File:** `playbook.md`

Contents:
- **Core principles**: Lead with edge, prove don't assert, show work, define failure, enable action
- **Drafting workflow**: Outline → Evidence fill → Valuation → Risks → Decision
- **Self-critique pass**: Rubric-based checklist
- **Red team pass**: Attack your own thesis
- **Anti-patterns**: 8 common mistakes with corrections
- **Templates**: Minimum viable memo (800-1,500 words) and elite memo (1,500-3,000 words)

---

### D6) Validation Plan

**File:** `validation.md`

Methods:
- **Blind evaluation**: Strip source labels, score on rubric
- **Pairwise ranking**: A/B preference, target 60%+ AI win rate
- **Holdout sets**: Time-based (pre-2021 train, post-2021 test) and author-based

Bias handling:
- Date stratification (percentile within year)
- Vote-weighting
- Author normalization
- Era calibration

Success metrics:
- Rubric score uplift ≥ 0
- Pairwise win rate ≥ 50%
- Hallucination rate ≤ 5%
- Decision readiness ≥ 90%

---

### D7) Roadmap

**File:** `roadmap.md`

| Sprint | Weeks | Focus |
|--------|-------|-------|
| 1 | 1-2 | Data pipeline, sampling, baseline analysis |
| 2 | 3-4 | Taxonomy, rubric, feature extraction |
| 3 | 5-6 | Playbook, templates, contrastive validation |
| 4 | 7-8 | Validation harness, bias handling, baseline benchmark |
| 5 | 9-10 | Self-upgrade loop, hypothesis testing, first promotions |
| 6 | 11-12 | Scale to 5,000+ memos, refine, publish v1.1 |

---

## E) Latent Quality Discovery Module

**File:** `latent_quality_module.md`

### Hypothesis Bank Schema
```json
{
  "hypothesis_id": "HYP-001",
  "name": "Falsification Framing",
  "status": "experimental|watchlist|core|rejected",
  "evidence": {
    "predictive_correlation": null,
    "pairwise_accuracy": null,
    "ablation_result": null
  },
  "promotion_threshold": {
    "predictive_r": 0.30,
    "pairwise_accuracy": 0.65
  }
}
```

### Promotion Criteria
- **Predictive:** r ≥ 0.30 after controlling for length/date/author
- **Pairwise:** ≥ 65% accuracy in blind ranking
- **Ablation:** Mean degradation > 0.5 points when feature removed

### Changelog Discipline
- **X.0.0 (Major):** Schema or taxonomy overhaul
- **X.Y.0 (Minor):** Latent quality promoted to core
- **X.Y.Z (Patch):** Bug fix, wording improvement

### Overfitting Guardrails
- Control for length, date, author in all tests
- Require pairwise confirmation (not just correlation)
- Test on non-VIC samples when available
- Audit for copied VIC phrasing

### Current State (v0.1.0)
- **Core:** First-paragraph thesis, Evidence quantification
- **Testing queue:** Falsification framing, Primary research, Catalyst timing, Exit criteria
- **Watchlist:** Author engagement, Position sizing, Management assessment

---

## F) Pitfalls & Compliance

### F1) ToS / IP Constraints

- **Do not copy text:** Extract patterns, structures, and rules only
- **No verbatim reproduction:** Distinctive VIC phrasing must not appear in output
- **Respect access:** Memos are member-only content; do not redistribute

### F2) Outcome Bias

- **Problem:** High VIC scores may reflect stock performance, not memo quality
- **Mitigation:** Use date stratification, era calibration, focus on quality at time of writing

### F3) Survivorship Bias

- **Problem:** We only see memos that were posted, not ideas that were rejected
- **Mitigation:** Acknowledge this limitation; don't claim completeness

### F4) Author Effects

- **Problem:** "Celebrity" authors get high scores regardless of memo quality
- **Mitigation:** Author normalization, test features across author subgroups

### F5) Overfitting to Rhetorical Style

- **Problem:** Confusing polished writing with analytical substance
- **Mitigation:** Rubric penalizes "confidence theater," rewards evidence specificity

### F6) Data Leakage

- **Problem:** Using comments/updates that reveal post-hoc information
- **Mitigation:** Primary scoring based on original memo only; comments analyzed separately

### F7) Memorization Risk

- **Problem:** AI reproduces VIC phrasing instead of learning patterns
- **Mitigation:** Grep output for distinctive phrases; test on non-VIC companies; regular audit

---

## Supporting Files

| File | Purpose |
|------|---------|
| `sampling_report.md` | Detailed file list and sampling methodology |
| `schema.json` | Data schema specification |
| `taxonomy.md` | Memo type taxonomy with templates |
| `rubric.md` | Scoring rubric with anchors |
| `feature_extraction.md` | Feature detection methods |
| `playbook.md` | Writing guidance and templates |
| `validation.md` | Evaluation methodology |
| `roadmap.md` | Implementation timeline |
| `latent_quality_module.md` | Self-upgrade mechanism |
| `PDF_LAYOUT_NOTES.md` | PDF rendering instructions |

---

## PDF Layout Notes

**File:** `PDF_LAYOUT_NOTES.md`

For PDF rendering:
- Page size: Letter (8.5" x 11")
- Margins: 1" all sides
- Font: 11pt for body, 14pt for H1, 12pt for H2
- Code blocks: 10pt monospace
- Page breaks: Before each major section (A-F)
- Header: "Buyside Memo Engine v0.1.0" on all pages
- Footer: Page numbers centered

---

*Generated by Buyside Memo Engine v0.1.0*
*Run ID: BME-v0.1.0-20260115*
