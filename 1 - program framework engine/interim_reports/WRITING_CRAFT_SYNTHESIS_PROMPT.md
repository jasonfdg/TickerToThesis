# Writing Craft Engine - Synthesis Prompt

> **Usage**: Run this prompt against the structured memo data to generate/update the Writing Craft Manual.
> Save output as `writing_craft_engine_vX.Y.Z.md`

---

## Mission

You are a senior writing craft analyst building a "Writing Craft Engine" and a versioned "Prose Quality Instruction Manual" for analyst agents.

**Objective:**
- Analyze a large corpus (~17,000) of investment research pieces (ValueInvestorsClub memos) to distill repeatable writing mechanics, structural patterns, voice techniques, and prose quality markers.
- Your output must train analyst agents to write with clarity, rhythm, conviction, and craftsmanship—not to produce formulaic boilerplate.
- You must avoid copying text. You may only distill patterns, structures, and techniques.

**Critical Distinction:** This prompt extracts *how* things are written, not *what* is written. Focus on prose mechanics, not investment content.

---

## Non-Negotiables

- No verbatim copying or near-paraphrase of source memos. Do not reproduce distinctive phrasing.
- Treat VIC community score (1-10) as a weak label for writing quality (conflates prose quality with analytical edge and outcome bias).
- Be concrete: step-by-step techniques, implementable patterns, rubrics, and templates.
- You must report exactly what you analyzed (which files, sizes, counts) and how you sampled.

---

## Tooling & File Expectations

Assume you have local folder access to:
1. Raw memo files (HTML/text/JSON/MD, etc.)
2. Prior versions of this writing craft manual (same folder)

**You must:**
- Identify the latest prior version in the folder
- Compare your new output to that latest version and clearly highlight changes
- Log the dataset coverage: number of files read, number of memos parsed, and file sizes

---

## Sampling Protocol (if cannot read all files)

If you cannot read all pieces directly (time/compute/context limits):
- Do NOT pretend you did
- Use a principled sampling + retrieval plan:
  - Stratify by score deciles, memo length buckets, date eras, and position type (long/short)
  - Use embeddings / clustering to ensure coverage of diverse writing styles
  - Expand iteratively until marginal pattern discoveries plateau
- Still report: which files were actually read, their sizes, and how many memos were parsed

---

## Key Feature: Latent Quality Discovery + Self-Upgrading Instruction

Implement an explicit mechanism that discovers latent qualities of strong prose and upgrades the writing instruction manual over time.

### Writing Craft Hypothesis Bank
- Each hypothesis is a candidate latent quality of excellent prose (e.g., sentence rhythm pattern, paragraph architecture, voice technique, structural device usage)
- For each hypothesis: define it operationally, give detection cues, and provide a test plan

### Contrastive Analysis
- Compare top-score vs bottom-score memos *within the same date buckets and length ranges* to reduce confounds
- Identify writing features that meaningfully separate strong from weak prose

### Validation Methods
- **Predictive**: Does feature presence correlate with higher scores after controlling for length/date/author?
- **Pairwise**: Can evaluators reliably identify better prose using the feature?
- **Ablation**: If you remove the feature from a memo draft, does perceived prose quality degrade?

### Upgrade Loop Rules
- Only promote a hypothesis into "Core Instruction" if it clears stated thresholds
- Otherwise keep it in "Experimental / Watchlist" with next experiments

### Versioning Discipline
- Every run produces a new version with a changelog and "what changed and why," grounded in evidence from your analysis

---

## Required Output Sections

**A single run must output ALL sections below:**

### A) RUN METADATA (must be first)
- Timestamp (local), run_id, and output_version (semantic version: vX.Y.Z)
- Folder scanned: path
- Previous version found: filename + version + modified timestamp
- Files analyzed:
  - A table/list of ALL files you actually opened/read, with file size (bytes or KB/MB) and type
  - Count of memos parsed from those files
- Sampling plan used (if not full-corpus): exact rules + distribution summary

### B) DIFF VS LATEST VERSION (must be explicit)
If a prior version exists:
- Provide a bullet list of changes, grouped by:
  1. Schema changes
  2. Voice taxonomy changes
  3. Rubric changes
  4. Feature extraction changes
  5. Playbook changes
  6. Any new "writing craft hypothesis" promoted into Core Instruction
- For each change: state the reason (what evidence triggered it)

If no prior version exists:
- State "No prior version found. This is v0.1.0 baseline."

### C) DEFINING TRAITS OF ELITE PROSE
Output a variable list of defining traits (no fixed count—let it grow as patterns emerge):
- Each bullet must be a *distinct* writing craft trait
- Each bullet must be phrased as a testable property (not vague)
- Add new traits as they are discovered from analysis
- If this version differs from previous version's traits:
  - Mark changed/new bullets with "(NEW)" or "(UPDATED)"
  - Briefly state what changed

### D) DELIVERABLES (6 required items)

#### D1) Writing Craft Schema
Prose metrics to extract from each memo:

**Document Metrics:**
- total_chars, total_words, paragraph_count, sentence_count
- avg_paragraph_length (chars), paragraph_length_variance
- avg_sentence_length (words), sentence_length_variance
- short_sentence_ratio (<12 words), long_sentence_ratio (>20 words)

**Structural Markers:**
- thesis_position (sentence number where main thesis appears)
- section_count (distinct content blocks)
- section_sequence (ordered list of section types detected)
- opening_type (thesis-first, context-first, contrarian, question)
- closing_type (summary, action, catalyst, open)

**Voice Indicators:**
- first_person_frequency (per 1000 words)
- hedging_frequency ("might", "perhaps", "possibly", "could")
- conviction_frequency ("believe", "convinced", "confident", "clearly")
- rhetorical_question_count
- parenthetical_count

**Device Usage:**
- table_count, bullet_list_count, numbered_list_count
- bold_emphasis_count, section_header_count
- whitespace_ratio (blank lines / total lines)

Output format:
- Schema spec in JSON-like pseudoformat
- Extraction notes: regex/heuristics + detection approach
- Quality checks and edge cases

#### D2) Voice Archetype Taxonomy (4 types)
Classify writing voices into 4 archetypes. Each archetype accumulates richer detail as more memos are analyzed:

**The 4 Archetypes:**
1. **The Educator** — Explains concepts patiently, builds understanding, heavy on "because" and causal chains
2. **The Engineer** — Model-focused, precise language, minimal hedging, data-forward
3. **The Storyteller** — Narrative arc, historical context, character development, "journey" framing
4. **The Conviction Machine** — Direct assertions, minimal hedging, "the market is wrong" framing

**For each archetype, maintain:**

*Linguistic Markers (grows over time):*
- Sentence patterns characteristic of this voice
- Word choice tendencies
- Paragraph structure preferences
- Transition patterns
- Opening/closing styles

*Voice-Specific Templates:*
- Opening sentence patterns
- Transition phrases
- Evidence presentation style
- Closing techniques

*Best Use Cases:*
- When this voice works best (complexity level, audience, purpose)
- Memo types that suit this voice

*Anti-Patterns:*
- Common failures when using this voice
- How elite writers avoid them

#### D3) Prose Quality Rubric (1-10, AI-executable)
Use 5 dimensions. Each dimension must have:
- Definition
- Scoring anchors (what a 2/5/8/10 looks like)
- Detection cues

**Dimensions:**

| Dimension | Weight | Definition |
|-----------|--------|------------|
| Structural Clarity | 25% | Logical flow, thesis placement, section organization, transitions |
| Sentence Craft | 20% | Rhythm, variety, punch lines, readability, clause construction |
| Voice & Conviction | 20% | Personality, confidence, hedging balance, author presence |
| Information Design | 20% | Data presentation, tables, lists, density pacing, visual hierarchy |
| Opening & Closing | 15% | Hook effectiveness, conclusion memorability, action orientation |

**Scoring Anchors (for each dimension):**

*Structural Clarity:*
| Score | Description |
|-------|-------------|
| 2 | No clear structure; thesis buried or missing; no logical flow |
| 5 | Clear sections but thesis delayed; transitions adequate but mechanical |
| 8 | Thesis upfront; logical flow; strong transitions; each section earns its place |
| 10 | Masterful organization; inevitable conclusion; reader never lost |

*Sentence Craft:*
| Score | Description |
|-------|-------------|
| 2 | Run-on sentences; monotonous rhythm; no variation; hard to parse |
| 5 | Adequate variety; occasional effective moments; readable |
| 8 | Intentional rhythm; strategic short sentences for punch; flows naturally |
| 10 | Musical prose; every sentence earns its place; memorable lines |

*Voice & Conviction:*
| Score | Description |
|-------|-------------|
| 2 | Generic; hedging-heavy; no personality; could be anyone |
| 5 | Clear point of view; some hedging; minimal personality |
| 8 | Distinct voice; conviction without arrogance; personality emerges |
| 10 | Unmistakable author identity; confident yet intellectually honest |

*Information Design:*
| Score | Description |
|-------|-------------|
| 2 | Wall of text or scattered data; no visual hierarchy; exhausting to read |
| 5 | Some tables/lists; adequate spacing; functional |
| 8 | Strategic device usage; appropriate density; breathing room present |
| 10 | Perfect balance; every table justified; data flows naturally into prose |

*Opening & Closing:*
| Score | Description |
|-------|-------------|
| 2 | Weak or missing hook; no clear ending; fizzles out |
| 5 | Adequate hook; standard conclusion; forgettable |
| 8 | Compelling hook; memorable closing; clear next action |
| 10 | Opening impossible to stop reading; closing creates urgency |

Include:
- Deterministic scoring function (weighted sum)
- Tie-breaker rules
- Handling of: length bias, era effects, author style confounds

#### D4) Feature Extraction Plan (8 categories)
Define how to detect each writing craft feature:

**Category 1: Document Architecture**
| Feature | Operational Definition | Detection Approach |
|---------|----------------------|-------------------|
| Section count | Number of distinct content blocks | H2/H3 markers, blank line clusters, topic shifts |
| Section sequence | Typical ordering pattern | Position-weighted content tagging |
| Section length ratios | % of document per section type | Character counts per section |
| Thesis placement | Sentence number of main thesis | First 500 chars analysis + claim detection |
| Information hierarchy | What comes first, second, third | Content type classification by position |

**Category 2: Paragraph Architecture**
| Feature | Operational Definition | Detection Approach |
|---------|----------------------|-------------------|
| Avg paragraph length | Characters per paragraph | Double-newline split |
| Paragraph length variance | Standard deviation | Statistical analysis |
| Topic sentence placement | First, mid, or closing position | NLP clause analysis |
| Transition patterns | Paragraph-to-paragraph connectors | First-word frequency analysis |
| Single-sentence paragraphs | Frequency and strategic placement | Isolated sentence detection |

**Category 3: Sentence Rhythm & Mechanics**
| Feature | Operational Definition | Detection Approach |
|---------|----------------------|-------------------|
| Sentence length distribution | Words per sentence histogram | Tokenization |
| Short-long-short patterns | Rhythmic alternation | Sequence pattern analysis |
| Punch line placement | Short emphatic sentence after exposition | Pattern: long sentence → short declarative |
| Clause complexity | Simple/compound/complex ratios | NLP parsing |
| Parenthetical usage | Frequency and length | Regex: `\([^)]+\)` |
| Em-dash usage | Frequency and purpose | Pattern: `—` or `--` |

**Category 4: Voice Construction**
| Feature | Operational Definition | Detection Approach |
|---------|----------------------|-------------------|
| First person frequency | "I/we" per 1000 words | Token count |
| Conviction markers | "believe", "convinced", "confident" | Keyword frequency |
| Hedging markers | "might", "perhaps", "possibly" | Keyword frequency |
| Rhetorical questions | Questions outside Q&A sections | Pattern: `\?(?!\s*A:)` |
| Direct address | "you", "consider", "note that" | Token frequency |
| Personality signals | Humor, analogies, metaphors | Pattern detection + manual tagging |

**Category 5: Structural Devices**
| Feature | Operational Definition | Detection Approach |
|---------|----------------------|-------------------|
| Table usage | Frequency, size, placement | Markdown table detection |
| Bullet list design | Nesting, item length, completeness | List pattern analysis |
| Numbered list usage | Sequential vs parallel structure | List type detection |
| Whitespace strategy | Section breaks, visual breathing | Line count analysis |
| Bold/italic emphasis | What gets emphasized | Markdown pattern detection |
| Section header style | Question-based, statement, minimal | Header text analysis |

**Category 6: Opening & Closing Techniques**
| Feature | Operational Definition | Detection Approach |
|---------|----------------------|-------------------|
| Opening hook type | Thesis-first, context-first, contrarian, question | First 200 chars classification |
| Opening length | Characters before main argument | Content boundary detection |
| Closing structure | Summary, call-to-action, catalyst, open | Last 500 chars analysis |
| Catalyst section design | Bullet, prose, table format | End-of-document patterns |

**Category 7: Information Density & Pacing**
| Feature | Operational Definition | Detection Approach |
|---------|----------------------|-------------------|
| Data points per paragraph | Numbers, percentages, dollar figures | Regex count |
| Breathing room | Prose paragraphs between data-heavy sections | Density mapping |
| Concept introduction rate | New terms per section | Noun phrase extraction |
| Repetition for emphasis | Key phrases repeated 2-3 times | N-gram frequency |

**Category 8: Linguistic Patterns & Phrase Craft**
| Feature | Operational Definition | Detection Approach |
|---------|----------------------|-------------------|
| Power phrases | High-impact constructions | N-gram analysis of top memos |
| Cliche detection | Overused phrases to avoid | N-gram analysis of bottom memos |
| Transition vocabulary | Connector words and phrases | First/last word of paragraphs |
| Active vs passive voice | Passive construction frequency | NLP parsing |
| Verb strength | Weak verbs vs strong verbs | Verb classification |

For each feature:
- Operational definition
- Detection heuristics
- Model-assisted classification approach
- Calibration strategy

#### D5) Writing Playbook (Phases + Checklists)

**Phase 1: Structural Planning**
- [ ] Determine opening hook type (thesis-first recommended for clarity)
- [ ] Map section sequence (problem → analysis → evidence → valuation → risks → action)
- [ ] Plan thesis placement (sentence 1-3 for high-clarity)
- [ ] Identify voice archetype best suited to content

**Phase 2: Drafting**
- [ ] Write in selected voice archetype consistently
- [ ] Maintain paragraph discipline (target 150-250 chars average)
- [ ] Vary sentence length intentionally (60% medium, 25% short, 15% long)
- [ ] Place topic sentences at paragraph start (70%+ of paragraphs)
- [ ] Use transitions between paragraphs

**Phase 3: Craft Pass**
- [ ] Add punch lines after complex analytical sentences
- [ ] Insert breathing paragraphs (synthesis/summary) between data-heavy sections
- [ ] Check data density (2-4 data points per paragraph max)
- [ ] Verify table/list usage (tables for comparison, bullets for 3+ items, prose otherwise)
- [ ] Audit whitespace (section breaks every 3-5 paragraphs)

**Phase 4: Voice Polish**
- [ ] Audit hedging vs conviction balance (conviction should dominate for main claims)
- [ ] Add personality moments (parenthetical asides, rhetorical questions sparingly)
- [ ] Verify active voice dominance (>70% of sentences)
- [ ] Check opening hook strength (would you keep reading?)
- [ ] Ensure closing has clear action/takeaway

**Anti-Pattern Catalog:**
- Wall of text: No paragraph breaks, no visual hierarchy
- Hedge overload: Every sentence qualified with "might", "could", "perhaps"
- Monotone rhythm: All sentences same length and structure
- Data dump: Numbers without narrative context
- Buried thesis: Main point appears in paragraph 5+
- Generic voice: Could have been written by anyone
- Trailing off: No clear conclusion or action

**Minimum Viable Memo vs Elite Memo:**
| Aspect | Minimum Viable | Elite |
|--------|---------------|-------|
| Thesis placement | Within first section | First 2 sentences |
| Paragraph length | Consistent | Intentionally varied |
| Sentence rhythm | Adequate variety | Musical, punch lines present |
| Voice | Clear | Distinctive, memorable |
| Information design | Functional | Strategic, never overwhelming |
| Closing | Present | Creates urgency |

#### D6) Validation Plan

**Testing Writing Craft Engine Quality:**
- Blind evaluation design: Rate memos without knowing source
- Holdout sets: Time-based + author-based splits
- Pairwise ranking: A/B comparisons on prose quality (not content)

**Handling Confounds:**
- Length normalization
- Era stratification (writing conventions evolve)
- Author effects (control for prolific writers)
- Score calibration (VIC score mixes content quality with prose)

**Success Metrics:**
| Metric | Target | Baseline |
|--------|--------|----------|
| Prose Quality Score | > 7.5 | 6.0 (corpus median) |
| Structural Clarity | > 8.0 | 6.5 |
| Readability preference | > 60% | 50% (chance) |
| Voice distinctiveness | > 7.0 | 5.5 |

Include failure analysis loop: What went wrong, why, how to fix.

---

### E) LATENT QUALITY MODULE (Writing Craft Focused)

#### E1) Hypothesis Bank Schema

```json
{
  "hypothesis_id": "WC-001",
  "name": "Punch Line Rhythm",
  "category": "sentence_mechanics",
  "status": "experimental",
  "definition": "Short declarative sentence (<8 words) following a complex analytical sentence (>25 words) creates emphasis and memorability",
  "detection_cues": [
    "Sentence ending period after sentence >25 words",
    "Following sentence <8 words",
    "Following sentence contains no hedging language",
    "Following sentence is declarative (not question)"
  ],
  "test_plan": {
    "predictive": "Correlate punch line frequency with prose quality score",
    "pairwise": "Show two memos differing in punch line usage, evaluate readability preference",
    "ablation": "Remove punch lines from memo, evaluate impact on perceived quality"
  },
  "evidence": {
    "predictive_correlation": null,
    "pairwise_preference": null,
    "ablation_degradation": null
  },
  "promotion_threshold": {
    "predictive_r": 0.25,
    "pairwise_preference": 0.60,
    "ablation_degradation": 0.5
  },
  "created_at": null,
  "last_tested": null,
  "promoted_at": null,
  "notes": ""
}
```

#### E2) Initial Writing Craft Hypothesis Bank

| ID | Name | Category | Status | Basis |
|----|------|----------|--------|-------|
| WC-001 | Punch Line Rhythm | sentence | experimental | Short sentences after long create impact |
| WC-002 | Thesis Upfront | structure | **core** | Opening thesis correlates with quality |
| WC-003 | Controlled Paragraph Length | paragraph | experimental | 150-250 char paragraphs score higher |
| WC-004 | Parenthetical Voice | voice | experimental | Asides create personality |
| WC-005 | Rhetorical Question Hooks | opening | experimental | Questions engage reader |
| WC-006 | Data-Prose-Data Sandwich | density | experimental | Breathing room aids comprehension |
| WC-007 | Active Voice Dominance | linguistic | experimental | Active >70% correlates with clarity |
| WC-008 | Conviction Framing | voice | **core** | Explicit "I believe" creates conviction |
| WC-009 | Strategic Table Placement | devices | experimental | Tables for comparison only |
| WC-010 | Single-Sentence Emphasis | paragraph | experimental | Isolated sentences for key points |
| WC-011 | Transition Discipline | paragraph | experimental | Explicit connectors between paragraphs |
| WC-012 | Opening Hook Strength | opening | watchlist | First sentence determines engagement |

#### E3) Promotion Criteria

| Predictive | Pairwise | Ablation | Decision |
|------------|----------|----------|----------|
| Pass (r ≥ 0.25) | Pass (≥ 60%) | Pass (≥ 0.5 pt drop) | **Promote to Core** |
| Pass | Pass | Fail | Promote (ablation optional for some features) |
| Pass | Fail | Pass | **Watchlist**, needs more pairwise data |
| Fail | Pass | Pass | **Watchlist**, investigate correlation |
| Any 2 Fail | - | - | **Reject** |

#### E4) Changelog Discipline

**Version Numbering (vX.Y.Z):**
| Bump | Trigger |
|------|---------|
| X.0.0 (Major) | Voice archetype restructure, major rubric overhaul |
| X.Y.0 (Minor) | Writing hypothesis promoted to Core, template updates |
| X.Y.Z (Patch) | Wording clarifications, threshold adjustments |

**Changelog Format:**
```markdown
## vX.Y.0 - [Date]

### Promoted to Core
- **WC-XXX: [Name]**
  - Evidence: Predictive r=X.XX, Pairwise XX%, Ablation -X.X points
  - Added to: Rubric (Dimension X), Playbook (Phase X), Templates

### Watchlist Updates
- WC-XXX moved to watchlist (reason)

### Rejected
- WC-XXX (reason, evidence)

### Other Changes
- [Specific change with reason]
```

#### E5) Guardrails Against Overfitting

**VIC House Style Risk:**
- Compare patterns to non-VIC writing samples when available
- Exclude VIC-distinctive phrasing from technique definitions
- Test: Does technique work for non-finance writing?

**Spurious Correlation Risk:**
- Always control for length in predictive tests
- Always control for date (era effects)
- Always control for author (celebrity effects)
- Require pairwise confirmation (not just correlation)

**Style vs Substance Confusion:**
- Good prose ≠ good analysis
- Maintain separate rubrics for writing quality vs content quality
- Test writing techniques on memos with varied content quality

---

### F) PITFALLS & COMPLIANCE

**IP/ToS Constraints:**
- No verbatim copying (patterns only)
- No distinctive phrase reproduction
- Usage: AI agent training, not content republishing

**Analytical Biases:**
| Bias | Risk | Mitigation |
|------|------|------------|
| Style vs Substance | Good prose ≠ good analysis | Separate rubrics |
| Era Effects | Writing conventions evolve | Stratify by date |
| Author Effects | Prolific authors dominate patterns | Normalize for author |
| Length Bias | Long ≠ well-written | Control for length |
| Score Conflation | VIC score mixes content + prose | Use as weak label only |

**Overfitting Risks:**
- VIC house style may not generalize to other contexts
- Test patterns on non-VIC writing when possible
- Validate with external writing quality reviewers

**Memorization Risk:**
- Grep output for distinctive VIC phrases
- Test: Can engine apply techniques to unfamiliar topics?
- Regular audit of output for copied language

---

## Output Formatting

Produce one artifact:
- **Markdown manual** (with clear headings, templates, and checklists)

Use headings, checklists, and templates. Avoid fluff.

---

## Tone Constraints

- Direct, craft-focused, and specific
- "Do X, because Y, verify with Z."
- No motivational language
- Show, don't tell (concrete examples, abstracted)

---

## Final Checklist

Before outputting, confirm you included:
- [ ] Run metadata with file sizes + counts
- [ ] Diff vs latest version
- [ ] Defining traits list (with NEW/UPDATED markers if applicable)
- [ ] All 6 required deliverables (Schema, Taxonomy, Rubric, Extraction, Playbook, Validation)
- [ ] Latent quality discovery module with hypothesis bank
- [ ] Pitfalls/compliance

If any are missing, fix before outputting.

---

**Now execute.**
