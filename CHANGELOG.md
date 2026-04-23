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

### Source scout actually routes through OpenRouter now (fix for 401 at genesis)
Previous provider-routing swap above declared source_scout should use `openrouter/perplexity/sonar` in `config.py`, but three code paths still hit Perplexity directly — causing a `401 Unauthorized` from `api.perplexity.ai` on today's MRX run, followed by a silent fallback to `claude-cli/sonnet`.

- **New: `providers/openrouter.py`** — `OpenRouterProvider(BaseProvider)` modeled after `providers/perplexity.py`. POSTs to `https://openrouter.ai/api/v1/chat/completions` with `HTTP-Referer` + `X-Title` headers. Reads `OPENROUTER_KIMI_KEY` (falls back to `OPENROUTER_API_KEY`). Preserves Sonar URL citations from `message.annotations[].url_citation` and appends them as a `## Sources` block so downstream source extraction still works. Raises `ProviderRateLimitError` on 429; re-raises other HTTP errors with status + body for visibility.
- **`providers/__init__.py`** — imported `OpenRouterProvider`, added it to `__all__` and the `ProviderType` enum (`"openrouter"`), added an `elif provider_type == "openrouter":` branch in `ProviderFactory.get_provider()`. Synced four stale `ROLE_PROVIDERS` defaults (consulted when `AgentCall` is built without explicit provider) with `config.py`'s authoritative `ROLE_PROVIDER_CONFIG` / `RD_REVIEW_PROVIDER_CONFIG`: `RD_REVIEW → openrouter/moonshotai/kimi-k2`, `RD_SYNTHESIS → claude-cli/sonnet`, `SOURCE_SUMMARY → claude-cli/sonnet`, `SOURCE_SCOUT → openrouter/perplexity/sonar`. Updated module docstring to reflect current routing.
- **`TickerToThesis.py` `_bootstrap_thesis()`** — removed hardcoded `provider="perplexity", model="sonar"` from the genesis `AgentCall`, letting `agent_runner._assign_provider_model()` route via config. Deleted the bare `except Exception` that was swallowing the 401. On `is_success=False`, now raises `RuntimeError` instead of warning and returning `""`. No more silent-degraded bootstrap.
- **`TickerToThesis.py` `_run_source_scout()`** — deleted the hardcoded `fallback_providers = [("perplexity", "sonar"), ("gemini", "gemini-2.0-flash"), ("claude", "sonnet")]` list and the surrounding for-loop. Replaced with a single config-driven `AgentCall` + a single `run_single`. Raises `RuntimeError` on failure. Fallback to knowledge-only models was masking the real provider failure and producing memos with degraded evidence; explicit user request was to fail loudly instead.
- **`.env.example`** — added `OPENROUTER_KIMI_KEY=` placeholder with a note that `OPENROUTER_API_KEY` is accepted as fallback. Retargeted the header comment to cover all API keys (Anthropic + OpenRouter + optional Gemini), not just Anthropic.

**Verification performed this session:**
- `python -m py_compile providers/openrouter.py providers/__init__.py TickerToThesis.py` → clean.
- Live call: `OpenRouterProvider.generate(model="perplexity/sonar", ...)` returned real Marex Q4 2025 earnings data with 5 URL citations — confirming auth and citation preservation both work end-to-end.
- `AgentCall(role=SOURCE_SCOUT)` with no explicit provider resolves to `('openrouter', 'perplexity/sonar')` — confirming the config-driven path is wired correctly through `_assign_provider_model()` and `get_effective_provider()`.
