# CLAUDE.md

This file provides guidance to Claude Code when working with this repository.

## Project Overview

Multi-agent investment research automation framework. Generates institutional-quality buyside memos by orchestrating 6 parallel AI analyst agents (each with distinct investing philosophies) through 5 debate iterations with a Research Director.

## Commands

### Pipeline Execution
```bash
cd "1 - program framework engine/0 - buyside_research_pipeline"
source venv/bin/activate

# Full pipeline: 5 iterations × 6 analysts + synthesis + polish
python TickerToThesis.py AAPL "preliminary investment thinking..."

# Resume from specific iteration (e.g., continue from iteration 3)
python resume_pipeline.py AAPL 3

# Synthesis only (uses existing v5 reports)
python run_synthesis_only.py AAPL

# Comprehensive synthesis on ALL reports (60 reports + source file)
python run_full_synthesis.py AAPL
```

### Setup
```bash
cd "1 - program framework engine/0 - buyside_research_pipeline"
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env  # Then add ANTHROPIC_API_KEY
```

## Architecture

### Core Flow
```
User: $TICKER + "preliminary thinking"
         ↓
    ITERATION 1-5
    ├── 6 Parallel Analysts → Reports [Av1...Av5]
    ├── Source file refresh
    └── 6 Parallel RD Reviews → Feedback [Bv1...Bv5]
         ↓
    SYNTHESIS (rd_synthesis_prompt on all v5 reports)
         ↓
    POLISH (human_readable_output_engine)
         ↓
Output: ${TICKER}_memo_vF.md
```

### Key Modules (`0 - buyside_research_pipeline/`)

| Module | Purpose |
|--------|---------|
| `TickerToThesis.py` | Main orchestrator, CLI entry point |
| `agent_runner.py` | Async Claude API with retry/rate limiting (50 RPM semaphore, exponential backoff) |
| `config.py` | Model config (claude-sonnet-4-20250514), paths, 6 investing types |
| `models.py` | `AgentRole` enum, `TokenUsage`, `AgentReport`, `PipelineState` dataclasses |
| `prompt_loader.py` | Cached loading of all prompt files |
| `report_saver.py` | Saves 60 interim reports + synthesis to `2 - report output/$TICKER/` |
| `source_manager.py` | Manages `${TICKER}_webSource.json` |

### Prompt System (`1 - program framework engine/`)

```
1 - agent_role md prompt/
    ├── analyst_prompt.md         # Core analyst identity
    ├── rd_review_prompt.md       # Research Director critique
    └── rd_synthesis_prompt.md    # Final synthesis directive

2 - agent_investing_type md prompt/analyst_investing_type/
    ├── 1-quality-compounders.md  # Buffett/Munger style
    ├── 2-imaginative-growth.md   # High-growth bets
    ├── 3-fundamental-long-short.md
    ├── 4-deep-value.md
    ├── 5-event-driven.md
    └── 6-macro-tactical.md

3 - agent synthesis engine md prompt/
    └── buyside_memo_engine_v1.3.0.md  # Main "constitution"

5 - final_readable_touch-up md prompt/
    └── human_readable_output_engine.md
```

### Output Structure
```
2 - report output/$TICKER/
├── interim/
│   ├── analyst_type_1_v1.md ... analyst_type_6_v5.md  (30 reports)
│   └── rd_review_type_1_v1.md ... rd_review_type_6_v5.md  (30 reviews)
├── ${TICKER}_webSource.json
├── ${TICKER}_synthesis_raw.md
└── ${TICKER}_memo_vF.md
```

## Design Principles

**Debate as Core Pattern**: The 5-iteration cycle forces genuine intellectual disagreement. Analysts defend positions; RD challenges them. Final synthesis resolves conflicts with evidence hierarchy.

**Philosophy-First Agents**: Each of 6 analyst types embodies a distinct investing worldview. They're not just different prompts—they're different mental models.

**Evidence Hierarchy**: Outputs distinguish high-confidence facts (primary sources) → medium-confidence inferences → speculation requiring validation. Kill conditions are explicit.

**Stateful & Resumable**: Pipeline saves after each phase. `resume_pipeline.py` can continue from any iteration after API failures or credit depletion.

## API Handling

- Model: `claude-sonnet-4-20250514`, 16K max tokens, temp 0.7
- Rate limiting: 50 RPM semaphore, 30-120s exponential backoff on 529 errors
- Sequential execution with delays between calls
- Expect ~1.7M tokens for full 5-iteration run (~$13-15 per ticker)

## Documentation Maintenance (project rule)

**After any change to the pipeline, prompts, provider routing, or output format — in the same turn that makes the change — update both `README.md` and `CHANGELOG.md`.** Do not defer to a later turn. Do not wait for the user to ask.

### CHANGELOG.md (full log, append per session)

Append a bullet under the current session heading (create a new heading if starting a new session). Describe the concrete change and name the files touched. Cover everything including infrastructure and internals — nothing is "too small."

### README.md (curated)

Update the sections affected by the change:

- **Auto-synced content** — do NOT hand-edit anything between `<!-- STATS:KEY --> <!-- /STATS -->` markers or inside the `<!-- TREE:START --> <!-- TREE:END -->` block. These are overwritten by sync scripts on each pipeline run. Your job is to add / remove / reposition markers, not to set the values inside them.
- Pipeline step descriptions (analyst routing, RD review routing, synthesis model)
- Output format changes, memo structure, evidence labeling rules
- Known Limitations, Pending Work trackers
- **Pending Work:** strike through (`~~N~~`) and add **DONE** note when an item ships; add new items for new follow-ups
- **Done section:** add a curated bullet for each shipped user-visible item

### When not to edit

If the change is purely internal refactoring that doesn't affect documented behavior, skip README (CHANGELOG still gets a bullet). When uncertain, err on the side of adding a bullet.

### Self-check at end of each turn

"Did I change code or data? Did I update CHANGELOG? Did I update README sections affected by this change?" If yes/yes/yes → commit-ready. If yes/no/* → fix it before moving on.

## Agent Workflow Rules (from AGENT_WORKFLOW.md)

- Always `git fetch origin; git checkout master; git pull origin master` before starting work.
- Create a new branch per fix. Never modify unrelated files. Stage only files touched by the fix.
- Read full files before editing. Make the smallest possible change. Preserve logging and CLI behavior.
- After editing: `python -m py_compile <edited_files>` and inspect `git diff` before pushing.
- Stop and ask when: required data source is unclear, multiple architectural approaches exist, or fix touches unrelated subsystems.
