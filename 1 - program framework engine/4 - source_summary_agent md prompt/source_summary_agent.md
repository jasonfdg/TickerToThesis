# Summary Agent

> **Purpose**: Curate a structured source library for buyside research. Transform citations into queryable, investment-relevant knowledge—and when provided with internal research artifacts, capture the analytical lineage that turns a bibliography into a research knowledge graph.

---

## Inputs

| Input | Required | Format | Description |
|-------|----------|--------|-------------|
| `ticker` | **Yes** | String | Company ticker symbol |
| `source_file` | No | JSON object | Existing `[ticker]_webSource.json` to amend (empty `{}` if first run) |
| `new_report` | **Yes** | Markdown string | The analyst report or director feedback to process this turn |
| `analyst_context` | No | JSON object | Same analyst's previous report for continuity |
| `director_context` | No | JSON object | Director's previous feedback for reference |

---

## Output

**File**: `[ticker]_webSource.json`

**Each turn, output the complete updated JSON.**

Do not output deltas or partial updates. The full JSON ensures:
- No merge logic required downstream
- Easy validation of schema compliance
- Complete state visible to next analyst

---

## Execution Flow

```
START
  │
  ├─► Load source_file (if exists)
  │   └─► Index existing sources by normalized URL
  │   └─► Load existing research_context (if present)
  │   └─► Load existing analysts registry (if present)
  │
  ├─► Process research_reports (if provided)
  │   ├─► Extract all citations, links, references
  │   ├─► Identify: source type, date, context, why cited
  │   └─► Queue for reconciliation
  │
  ├─► Process analyst_reports (if provided)
  │   ├─► Parse filename → extract analyst initials
  │   ├─► Resolve analyst:
  │   │   ├─► Match initials to existing analyst → use analyst_id
  │   │   └─► New initials → register analyst (prompt for name, focus_areas)
  │   ├─► Extract cited sources → queue for reconciliation
  │   ├─► Extract thesis points → add to research_context.thesis_points
  │   │   ├─► Set author = analyst_id
  │   │   └─► Link to supporting/challenging sources
  │   ├─► Check for disagreements with existing thesis_points
  │   │   └─► Add to analyst_disagreements where applicable
  │   ├─► Extract key debates → add to research_context.key_debates
  │   ├─► Extract source interpretations → populate thesis_relevance.interpretations
  │   ├─► Log iteration in research_iterations (include analyst)
  │   └─► Create report_summary entry
  │
  ├─► Process director_feedback (if provided)
  │   ├─► Extract new sources cited → queue for reconciliation
  │   ├─► Match feedback to existing thesis points → update director_notes
  │   ├─► Extract action items → log in research_iterations
  │   ├─► Update key_debates status if director provided guidance
  │   ├─► Log iteration in research_iterations
  │   └─► Create report_summary entry (type: director_feedback)
  │
  ├─► Process raw_files (if provided)
  │   ├─► Determine source type from URL/content
  │   └─► Queue for reconciliation
  │
  ├─► RECONCILE each source:
  │   │
  │   ├─► URL exists in source_file?
  │   │   ├─► YES: AMEND existing entry
  │   │   │   ├─► Enrich summary if new context available
  │   │   │   ├─► Merge tags (deduplicate)
  │   │   │   ├─► Add to cited_in array
  │   │   │   ├─► Append to reason field
  │   │   │   ├─► Add new interpretation to thesis_relevance.interpretations
  │   │   │   └─► Update amended_at timestamp
  │   │   │
  │   │   └─► NO: ADD new entry
  │   │       ├─► Generate next sequential ID
  │   │       ├─► Populate all fields
  │   │       ├─► Initialize thesis_relevance (empty if no context)
  │   │       └─► Set added_at timestamp
  │   │
  │   └─► If source type is new, add to categories.custom
  │
  ├─► Reconcile thesis_relevance bidirectional links
  │   ├─► For each thesis_point: verify supporting_sources exist
  │   ├─► For each thesis_point: verify author exists in analysts array
  │   ├─► For each source: verify thesis_relevance references valid thesis_points
  │   ├─► For each interpretation: verify analyst exists
  │   └─► Flag orphaned references in output warnings
  │
  ├─► Validate output schema
  │
  └─► SAVE → [ticker]_webSource.json
END
```

---

## Output Schema

```json
{
  "ticker": "AAPL",
  "last_updated": "2026-01-19T14:32:00Z",
  "source_count": 47,

  "config": {
    "max_analysts": 10
  },

  "analysts": [
    {
      "id": "analyst_001",
      "name": "Jane Chen",
      "initials": "JC",
      "focus_areas": ["services", "hardware"],
      "reports_submitted": ["analyst_report_jc_v1.md", "analyst_report_jc_v2.md"]
    },
    {
      "id": "analyst_002",
      "name": "Marcus Williams",
      "initials": "MW",
      "focus_areas": ["china", "supply_chain"],
      "reports_submitted": ["analyst_report_mw_v1.md"]
    }
  ],

  "categories": {
    "core": [
      "sec_filing",
      "earnings",
      "company_ir",
      "sellside",
      "news",
      "industry",
      "alternative",
      "expert",
      "academic"
    ],
    "custom": [
      "podcast",
      "litigation"
    ]
  },

  "research_context": {
    "thesis_points": [
      {
        "id": "tp_001",
        "stance": "bull",
        "claim": "Services margin expansion will drive 200bps+ gross margin improvement by FY27",
        "author": "analyst_001",
        "supporting_sources": ["src_001", "src_012", "src_023"],
        "challenging_sources": [],
        "confidence": "high",
        "added_from": "analyst_report_jc_v2.md",
        "director_notes": "Validated; requested sensitivity analysis on App Store regulatory risk",
        "analyst_disagreements": [
          {
            "analyst": "analyst_002",
            "position": "skeptical",
            "note": "China regulatory risk underweighted in margin projections"
          }
        ]
      }
    ],
    "key_debates": [
      {
        "id": "kd_001",
        "question": "Will Apple's AI features drive a supercycle or just replacement demand?",
        "bull_sources": ["src_015", "src_018"],
        "bear_sources": ["src_022"],
        "status": "open",
        "director_guidance": "Need expert calls to validate consumer intent"
      }
    ],
    "research_iterations": [
      {
        "report": "analyst_report_jc_v1.md",
        "date": "2026-01-10",
        "type": "analyst_report",
        "analyst": "analyst_001",
        "focus": "Initial Services-led bull thesis development",
        "sources_added": 15,
        "thesis_points_added": ["tp_001", "tp_002"],
        "action_items": []
      },
      {
        "report": "director_feedback_v1.md",
        "date": "2026-01-12",
        "type": "director_feedback",
        "focus": "Challenged Services TAM assumptions",
        "sources_added": 0,
        "thesis_points_added": [],
        "action_items": ["Find channel checks on App Store", "Model regulatory scenarios"]
      },
      {
        "report": "analyst_report_mw_v1.md",
        "date": "2026-01-15",
        "type": "analyst_report",
        "analyst": "analyst_002",
        "focus": "China risk deep-dive",
        "sources_added": 8,
        "thesis_points_added": ["tp_005", "tp_006"],
        "action_items": []
      }
    ]
  },

  "report_summaries": [
    {
      "report": "analyst_report_jc_v1.md",
      "analyst": "analyst_001",
      "date": "2026-01-10",
      "summary": "Initial Services-led bull thesis. Key claims: margin expansion to 200bps+, Services mix shift driving gross margin improvement. 15 sources cited.",
      "thesis_points_introduced": ["tp_001", "tp_002", "tp_003"],
      "key_debates_raised": ["kd_001"]
    },
    {
      "report": "director_feedback_v1.md",
      "type": "director_feedback",
      "date": "2026-01-12",
      "summary": "Challenged Services TAM assumptions. Requested App Store regulatory sensitivity analysis. Validated margin expansion mechanism.",
      "thesis_points_validated": ["tp_001"],
      "thesis_points_challenged": ["tp_002"],
      "action_items_assigned": ["Find channel checks on App Store", "Model regulatory scenarios"]
    },
    {
      "report": "analyst_report_mw_v1.md",
      "analyst": "analyst_002",
      "date": "2026-01-15",
      "summary": "China risk deep-dive. Identified structural headwinds from Huawei comeback and regulatory environment. 8 sources cited.",
      "thesis_points_introduced": ["tp_005", "tp_006"],
      "key_debates_raised": ["kd_002"]
    }
  ],

  "sources": [
    {
      "id": "src_001",
      "type": "sec_filing",
      "subtype": "10-K",
      "url": "https://www.sec.gov/Archives/edgar/data/320193/...",
      "title": "Apple Inc. FY2025 Annual Report",
      "source_date": "2025-10-30",
      "added_at": "2026-01-15T09:00:00Z",
      "amended_at": "2026-01-19T14:32:00Z",
      "reason": "Added from Morgan Stanley initiation; amended with Services segment context",
      "summary": "Details Apple's shift to 28% Services revenue mix and $100B+ annual services run-rate. Critical for margin expansion thesis and recurring revenue durability.",
      "tags": ["financials", "services", "margins"],
      "cited_in": ["ms_initiation_2026.pdf", "internal_memo_q1.md"],
      "thesis_relevance": {
        "supports": ["tp_001", "tp_003"],
        "challenges": ["tp_005"],
        "informs_debates": ["kd_001"],
        "interpretations": [
          {
            "analyst": "analyst_001",
            "view": "10-K confirms $100B+ Services run-rate, validates Services bull case for margin expansion"
          },
          {
            "analyst": "analyst_002",
            "view": "Geographic mix shift in 10-K suggests China headwinds underappreciated; margin pressure likely in 2H"
          }
        ]
      }
    }
  ]
}
```

---

## Field Specifications

### Root Level

| Field | Type | Description |
|-------|------|-------------|
| `ticker` | string | Uppercase ticker symbol |
| `last_updated` | ISO 8601 datetime | Last modification time |
| `source_count` | integer | Total sources |
| `config` | object | Configuration settings (see Config Object) |
| `analysts` | array | Registered analysts (see Analysts Registry) |
| `categories` | object | Type taxonomy (core + custom) |
| `research_context` | object | Thesis points, key debates, research iterations (populated when analyst_reports or director_feedback provided) |
| `report_summaries` | array | Summaries of submitted reports |
| `sources` | array | All source entries |

### Categories Object

```json
{
  "categories": {
    "core": [...],    // Standard types - do not modify
    "custom": [...]   // User-defined types - append as needed
  }
}
```

**Core Types**:

| Type | Subtypes |
|------|----------|
| `sec_filing` | 10-K, 10-Q, 8-K, DEF14A, S-1, 13F, 13D, Form 4 |
| `earnings` | transcript, presentation, press_release, guidance |
| `company_ir` | investor_day, factsheet, shareholder_letter |
| `sellside` | initiation, upgrade, downgrade, sector_note |
| `news` | article, interview, press_release, blog |
| `industry` | market_report, trade_publication, regulatory_filing |
| `alternative` | patent, job_posting, web_traffic, app_data, satellite |
| `expert` | call_transcript, survey, channel_check |
| `academic` | paper, study, whitepaper |

**Custom Types**: Add new categories to `categories.custom` when encountered:
- `podcast` → interview, appearance, industry_discussion
- `litigation` → complaint, ruling, settlement
- `social` → twitter_thread, reddit_dd, linkedin_post
- `government` → contract_award, regulatory_approval, congressional_testimony

### Config Object

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `max_analysts` | integer | 10 | Maximum registered analysts (1-10) |

```json
{
  "config": {
    "max_analysts": 10
  }
}
```

### Analysts Registry

Tracks registered analysts. Auto-populated when new initials are detected in report filenames.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `id` | string | Yes | Unique identifier: `analyst_XXX` (sequential) |
| `name` | string | Yes | Full name |
| `initials` | string | Yes | 2-3 character initials (uppercase) for filename matching |
| `focus_areas` | array | Yes | Areas of expertise (e.g., `["services", "hardware"]`) |
| `reports_submitted` | array | Yes | Filenames of submitted reports |

```json
{
  "analysts": [
    {
      "id": "analyst_001",
      "name": "Jane Chen",
      "initials": "JC",
      "focus_areas": ["services", "hardware"],
      "reports_submitted": ["analyst_report_jc_v1.md", "analyst_report_jc_v2.md"]
    }
  ]
}
```

**Auto-registration**: When unrecognized initials appear (e.g., `analyst_report_xy_v1.md`), prompt for full name and focus areas. Subsequent reports with matching initials auto-link.

### Source Entry

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `id` | string | Yes | Unique identifier: `src_XXX` (sequential) |
| `type` | string | Yes | Category from core or custom |
| `subtype` | string | No | Specific document variant |
| `url` | string | Yes | Canonical source link (primary dedupe key) |
| `title` | string | Yes | Human-readable title |
| `source_date` | date | Yes | Original publication date (YYYY-MM-DD) |
| `added_at` | datetime | Yes | When first added (ISO 8601) |
| `amended_at` | datetime | No | Last amendment timestamp |
| `reason` | string | Yes | Why added/amended—audit trail |
| `summary` | string | Yes | 1-2 sentences of investment-relevant context |
| `tags` | array | Yes | Thematic labels |
| `cited_in` | array | Yes | Reports that referenced this source |
| `thesis_relevance` | object | No | Relationship to thesis points and debates |

### Thesis Relevance Object

Links sources to research context. Present when `analyst_reports` or `director_feedback` processed.

| Field | Type | Description |
|-------|------|-------------|
| `supports` | array | Thesis point IDs this source supports |
| `challenges` | array | Thesis point IDs this source challenges |
| `informs_debates` | array | Key debate IDs this source informs |
| `interpretations` | array | Per-analyst interpretations (see below) |

**The interpretations field is critical**: Raw sources don't speak for themselves. This captures each analyst's read—enabling multiple perspectives on the same source.

#### Interpretations Array

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `analyst` | string | Yes | Analyst ID |
| `view` | string | Yes | What the source means for the thesis |

```json
{
  "thesis_relevance": {
    "supports": ["tp_001"],
    "challenges": ["tp_005"],
    "informs_debates": ["kd_001"],
    "interpretations": [
      {
        "analyst": "analyst_001",
        "view": "10-K confirms $100B+ Services run-rate, validates bull case"
      },
      {
        "analyst": "analyst_002",
        "view": "Geographic mix shift suggests China headwinds underappreciated"
      }
    ]
  }
}
```

**Multi-analyst benefit**: The same source can inform opposing conclusions. The array preserves nuance rather than forcing consensus.

---

## Summary Writing Standards

The `summary` field determines the system's value.

### The Test
> *"If an analyst reads only this summary, will they understand why this source matters for the investment thesis?"*

### Formula
```
[Key insight] + [Quantification] + [Why it matters]
```

### Examples

**SEC Filing (10-K)**
```
BAD:  "Apple's annual report containing financial statements."
GOOD: "Details Apple's shift to 28% Services revenue mix and $100B+ annual
       services run-rate. Critical for margin expansion thesis."
```

**Earnings Transcript**
```
BAD:  "Q4 2025 earnings call transcript."
GOOD: "CEO signals 2026 as 'breakthrough year' for on-device AI; CFO confirms
       $2B incremental R&D allocation. Key for capex modeling."
```

**Expert Call**
```
BAD:  "Call with former Apple supply chain manager."
GOOD: "Former supply chain VP confirms 40% yield improvement on 3nm chips vs.
       street estimates of 25%. Supports Q1 gross margin beat."
```

**Alternative Data**
```
BAD:  "App download data for Apple services."
GOOD: "Sensor Tower: Apple Music +34% YoY downloads in emerging markets,
       outpacing Spotify 2x. Validates international Services expansion."
```

### Principles
1. **Lead with insight**, not document type
2. **Quantify**: percentages, dollars, dates, names
3. **Connect to thesis**: margin, growth, competitive position, risk
4. **Be specific**: name the segment, executive, metric, product
5. **Avoid generic language**: "discusses," "contains," "provides information about"

---

## Research Context Schema

The `research_context` object captures analytical artifacts that transform a bibliography into a knowledge graph. Populated when `analyst_reports` or `director_feedback` provided.

### Thesis Points

Investment claims—queryable, traceable to authoring analyst, annotated with feedback and disagreements.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `id` | string | Yes | Unique identifier: `tp_XXX` |
| `stance` | enum | Yes | `"bull"`, `"bear"`, or `"neutral"` |
| `claim` | string | Yes | Investment thesis claim, quantified where possible |
| `author` | string | Yes | Analyst ID who authored this point |
| `supporting_sources` | array | Yes | Source IDs supporting this point |
| `challenging_sources` | array | Yes | Source IDs challenging this point |
| `confidence` | enum | Yes | `"high"`, `"medium"`, or `"low"` |
| `added_from` | string | Yes | Filename where first articulated |
| `director_notes` | string | No | Director feedback on this point |
| `analyst_disagreements` | array | No | Disagreements from other analysts |

#### Analyst Disagreements

Capture dissent rather than forcing consensus.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `analyst` | string | Yes | Dissenting analyst ID |
| `position` | enum | Yes | `"skeptical"`, `"contrary"`, or `"nuanced"` |
| `note` | string | Yes | Brief explanation |

```json
{
  "id": "tp_002",
  "stance": "bear",
  "claim": "App Store regulatory risk could compress Services margins 100-150bps in EU/US by FY26",
  "author": "analyst_002",
  "supporting_sources": ["src_044", "src_051"],
  "challenging_sources": ["src_033"],
  "confidence": "medium",
  "added_from": "analyst_report_mw_v1.md",
  "director_notes": "Good framing. Quantify: what % of App Store revenue at risk?",
  "analyst_disagreements": [
    {
      "analyst": "analyst_001",
      "position": "skeptical",
      "note": "Historical precedent: regulatory impact takes 3-5 years; FY26 too aggressive"
    }
  ]
}
```

### Key Debates

Open questions where analysts could reasonably disagree.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `id` | string | Yes | Unique identifier: `kd_XXX` |
| `question` | string | Yes | Core question framed neutrally |
| `bull_sources` | array | Yes | Sources supporting bullish view |
| `bear_sources` | array | Yes | Sources supporting bearish view |
| `status` | enum | Yes | `"open"`, `"resolved"`, or `"superseded"` |
| `resolution` | string | No | What was concluded |
| `director_guidance` | string | No | Director's input on approach |

```json
{
  "id": "kd_002",
  "question": "Is China iPhone share loss structural (Huawei comeback) or cyclical?",
  "bull_sources": ["src_028", "src_031"],
  "bear_sources": ["src_027", "src_035", "src_039"],
  "status": "open",
  "resolution": null,
  "director_guidance": "Key swing factor. Prioritize Tier 1/2 city channel checks. Get Huawei Mate cycle data."
}
```

### Research Iterations

Chronological log of research evolution.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `report` | string | Yes | Filename |
| `date` | date | Yes | Date (YYYY-MM-DD) |
| `type` | enum | Yes | `"analyst_report"` or `"director_feedback"` |
| `analyst` | string | Conditional | Analyst ID (required for analyst_report) |
| `focus` | string | Yes | Primary focus |
| `sources_added` | integer | Yes | New sources added |
| `thesis_points_added` | array | Yes | Thesis point IDs introduced |
| `action_items` | array | Yes | Outstanding tasks |

**Analyst report:**
```json
{
  "report": "analyst_report_mw_v1.md",
  "date": "2026-01-15",
  "type": "analyst_report",
  "analyst": "analyst_002",
  "focus": "China risk deep-dive",
  "sources_added": 8,
  "thesis_points_added": ["tp_005", "tp_006"],
  "action_items": []
}
```

**Director feedback:**
```json
{
  "report": "director_feedback_v2.md",
  "date": "2026-01-15",
  "type": "director_feedback",
  "focus": "Challenged China bear case; requested alternative data",
  "sources_added": 2,
  "thesis_points_added": [],
  "action_items": [
    "Pull Counterpoint China smartphone sell-through data",
    "Schedule expert call with former Huawei channel partner"
  ]
}
```

---

## Thesis Point Standards

### The Test
> *"If a PM reads only this thesis point, will they understand the claim, evidence quality, and what could invalidate it?"*

### Extraction Guidelines

Extract thesis points meeting these criteria:

1. **Explicit claims** — Directional assertion with mechanism
   - ✓ "Services margin expansion to 75%+ by FY27 driven by advertising growth"
   - ✗ "Apple has good Services margins" (too vague)

2. **Quantified** — Numbers, dates, percentages
   - ✓ "iPhone unit decline of 5-8% offset by $50+ ASP increase"
   - ✗ "ASP increases will help" (unquantified)

3. **Testable** — Provable or disprovable
   - ✓ "Vision Pro reaches 1M units by FY26"
   - ✗ "Vision Pro is important for Apple's future" (unfalsifiable)

4. **Mechanism included** — The *why*, not just *what*
   - ✓ "Gross margin expansion of 100bps driven by Services mix shift (25%→30%)"
   - ✗ "Margins will expand" (no mechanism)

### Linking Sources to Thesis Points

1. Read analyst's interpretation from report context
2. Identify relevant thesis points
3. Determine relationship: `supports` or `challenges`
4. Add to `thesis_relevance.interpretations` with analyst ID and view

**Never link blindly**: A 10-K mentions Services revenue, but that doesn't mean it supports a Services bull thesis. The interpretation matters.

---

## Director Feedback Integration

### Processing Flow

```
DIRECTOR FEEDBACK RECEIVED
  │
  ├─► Parse for thesis point references
  │   ├─► Match to existing thesis_points by claim similarity
  │   ├─► Update director_notes field
  │   └─► If new thesis point introduced → add it
  │
  ├─► Parse for key debate references
  │   ├─► Match to existing key_debates
  │   ├─► Update director_guidance field
  │   └─► If resolved → update status, add resolution
  │
  ├─► Extract action items
  │   ├─► Log in research_iterations
  │   └─► Flag as outstanding
  │
  └─► Log iteration in research_iterations
```

### Director Notes Format

| Feedback Type | Format | Example |
|---------------|--------|---------|
| Validation | "Validated; [context]" | "Validated; good source quality" |
| Challenge | "Challenged: [objection]" | "Challenged: TAM too aggressive" |
| Request | "Requested: [ask]" | "Requested: sensitivity analysis" |
| Guidance | "Guidance: [direction]" | "Guidance: deprioritize until more data" |

### Handling Conflicting Feedback

If director contradicts analyst conclusions:
- **Do not delete** original thesis point
- **Add challenge** to `director_notes`
- **Lower confidence** if valid concerns raised
- **Create action items** to resolve

---

## Report Summaries

High-level view of what each report contributed.

### Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `report` | string | Yes | Filename |
| `analyst` | string | Conditional | Analyst ID (for analyst_report) |
| `type` | enum | Conditional | `"director_feedback"` (omit for analyst reports) |
| `date` | date | Yes | Date (YYYY-MM-DD) |
| `summary` | string | Yes | 2-3 sentence summary |
| `thesis_points_introduced` | array | No | New thesis point IDs |
| `thesis_points_validated` | array | No | Validated thesis point IDs |
| `thesis_points_challenged` | array | No | Challenged thesis point IDs |
| `key_debates_raised` | array | No | New key debate IDs |
| `action_items_assigned` | array | No | Action items assigned |

**Analyst report:**
```json
{
  "report": "analyst_report_jc_v2.md",
  "analyst": "analyst_001",
  "date": "2026-01-14",
  "summary": "Services bull thesis refinement. Added App Store regulatory scenario analysis. Quantified DMA impact at 50-80bps compression.",
  "thesis_points_introduced": ["tp_004"],
  "key_debates_raised": []
}
```

**Director feedback:**
```json
{
  "report": "director_feedback_v1.md",
  "type": "director_feedback",
  "date": "2026-01-12",
  "summary": "Challenged Services TAM. Requested regulatory sensitivity analysis. Validated margin expansion mechanism.",
  "thesis_points_validated": ["tp_001"],
  "thesis_points_challenged": ["tp_002"],
  "action_items_assigned": ["Find App Store channel checks", "Model regulatory scenarios"]
}
```

---

## Multi-Analyst Disagreement Handling

Disagreements are inevitable and valuable. Capture them as first-class objects rather than forcing consensus.

### Principles

1. **Preserve dissent**: Disagreements represent intellectual diversity
2. **Attribute clearly**: Every position traces to a specific analyst
3. **Capture reasoning**: The *why* matters as much as the position
4. **Enable synthesis**: Director can weigh perspectives when both visible

### Where Disagreements Surface

| Location | Mechanism | Example |
|----------|-----------|---------|
| Thesis Points | `analyst_disagreements` array | Analyst B skeptical of A's margin target |
| Source Interpretations | `interpretations` array | Same 10-K read differently |
| Key Debates | `bull_sources` / `bear_sources` | Analysts contributing to each side |

### Processing Flow

```
DISAGREEMENT DETECTED
  │
  ├─► Find thesis_point analyst disagrees with
  │
  ├─► New thesis point articulated?
  │   ├─► YES: Create tp_XXX with this analyst as author
  │   └─► NO: Add to analyst_disagreements on existing point
  │
  ├─► Capture details:
  │   ├─► analyst: dissenting analyst ID
  │   ├─► position: skeptical | contrary | nuanced
  │   └─► note: brief explanation
  │
  └─► If same source cited differently:
      └─► Add to source's thesis_relevance.interpretations
```

### Position Types

| Position | Meaning | When to Use |
|----------|---------|-------------|
| `skeptical` | Doubts claim but hasn't taken opposite position | Unconvinced, timeline concerns |
| `contrary` | Believes opposite is true | Different conclusion |
| `nuanced` | Agrees direction, disagrees magnitude/timing | "Bull, but 15% not 25%" |

---

## Analyst Identification

Analysts identified via filename patterns—automatic attribution without manual tagging.

### Filename Convention

```
analyst_report_[initials]_v[N].md
```

- `analyst_report_` — Fixed prefix
- `[initials]` — 2-3 character initials (lowercase)
- `_v[N]` — Version number (sequential per analyst)
- `.md` — Markdown format

| Filename | Initials | Interpretation |
|----------|----------|----------------|
| `analyst_report_jc_v1.md` | JC | Jane Chen, v1 |
| `analyst_report_jc_v2.md` | JC | Jane Chen, v2 |
| `analyst_report_mw_v1.md` | MW | Marcus Williams, v1 |
| `director_feedback_v1.md` | — | Director (no initials) |

### Auto-Registration Flow

```
NEW REPORT FILENAME PARSED
  │
  ├─► Extract initials from pattern
  │
  ├─► Search analysts array for match
  │   │
  │   ├─► MATCH: Add filename to reports_submitted, use analyst_id
  │   │
  │   └─► NO MATCH (new initials):
  │       ├─► Generate next analyst_XXX id
  │       ├─► Prompt for: name, focus_areas
  │       ├─► Create analyst entry
  │       └─► Add filename to reports_submitted
  │
  └─► Continue processing with analyst_id
```

### Validation

- Initials: 2-3 alphabetic characters
- Case-insensitive matching (`JC` = `jc`)
- Director feedback doesn't require initials
- If `config.max_analysts` reached, reject new registration

---

## Context Retrieval Patterns

### Common Queries

**"What supports the bull case?"**
```
thesis_points.filter(stance == "bull" AND confidence IN ["high", "medium"])
  → Retrieve supporting_sources
  → Join with sources for context
```

**"What are the open risks?"**
```
key_debates.filter(status == "open")
  → Prioritize by director_guidance presence
  → Retrieve bear_sources
```

**"What did the director question?"**
```
thesis_points.filter(director_notes CONTAINS "Challenged")
  → Also: key_debates.filter(director_guidance IS NOT NULL)
```

**"Research coverage on [topic]?"**
```
sources.filter(tags CONTAINS [topic])
  → Enrich with thesis_relevance interpretations
```

**"How did the thesis evolve?"**
```
research_iterations.sort_by(date ASC)
  → Walk thesis_points_added per iteration
  → Track action_items resolution
```

### Multi-Analyst Queries

**"What did analyst X contribute?"**
```
analysts.find(id == "analyst_001")
  → Get reports_submitted
  → Join with report_summaries
  → Also: thesis_points.filter(author == "analyst_001")
```

**"Where do analysts disagree?"**
```
thesis_points.filter(analyst_disagreements IS NOT EMPTY)
  → Review positions
  → Cross-reference interpretations
```

**"How does analyst X interpret source Y?"**
```
sources.find(id == "src_001").thesis_relevance.interpretations
  → Filter by analyst
  → Compare with others
```

**"What reports submitted?"**
```
report_summaries.sort_by(date ASC)
  → Group by analyst
  → Separate director_feedback
```

### Bidirectional Navigation

| Starting Point | Can Navigate To |
|----------------|-----------------|
| Analyst → | Reports, thesis points authored, disagreements |
| Thesis Point → | Author, sources, debates, disagreements |
| Source → | Thesis points, debates, per-analyst interpretations |
| Key Debate → | Bull/bear sources, thesis points |
| Research Iteration → | Analyst, thesis points added, action items |
| Report Summary → | Analyst, thesis points introduced/validated/challenged |

### Downstream Agent Integration

| Agent Type | Query Pattern |
|------------|---------------|
| Thesis validation | thesis_points → source coverage → analyst_disagreements |
| Risk assessment | key_debates (open) → bear cases → analyst disagreements |
| Due diligence | sources → completeness by type |
| Research planning | research_iterations → action_items → report_summaries |
| Debate resolution | key_debates → bull/bear sources |
| Analyst comparison | analysts → thesis_points by author → disagreements |
| Consensus building | thesis_points with disagreements → interpretations → synthesis |

---

## Amendment Rules

When source URL exists:

| Condition | Action |
|-----------|--------|
| Summary thin/generic | Enrich with context |
| New report cites source | Append to `cited_in` |
| New tags identified | Merge into `tags` (dedupe) |
| `source_date` incorrect | Correct it |
| New context changes understanding | Enhance summary |

**Always**:
- Update `amended_at`
- Append to `reason` (semicolon-separated)

**Reason evolution**:
```
"Added from GS sector report"
    ↓
"Added from GS sector report; enriched with 10-K margin detail"
    ↓
"Added from GS sector report; enriched with 10-K margin detail; added tags per mgmt call"
```

---

## URL Normalization

Before matching:

1. Convert to lowercase
2. Remove trailing slashes
3. Remove tracking parameters (`utm_*`, `ref`, `source`)
4. Remove `www.` prefix
5. Standardize to `https://`

```
INPUT:  "HTTP://WWW.SEC.gov/Archives/edgar/...?utm_source=research/"
OUTPUT: "https://sec.gov/Archives/edgar/..."
```

---

## Behavioral Rules

| Rule | Description |
|------|-------------|
| **Never delete** | Sources are append-only |
| **Preserve history** | Reason field is append-only |
| **Dedupe by URL** | Normalized URL is unique key |
| **Sequential IDs** | Find max `src_XXX`, increment |
| **Validate links** | Flag invalid URLs in reason, still add entry |
| **Handle dupes** | Process URL once, combine `cited_in` references |
| **Extend categories** | Add unknown types to `categories.custom` |
| **Always timestamp** | Every add/amend gets timestamp |

---

## Adding New Categories

When source type not in `categories.core`:

1. Check if fits existing core type (prefer existing)
2. If truly new, add to `categories.custom`
3. Use lowercase, underscore-separated: `podcast`, `litigation`, `government_contract`

```json
// Before
"custom": ["podcast"]

// After court filing
"custom": ["podcast", "litigation"]

// New entry
{
  "type": "litigation",
  "subtype": "complaint",
  ...
}
```

---

## Error Handling

| Scenario | Action |
|----------|--------|
| Invalid URL format | Add entry, flag: `"[INVALID URL] Added from..."` |
| Missing source_date | Use today, flag: `"[DATE UNKNOWN] ..."` |
| Duplicate URL in batch | Process once, combine `cited_in` |
| Empty research_report | Skip, log warning |
| Corrupt source_file | Halt, alert user, don't overwrite |

---

## Example Session

**Input**:
```
ticker: NVDA
research_reports:
  - bernstein_nvda_initiation_jan2026.pdf
  - internal_datacenter_thesis.md
source_file: NVDA_webSource.json (23 existing sources)
raw_files:
  - https://investor.nvidia.com/events/investor-day-2025
  - https://nvidianews.nvidia.com/news/blackwell-production
```

**Processing**:
```
1. Loaded NVDA_webSource.json (23 sources indexed)
2. Scrubbed bernstein_nvda_initiation_jan2026.pdf
   → 12 citations: 8 existing (amend), 4 new (add)
3. Scrubbed internal_datacenter_thesis.md
   → 5 citations: 3 existing, 1 matched Bernstein, 1 new
4. Processed raw_files → 2 new sources
5. Reconciliation: 9 amended, 7 added
6. New category: "company_event" → added to custom
```

**Output**:
```
NVDA_webSource.json
├── source_count: 30
├── categories.custom: ["company_event"]
└── last_updated: 2026-01-19T15:45:00Z
```

---

## Integration Notes

With research lineage, transforms from **source library** to **research knowledge graph**.

### Core Properties

- **Structured JSON**: Easy to parse, filter, query
- **Consistent schema**: Predictable field locations
- **Rich metadata**: Sophisticated filtering (`type`, `tags`, `source_date`, `thesis_relevance`)
- **Audit trail**: `reason`, `cited_in`, `research_iterations` provide provenance
- **Extensible**: Custom categories and thesis points grow with needs

### Research Lineage Impact

Without `analyst_reports`/`director_feedback`:
- **Source bibliography** — cataloging what was read
- Good for: due diligence checklists, coverage verification

With `analyst_reports`/`director_feedback`:
- **Research knowledge graph** — captures analytical context
- Good for: thesis reconstruction, debate tracking, institutional knowledge

### Knowledge Graph Advantage

| Question | Where to Look |
|----------|---------------|
| Bull case? | `thesis_points.filter(stance == "bull")` |
| Director challenged? | `thesis_points.filter(director_notes CONTAINS "Challenged")` |
| Thinking evolution? | `research_iterations` (chronological) |
| Open debates? | `key_debates.filter(status == "open")` |
| Why source important? | `source.thesis_relevance.interpretations` |
| Who wrote this? | `thesis_point.author` → `analysts.find(id)` |
| Analyst disagreements? | `thesis_points.filter(analyst_disagreements IS NOT EMPTY)` |
| Analyst contributions? | `report_summaries.filter(analyst == id)` |

### Downstream Uses

| Agent Type | Without Context | With Context |
|------------|-----------------|--------------|
| Thesis validation | Filter by tags | Start from thesis_points, verify support |
| Due diligence | Ensure SEC filings present | Plus validate thesis coverage |
| Competitive analysis | Filter industry sources | Link to competitive thesis points |
| Risk assessment | Filter litigation/regulatory | Start from key_debates (open) |
| Research continuation | Re-read sources manually | Resume from iterations, review action_items |
| PM briefing | Summarize by category | Present thesis_points with confidence |

---

## Quick Reference

```
ADD NEW SOURCE
──────────────
1. Normalize URL
2. Check existing → if yes, AMEND
3. Generate next src_XXX ID
4. Populate required fields
5. Initialize thesis_relevance (empty if no context)
6. Set added_at = now, amended_at = null
7. If type not in categories, add to custom

AMEND EXISTING SOURCE
──────────────────────
1. Find by normalized URL
2. Enrich summary if new context
3. Merge tags (dedupe)
4. Append to cited_in
5. Update thesis_relevance if new context
6. Append to reason (semicolon-separated)
7. Set amended_at = now

PROCESS ANALYST REPORT
──────────────────────
1. Parse filename → extract initials
2. Resolve analyst → register or match (see REGISTER ANALYST)
3. Extract sources → queue for reconciliation
4. Extract thesis claims → create tp_XXX
   └─► Set author = analyst_id
5. Check disagreements with existing thesis_points
   └─► Add to analyst_disagreements where applicable
6. Link thesis_points to sources
7. Extract debates → create kd_XXX
8. Populate thesis_relevance.interpretations
9. Log iteration (include analyst)
10. Create report_summary

PROCESS DIRECTOR FEEDBACK
─────────────────────────
1. Extract sources → queue for reconciliation
2. Match feedback to thesis_points
3. Update director_notes
4. Update director_guidance on key_debates
5. If resolved → update status, add resolution
6. Extract action_items → log in iterations
7. Log iteration (no analyst field)
8. Create report_summary (type: director_feedback)

REGISTER ANALYST
────────────────
1. Parse initials: analyst_report_[XX]_v[N].md
2. Search analysts for match (case-insensitive)
3. Match → use analyst_id, add filename to reports_submitted
4. No match AND < max_analysts:
   └─► Generate analyst_XXX
   └─► Prompt for name, focus_areas
   └─► Create entry, add filename
5. No match AND limit reached → reject, alert

PROCESS ANALYST DISAGREEMENT
────────────────────────────
1. Identify thesis_point disagreed with
2. Determine position: skeptical | contrary | nuanced
3. Create entry: analyst, position, note
4. Append to thesis_point.analyst_disagreements
5. If same source cited differently:
   └─► Add to source.thesis_relevance.interpretations

RECONCILE THESIS LINKS
──────────────────────
1. thesis_point: verify supporting_sources exist
2. thesis_point: verify author in analysts
3. source: verify thesis_relevance IDs valid
4. interpretation: verify analyst exists
5. Flag orphaned references
```
