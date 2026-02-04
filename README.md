# TickerToThesis

**Multi-agent framework for generating institutional-quality buyside investment memos.**

Built on analysis of 13,635 VIC (Value Investors Club) memos. Uses 6 parallel AI analysts with distinct investing philosophies through 5 debate iterations with a Research Director.

🔗 **Website:** [tickertothesis.com](https://tickertothesis.com)

---

## How It Works

```
User: $TICKER + "preliminary thinking"
         ↓
    ITERATION 1-5 (5 debate rounds)
    ├── 6 Parallel Analysts → Reports [v1...v5]
    ├── Source file refresh each iteration
    └── 6 Parallel RD Reviews → Feedback [v1...v5]
         ↓
    SYNTHESIS (RD merges all v5 reports)
         ↓
    POLISH (human-readable output)
         ↓
Output: ${TICKER}_memo_vF.md
```

**The core insight:** Debate produces better analysis than consensus. Six distinct worldviews, forced to defend positions against rigorous critique, converge on institutional-quality conviction.

---

## The Six Analysts

Each analyst embodies a distinct investing philosophy—not just different prompts, but different mental models:

| # | Philosophy | Time Horizon | Key Metric | Representatives |
|---|------------|--------------|------------|-----------------|
| 1 | **Quality Compounders** | Forever | ROIC | Buffett, Munger, Li Lu |
| 2 | **Imaginative Growth** | 5+ years | Revenue growth | Baillie Gifford, ARK |
| 3 | **Fundamental L/S** | 1-3 years | EV/EBITDA | Viking, Lone Pine, Tiger Cubs |
| 4 | **Deep Value** | Years (patient) | Replacement cost | Klarman, Howard Marks |
| 5 | **Event-Driven** | 6-18 months | Catalyst timeline | Tepper, Ackman, Elliott |
| 6 | **Macro-Tactical** | Regime-dependent | Fed policy | Druckenmiller, Bessent |

Each analyst forms conviction early, then defends it against the Research Director's critique. When the RD pushes back, they engage—not capitulate.

---

## Quick Start

```bash
git clone https://github.com/jasonfdg/TickerToThesis.git
cd "TickerToThesis/1 - program framework engine/0 - buyside_research_pipeline"

# Setup
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Configure
cp .env.example .env
# Edit .env and add your ANTHROPIC_API_KEY

# Run
python TickerToThesis.py AAPL "Apple's services business is undervalued..."
```

---

## Output Structure

```
2 - report output/$TICKER/
├── interim/
│   ├── analyst_type_1_v1.md ... analyst_type_6_v5.md  (30 analyst reports)
│   └── rd_review_type_1_v1.md ... rd_review_type_6_v5.md  (30 RD reviews)
├── ${TICKER}_webSource.json      # Gathered research sources
├── ${TICKER}_synthesis_raw.md    # RD's merged synthesis
└── ${TICKER}_memo_vF.md          # Final polished memo
```

---

## Cost & Performance

- **Tokens:** ~1.7M per ticker
- **Cost:** ~$13-15 with Claude Sonnet
- **Time:** ~15-20 minutes for full pipeline

---

## Key Features

### Evidence Hierarchy
Distinguishes primary sources (CEO interviews, Glassdoor, GitHub activity) from facts (SEC filings) and opinions (sell-side research). Minimum 3 primary sources required.

### Variant View Required
Every memo must articulate: "The market believes X. We believe Y. Here's why they're wrong." Only 19% of the VIC corpus does this well—TTT enforces it.

### Kill Conditions
Specific, falsifiable thresholds that would invalidate the thesis. Not "revenue declines" but "revenue growth falls below 5% for 2 consecutive quarters."

### Debate History
Analysts receive their prior iteration's thesis and RD feedback. They must explicitly respond: Accept / Reject / Partially Accept with evidence.

### IRR Hurdle
- Long positions require ≥15% expected IRR
- Short positions require ≥20-25% expected IRR
- Below hurdle = PASS regardless of qualitative conviction

---

## Project Structure

```
1 - program framework engine/
├── 0 - buyside_research_pipeline/    # Python code
│   ├── TickerToThesis.py             # Main entry point
│   ├── agent_runner.py               # Async API with retry/rate limiting
│   ├── config.py                     # Model config, investing types
│   ├── debate_tracker.py             # Tracks analyst <-> RD evolution
│   ├── prompt_loader.py              # Loads all prompt files
│   ├── report_saver.py               # Saves interim + final outputs
│   ├── providers/                    # AI provider implementations
│   └── requirements.txt
│
├── 1 - agent_role md prompt/         # Role definitions
│   ├── analyst_prompt.md             # Analyst identity & requirements
│   ├── rd_review_prompt.md           # RD critique framework
│   └── rd_synthesis_prompt_v2.md     # Final synthesis directive
│
├── 2 - agent_investing_type/         # The 6 philosophies
│   └── analyst_investing_type/
│       ├── 1-quality-compounders.md
│       ├── 2-imaginative-growth.md
│       ├── 3-fundamental-long-short.md
│       ├── 4-deep-value.md
│       ├── 5-event-driven.md
│       └── 6-macro-tactical.md
│
├── 3 - agent synthesis engine/       # Core constitution
│   └── buyside_memo_engine_v1.3.0.md # Scoring rubric, style taxonomy
│
└── 5 - final_readable_touch-up/      # Polish pass
    └── human_readable_output_engine.md
```

---

## Resume from Interruption

Pipeline saves state after each phase. If interrupted (API failure, credit depletion):

```bash
python resume_pipeline.py AAPL 3  # Resume from iteration 3
```

---

## Advanced Usage

```bash
# Synthesis only (uses existing v5 reports)
python run_synthesis_only.py AAPL

# Full synthesis on ALL reports (60 reports + source file)
python run_full_synthesis.py AAPL

# Disable dashboard UI
python TickerToThesis.py AAPL "thesis..." --no-gui
```

---

## Requirements

- Python 3.10+
- Anthropic API key (Claude Sonnet recommended)
- ~$15 per ticker for full pipeline

---

## License

MIT

---

## Acknowledgments

Built on learnings from 13,635 VIC memos. Inspired by the investment processes of Buffett, Munger, Druckenmiller, Klarman, and the Tiger Cubs.
