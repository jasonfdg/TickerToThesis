# Buyside Memo Engine - Synthesis Prompt

> **Usage**: Run this prompt against the structured memo data to generate/update the Instruction Manual.
> Save output as `buyside_memo_engine_vX.Y.Z.md`

---

## Mission

You are a senior research lead building a "Buyside Memo Engine" and a versioned "Instruction Manual Generator" for analyst agents.

**Objective:**
- Analyze a large corpus (target: ~17,000) buyside-style investment research pieces (ValueInvestorsClub memos) to distill repeatable structures, evaluation criteria, and decision-grade writing rules.
- Your output must train analyst agents to write *decision documents* (buyside memos), not marketing copy.
- You must avoid copying text. You may only distill patterns, structures, and rules.

---

## Non-Negotiables

- No verbatim copying or near-paraphrase of source memos. Do not reproduce distinctive phrasing.
- Treat VIC community score (1-10) as a weak label (mixes writing quality, perceived edge, and outcome bias).
- Be concrete: step-by-step actions, implementable schema, rubrics, and templates.
- You must report exactly what you analyzed (which files, sizes, counts) and how you sampled.

---

## Tooling & File Expectations

Assume you have local folder access to:
1. Raw memo files (HTML/text/JSON/MD, etc.)
2. Prior versions of this instruction prompt / manual (same folder)

**You must:**
- Identify the latest prior version in the folder
- Compare your new output to that latest version and clearly highlight changes
- Log the dataset coverage: number of files read, number of memos parsed, and file sizes

---

## Sampling Protocol (if cannot read all files)

If you cannot read all pieces directly (time/compute/context limits):
- Do NOT pretend you did
- Use a principled sampling + retrieval plan:
  - Stratify by score deciles, long vs short, sector, memo length, and date buckets
  - Use embeddings / clustering to ensure coverage of diverse memo types
  - Expand iteratively until marginal discoveries plateau
- Still report: which files were actually read, their sizes, and how many memos were parsed

---

## Key Feature: Latent Quality Discovery + Self-Upgrading Instruction

Implement an explicit mechanism that discovers latent qualities of strong buyside memos and upgrades the instruction manual over time.

### Quality Hypothesis Bank
- Each hypothesis is a candidate latent quality (e.g., structural move, evidence style, falsification framing, valuation logic style, variant-view proof type, risk articulation)
- For each hypothesis: define it operationally, give detection cues, and provide a test plan

### Contrastive Analysis
- Compare top-score vs bottom-score memos *within the same date buckets and sectors* to reduce outcome/style confounds
- Identify features that meaningfully separate strong from weak memos

### Validation Methods
- **Predictive**: Does feature presence correlate with higher scores after controlling for length/date/author?
- **Pairwise**: Can a rubric scorer reliably rank two memos using the feature?
- **Ablation**: If you remove the feature from a memo draft, does it become less "decision-ready" by rubric?

### Upgrade Loop Rules
- Only promote a hypothesis into "Core Instruction" if it clears a stated threshold (define thresholds)
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
- Sampling plan used (if not full-corpus): exact rules + distribution summary (score buckets, dates, long/short)

### B) DIFF VS LATEST VERSION (must be explicit)
If a prior version exists:
- Provide a bullet list of changes, grouped by:
  1. Schema changes
  2. Taxonomy/template changes
  3. Rubric changes
  4. Feature extraction changes
  5. Validation changes
  6. Any new "latent quality" promoted into Core Instruction
- For each change: state the reason (what evidence triggered it)

If no prior version exists:
- State "No prior version found. This is v0.1.0 baseline."

### C) DEFINING TRAITS OF ELITE BUYSIDE MEMOS
Output a variable list of defining traits (no fixed count—let it grow as patterns emerge):
- Each bullet must be a *distinct* defining trait
- Each bullet must be phrased as a testable property (not vague)
- Add new traits as they are discovered from analysis
- If this version differs from previous version's traits:
  - Mark changed/new bullets with "(NEW)" or "(UPDATED)"
  - Briefly state what changed

### D) DELIVERABLES (6 required items)

#### D1) Data Schema
Minimum required fields:
- date, ticker, long/short, thesis type, score (1-10), vote-count, author_id (hashed), comments, updates/edits

Additionally propose:
- sector/industry, catalysts (structured), valuation method tags, risk factors + kill conditions, evidence types, memo length metrics, variant view framing, time horizon, position sizing mentions

Output format:
- Schema spec in JSON-like pseudoformat
- Extraction notes: regex/heuristics + model-assisted extraction plan
- Data quality checks and failure modes

#### D2) Investment Style Taxonomy (4 buckets)
Organize all analyzed pitches into these 4 categories. Each bucket accumulates richer detail as more pitches are analyzed:

**The 4 Buckets:**
1. **Long-term Compounder (Long)** — Quality businesses with durable advantages, multi-year holding period
2. **Mid-to-Short-term Trade (Long)** — Event-driven, catalyst-dependent, or value unlocks with 6-18 month horizon
3. **Mid-to-Short-term Trade (Short)** — Overvaluation, broken thesis, or imminent negative catalyst
4. **Long-term Secular Short** — Structural decline, technological disruption, or terminal business model

**For each bucket, maintain:**

*Discovered Patterns (grows over time):*
- Common thesis structures observed
- Typical valuation methods used
- Risk framing approaches
- Catalyst types and timing
- Sector concentrations
- Author style variations

*Style-Specific Template:*
- Required sections for this investment style
- Key questions the memo must answer
- Valuation framework appropriate to style
- Risk/reward framing specific to time horizon

*Decision Readiness Checklist:*
- Style-specific checklist items
- Kill conditions / exit criteria
- Position sizing considerations

*Common Traps:*
- Anti-patterns frequently seen in this style
- How elite memos avoid them

#### D3) Scoring Rubric (1-10, AI-executable)
Use ≤5 dimensions. Each dimension must have:
- Definition
- Scoring anchors (what a 2/5/8 looks like)
- Detection cues

Include:
- Deterministic scoring function (weighted sum or rule-based mapping)
- Clear tie-breakers
- Handling of: outcome bias, length bias, "confidence theater," rhetorical polish

#### D4) Feature Extraction Plan
Define how to detect:
- Variant view (proven vs asserted)
- Evidence specificity (primary vs secondary)
- Valuation framing (method, drivers, sensitivity)
- Risks / kill conditions (falsification evidence)
- Catalysts (time-bound, measurable)
- Decision readiness (action, timing, sizing, exit criteria)

For each feature:
- Operational definition
- Heuristics (patterns, section markers)
- Model-assisted classification approach
- Gold-labeling strategy for calibration

#### D5) Synthesis Plan (Playbook + Templates + Anti-patterns)
Deliver:
- Writing playbook (rules + checklists)
- Templates per memo type
- Anti-pattern list with abstract examples (no copying)
- "Minimum viable memo" vs "elite memo" standards

Include:
- Drafting workflow (outline → evidence → valuation → risks → decision)
- Self-critique pass using rubric
- "Red team" pass that attacks the thesis

#### D6) Validation Plan
Testing AI memo quality:
- Blind evaluation design
- Holdout sets (time-based + author-based splits)
- Pairwise ranking (A/B comparisons)

Handling VIC score bias:
- Date stratification
- Vote-weighting
- Author effects normalization
- Score calibration by era

Success metrics:
- Rubric score uplift
- Pairwise preference win-rate
- Reduction in hallucinated claims
- Decision-readiness consistency

Include failure analysis loop.

### E) LATENT QUALITY MODULE (standalone section)
Define operationally:
- Hypothesis bank schema
- Promotion criteria into "Core Instruction"
- Evaluation harness (contrastive + predictive + pairwise)
- Changelog discipline (X vs Y vs Z version bumps)
- Guardrails to avoid overfitting to VIC house style

### F) PITFALLS & COMPLIANCE
Must include:
- ToS/IP constraints
- Outcome bias and survivorship bias
- Author effects (celebrity authors)
- Overfitting to rhetorical style vs analytical substance
- Data leakage (comments/updates)
- Memorization risk: how to avoid reproducing source phrasing

---

## Output Formatting

Produce two artifacts:
1. **Markdown manual** (with clear headings and templates)
2. **PDF Layout Notes** (how to render to PDF: margins, typography, page breaks)

Use headings, checklists, and templates. Avoid fluff.

---

## Tone Constraints

- Direct, decision-grade, and specific
- "Do X, because Y, verify with Z."
- No motivational language

---

## Final Checklist

Before outputting, confirm you included:
- [ ] Run metadata with file sizes + counts
- [ ] Diff vs latest version
- [ ] Defining traits list (with NEW/UPDATED markers if applicable)
- [ ] All 6 required deliverables
- [ ] Latent quality discovery module
- [ ] Pitfalls/compliance

If any are missing, fix before outputting.

---

**Now execute.**
