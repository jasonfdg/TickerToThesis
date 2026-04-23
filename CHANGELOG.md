# Changelog

Full history of changes to TickerToThesis_Original. Entries are grouped by session (one heading per working session); bullets describe the concrete change and files touched.

---

## Session 2026-04-23 — Provider routing overhaul + MRX materials + auto-maintenance scaffolding

### Provider routing swap (remove OpenAI, adopt OpenRouter for Kimi & Sonar)
- RD Reviews (all 6 types) moved from mixed `claude-cli/sonnet` + `gemini/gemini-2.5-pro` → `openrouter/moonshotai/kimi-k2`.
  - File: `1 - program framework engine/0 - buyside_research_pipeline/config.py` (`RD_REVIEW_PROVIDER_CONFIG`).
- RD Synthesis moved from `gemini/gemini-3-pro-preview` → `claude-cli/sonnet`.
  - File: `config.py` (`ROLE_PROVIDER_CONFIG["rd_synthesis"]`, `LIGHT_MODE_PROVIDER_CONFIG["rd_synthesis"]`).
- Source Summary moved from `openai/gpt-4o-mini` → `claude-cli/sonnet`.
  - File: `config.py` (`ROLE_PROVIDER_CONFIG["source_summary"]`, `LIGHT_MODE_PROVIDER_CONFIG["source_summary"]`).
- Source Scout moved from direct Perplexity API (`perplexity/sonar`) → `openrouter/perplexity/sonar`.
  - File: `config.py` (`ROLE_PROVIDER_CONFIG["source_scout"]`, `LIGHT_MODE_PROVIDER_CONFIG["source_scout"]`).
- Light-mode analysts 4-6 and RD reviews 4-6 moved from `openai/gpt-4o-mini` → `claude/sonnet` (API).
  - File: `config.py` (`LIGHT_MODE_ANALYST_CONFIG`, `LIGHT_MODE_RD_REVIEW_CONFIG`).
- Fallback chain (full): removed `gemini/gemini-3-pro-preview` and `openai/gpt-4o`; now `claude-cli/sonnet → claude/sonnet`.
  - File: `config.py` (`FALLBACK_CHAIN_FULL`).
- Fallback chain (light): removed `openai/gpt-4o-mini`; now `gemini/gemini-2.5-flash → claude/sonnet`.
  - File: `config.py` (`FALLBACK_CHAIN_LIGHT`, `LIGHT_MODE_FALLBACK_CHAIN`).
- Rate-limit dict trimmed: removed `openai` and `perplexity` entries; added `openrouter`.
  - File: `config.py` (`provider_rate_limits` default factory).
- Result: zero OpenAI references remain in `config.py`; Perplexity is only reached via OpenRouter. Auth relies on machine-level `OPENROUTER_KIMI_KEY` env var (confirmed set).

### MRX materials bundle
- Created `2 - report output/MRX/materials/` and copied 13 source PDFs from `OneDrive/ACM Research II/MRX/` (annual accounts, 5 Barclays notes, 4 Tegus expert interviews, investor day deck, Q4 earnings deck, short report).
- Copied 4 additional transcripts from `OneDrive/ACM Research II/MRX/` (two earnings calls, investor day, conference presentation).
- All 17 files renamed to match `materials_manager.py` prefix convention: `10k_`, `sellside_`, `expert_`, `presentation_`, `transcript_`.

### Documentation scaffolding (this entry)
- Appended `## Documentation Maintenance (project rule)` and `## Agent Workflow Rules` sections to `CLAUDE.md`, matching the insider-alpha maintenance protocol.
- Created `CHANGELOG.md` (this file).
- Added Project Stats marker block, auto-generated tree marker block, Known Limitations, Pending Work, and Done sections to `README.md`.
