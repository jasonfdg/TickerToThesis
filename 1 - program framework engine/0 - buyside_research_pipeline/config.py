"""
Pipeline Configuration
======================
Paths, constants, and settings for the TickerToThesis pipeline.
"""

from dataclasses import dataclass, field
import os
from pathlib import Path
from typing import Dict, List, Tuple

# =============================================================================
# Dashboard Configuration
# =============================================================================
DASHBOARD_PORT: int = int(os.getenv("TTT_DASHBOARD_PORT", "8765"))
DASHBOARD_ENABLED: bool = os.getenv("TTT_DASHBOARD_ENABLED", "true").lower() == "true"
DASHBOARD_HOST: str = os.getenv("TTT_DASHBOARD_HOST", "127.0.0.1")

# Base paths
PROJECT_ROOT = Path(__file__).resolve().parents[2]
FRAMEWORK_ENGINE = PROJECT_ROOT / "1 - program framework engine"
REPORT_OUTPUT = PROJECT_ROOT / "2 - report output"

# Prompt directories
AGENT_ROLE_DIR = FRAMEWORK_ENGINE / "1 - agent_role md prompt"
INVESTING_TYPE_DIR = FRAMEWORK_ENGINE / "2 - agent_investing_type md prompt" / "analyst_investing_type"
SYNTHESIS_ENGINE_DIR = FRAMEWORK_ENGINE / "3 - agent synthesis engine md prompt"
SOURCE_AGENT_DIR = FRAMEWORK_ENGINE / "4 - source_summary_agent md prompt"
HUMAN_READABLE_DIR = FRAMEWORK_ENGINE / "5 - final_readable_touch-up md prompt"
SOURCE_SCOUT_AGENT_DIR = FRAMEWORK_ENGINE / "6 - source_scout_agent md prompt"

# Prompt file paths
ANALYST_ROLE_PATH = AGENT_ROLE_DIR / "analyst_prompt.md"
RD_REVIEW_ROLE_PATH = AGENT_ROLE_DIR / "rd_review_prompt.md"
RD_SYNTHESIS_ROLE_PATH = AGENT_ROLE_DIR / "rd_synthesis_prompt_v2.md"  # Merged synthesis+polish
MEMO_ENGINE_PATH = SYNTHESIS_ENGINE_DIR / "buyside_memo_engine_v1.3.0.md"
SOURCE_SUMMARY_AGENT_PATH = SOURCE_AGENT_DIR / "source_summary_agent.md"
SOURCE_SUMMARY_AGENT_V2_PATH = SOURCE_AGENT_DIR / "source_summary_agent_v2.md"  # Slim, structured input
HUMAN_READABLE_ENGINE_PATH = HUMAN_READABLE_DIR / "human_readable_output_engine.md"
SOURCE_SCOUT_AGENT_PATH = SOURCE_SCOUT_AGENT_DIR / "source_scout_agent.md"

# Investing types mapping (1-6)
INVESTING_TYPES: Dict[int, Dict[str, str]] = {
    1: {
        "name": "Quality Compounders",
        "filename": "1-quality-compounders.md",
        "short_name": "quality_compounder",
    },
    2: {
        "name": "Imaginative Growth",
        "filename": "2-imaginative-growth.md",
        "short_name": "imaginative_growth",
    },
    3: {
        "name": "Fundamental Long-Short",
        "filename": "3-fundamental-long-short.md",
        "short_name": "fundamental_ls",
    },
    4: {
        "name": "Deep Value",
        "filename": "4-deep-value.md",
        "short_name": "deep_value",
    },
    5: {
        "name": "Event-Driven",
        "filename": "5-event-driven.md",
        "short_name": "event_driven",
    },
    6: {
        "name": "Macro-Tactical",
        "filename": "6-macro-tactical.md",
        "short_name": "macro_tactical",
    },
}


def get_investing_type_path(type_id: int) -> Path:
    """Get the full path for an investing type prompt file."""
    if type_id not in INVESTING_TYPES:
        raise ValueError(f"Invalid investing type ID: {type_id}. Must be 1-6.")
    return INVESTING_TYPE_DIR / INVESTING_TYPES[type_id]["filename"]


@dataclass
class PipelineConfig:
    """Configuration for the TickerToThesis pipeline."""

    # Model settings (legacy - used when multi_provider=False)
    model: str = "claude-sonnet-4-20250514"
    max_tokens: int = 16000
    temperature: float = 0.7

    # Multi-provider settings
    multi_provider: bool = True  # Enable multi-provider architecture
    parallel_execution: bool = True  # Enable parallel execution across providers

    # Pipeline mode: "full" or "light"
    # Light mode uses gpt-4o-mini for most agents (~$0.20/ticker vs ~$2.50)
    pipeline_mode: str = "full"

    # Pipeline settings
    num_iterations: int = 5  # Full debate cycle
    num_analysts: int = 6

    # Timeout settings (seconds)
    single_call_timeout: float = 300.0
    parallel_batch_timeout: float = 600.0

    # Retry settings (tuned for rate limits)
    max_retries: int = 5
    retry_base_delay: float = 30.0  # Longer base delay for rate limits
    retry_max_delay: float = 120.0

    # Logging
    verbose: bool = True
    log_dir: Path = field(default_factory=lambda: FRAMEWORK_ENGINE / "logs")

    # Rate limiting (requests per minute) - per provider
    rate_limit_rpm: int = 50

    # Provider-specific rate limits (parallel execution can exceed single-provider limits)
    provider_rate_limits: Dict[str, int] = field(default_factory=lambda: {
        "claude": 50,
        "openai": 60,
        "gemini": 60,
        "perplexity": 20,
    })

    def __post_init__(self):
        """Create necessary directories if they don't exist."""
        self.log_dir.mkdir(parents=True, exist_ok=True)

    @classmethod
    def from_dict(cls, config_dict: dict) -> "PipelineConfig":
        """Create a PipelineConfig from a dictionary."""
        return cls(**{k: v for k, v in config_dict.items() if k in cls.__dataclass_fields__})


# Multi-provider model configuration
# Analyst type -> (provider, model) mapping
# 3 Claude + 3 OpenAI (Gemini excluded from analyst roles)
# NOTE: Iteration 1 uses GPT-4o-mini for all analysts (see agent_runner.py)
ANALYST_PROVIDER_CONFIG: Dict[int, Dict[str, str]] = {
    1: {"provider": "claude-cli", "model": "sonnet"},  # Quality Compounders
    2: {"provider": "claude-cli", "model": "sonnet"},  # Imaginative Growth
    3: {"provider": "claude-cli", "model": "sonnet"},  # Fundamental L/S
    4: {"provider": "openai", "model": "gpt-4o"},      # Deep Value
    5: {"provider": "openai", "model": "gpt-4o"},      # Event-Driven
    6: {"provider": "openai", "model": "gpt-4o"},      # Macro-Tactical
}

# RD Review routing by analyst type (3 Claude + 3 Gemini)
# Types 1-3: Claude Sonnet (consistency with analyst provider)
# Types 4-6: Gemini 2.5 Pro (best RD quality from benchmark)
# Mixed providers enable 2x throughput via parallel rate limits
RD_REVIEW_PROVIDER_CONFIG: Dict[int, Dict[str, str]] = {
    1: {"provider": "claude-cli", "model": "sonnet"},       # Quality Compounders
    2: {"provider": "claude-cli", "model": "sonnet"},       # Imaginative Growth
    3: {"provider": "claude-cli", "model": "sonnet"},       # Fundamental L/S
    4: {"provider": "gemini", "model": "gemini-2.5-pro"},   # Deep Value
    5: {"provider": "gemini", "model": "gemini-2.5-pro"},   # Event-Driven
    6: {"provider": "gemini", "model": "gemini-2.5-pro"},   # Macro-Tactical
}

# Role -> (provider, model) mapping for non-analyst calls
ROLE_PROVIDER_CONFIG: Dict[str, Dict[str, str]] = {
    "rd_review": {"provider": "claude", "model": "sonnet"},       # Default for non-typed RD calls
    "rd_synthesis": {"provider": "gemini", "model": "gemini-2.5-pro"},  # Better synthesis quality
    "source_summary": {"provider": "openai", "model": "gpt-4o-mini"},   # Best JSON validity from benchmark
    "human_readable": {"provider": "claude", "model": "sonnet"},  # Preserve depth
    "source_scout": {"provider": "perplexity", "model": "sonar"}, # Real web search
}

# Light mode: Use gpt-4o-mini for most agents (cheap + fast)
# Exceptions: Perplexity for web search, Gemini for synthesis
# Cost: ~$0.20/ticker vs ~$2.50/ticker for full mode
LIGHT_MODE_PROVIDER_CONFIG: Dict[str, Dict[str, str]] = {
    "analyst": {"provider": "openai", "model": "gpt-4o-mini"},
    "rd_review": {"provider": "openai", "model": "gpt-4o-mini"},
    "source_summary": {"provider": "openai", "model": "gpt-4o-mini"},
    "human_readable": {"provider": "openai", "model": "gpt-4o-mini"},
    # Keep these on premium providers:
    "source_scout": {"provider": "perplexity", "model": "sonar"},
    "rd_synthesis": {"provider": "gemini", "model": "gemini-2.5-pro"},
}


# =============================================================================
# Provider Mode Configuration
# =============================================================================
# "api" = use API calls (default, costs per token)
# "cli" = use Claude Code CLI (requires Max subscription, unlimited usage)
#
# Set via environment variable: export PROVIDER_MODE=cli
# Or modify directly here for persistent change
PROVIDER_MODE: str = os.getenv("PROVIDER_MODE", "api")


# Component-level provider overrides
# Allows swapping any component to a different provider/model
# Format: {"component_name": {"provider": "...", "model": "..."}}
#
# Component naming convention:
#   - analyst_1, analyst_2, ..., analyst_6 (by investing type)
#   - rd_review_1, rd_review_2, ..., rd_review_6 (by investing type)
#   - rd_synthesis, source_summary, source_scout, etc. (by role)
#
# Examples:
#   COMPONENT_OVERRIDES = {
#       "analyst_1": {"provider": "claude-cli", "model": "sonnet"},
#       "rd_synthesis": {"provider": "claude-cli", "model": "opus"},
#   }
COMPONENT_OVERRIDES: Dict[str, Dict[str, str]] = {
    # Uncomment to override specific components:
    # "analyst_1": {"provider": "claude-cli", "model": "sonnet"},
    # "analyst_2": {"provider": "claude-cli", "model": "sonnet"},
    # "rd_synthesis": {"provider": "claude-cli", "model": "opus"},
}


def get_effective_provider(
    component: str,
    iteration: int = 1,
    pipeline_mode: str | None = None
) -> Tuple[str, str]:
    """Get provider/model for a component, respecting overrides and mode.

    Priority order:
    1. Explicit COMPONENT_OVERRIDES entry
    2. Light mode config (if pipeline_mode == "light")
    3. PROVIDER_MODE substitution (api->cli for Claude providers)
    4. Default routing from ANALYST_PROVIDER_CONFIG / ROLE_PROVIDER_CONFIG

    Args:
        component: Component identifier (e.g., "analyst_1", "rd_synthesis")
        iteration: Pipeline iteration (affects analyst routing in iteration 1)
        pipeline_mode: "full" or "light" - if None, uses current global mode.
                       Light mode uses gpt-4o-mini for most agents.

    Returns:
        Tuple of (provider_type, model)
    """
    mode = os.getenv("PROVIDER_MODE", PROVIDER_MODE)
    effective_pipeline_mode = pipeline_mode if pipeline_mode is not None else _current_pipeline_mode

    # 1. Check for explicit override
    if component in COMPONENT_OVERRIDES:
        override = COMPONENT_OVERRIDES[component]
        return override["provider"], override["model"]

    # 2. Light mode: check LIGHT_MODE_PROVIDER_CONFIG first
    if effective_pipeline_mode == "light":
        # Determine component type for light mode lookup
        if component.startswith("analyst_"):
            light_config = LIGHT_MODE_PROVIDER_CONFIG.get("analyst")
        elif component.startswith("rd_review_"):
            light_config = LIGHT_MODE_PROVIDER_CONFIG.get("rd_review")
        else:
            light_config = LIGHT_MODE_PROVIDER_CONFIG.get(component)

        if light_config:
            return light_config["provider"], light_config["model"]

    # 3. Determine default provider based on component type (full mode)
    default_provider = None
    default_model = None

    # Parse component to determine type
    if component.startswith("analyst_"):
        type_id = int(component.split("_")[1])
        # Iteration 1 uses GPT-4o-mini for all analysts
        if iteration == 1:
            default_provider = "openai"
            default_model = "gpt-4o-mini"
        else:
            config = ANALYST_PROVIDER_CONFIG.get(type_id, {})
            default_provider = config.get("provider", "claude")
            default_model = config.get("model", "sonnet")
    elif component.startswith("rd_review_"):
        type_id = int(component.split("_")[2])
        config = RD_REVIEW_PROVIDER_CONFIG.get(type_id, {})
        default_provider = config.get("provider", "claude")
        default_model = config.get("model", "sonnet")
    else:
        # Role-based component (rd_synthesis, source_summary, etc.)
        config = ROLE_PROVIDER_CONFIG.get(component, {})
        default_provider = config.get("provider", "claude")
        default_model = config.get("model", "sonnet")

    # 4. Apply mode-based substitution
    # If mode is "cli" and default provider is "claude", use "claude-cli" instead
    if mode == "cli" and default_provider == "claude":
        return "claude-cli", default_model

    return default_provider, default_model


def _get_next_version(ticker: str) -> int:
    """Find the next available version number for a ticker."""
    import re
    pattern = re.compile(rf"^{ticker}_V(\d+)_")
    max_version = 0

    if REPORT_OUTPUT.exists():
        for folder in REPORT_OUTPUT.iterdir():
            if folder.is_dir():
                match = pattern.match(folder.name)
                if match:
                    version = int(match.group(1))
                    max_version = max(max_version, version)

    return max_version + 1


def _get_current_date() -> str:
    """Get current date in YYYY-MM-DD format."""
    from datetime import datetime
    return datetime.now().strftime("%Y-%m-%d")


# Cache for output directory to ensure consistency within a run
_output_dir_cache: Dict[str, Path] = {}

# Current pipeline mode for path functions (set via set_pipeline_mode())
_current_pipeline_mode: str = "full"


def set_pipeline_mode(mode: str) -> None:
    """Set the current pipeline mode for path functions.

    Args:
        mode: "full" or "light"
    """
    global _current_pipeline_mode
    if mode not in ("full", "light"):
        raise ValueError(f"Invalid pipeline mode: {mode}. Must be 'full' or 'light'.")
    _current_pipeline_mode = mode


def get_pipeline_mode() -> str:
    """Get the current pipeline mode."""
    return _current_pipeline_mode


def _find_todays_folder(ticker: str, mode: str = "full") -> Path | None:
    """Find an existing folder for this ticker with today's date.

    This ensures consistency even if the cache is not shared across imports.

    Args:
        ticker: Stock ticker symbol
        mode: Pipeline mode ("full" or "light") - light mode folders have "-light" suffix
    """
    import re
    date_str = _get_current_date()
    suffix = "-light" if mode == "light" else ""
    pattern = re.compile(rf"^{ticker}_V(\d+)_{date_str}{suffix}$")

    if not REPORT_OUTPUT.exists():
        return None

    # Find highest version folder for today
    best_folder = None
    best_version = 0

    for folder in REPORT_OUTPUT.iterdir():
        if folder.is_dir():
            match = pattern.match(folder.name)
            if match:
                version = int(match.group(1))
                if version > best_version:
                    best_version = version
                    best_folder = folder

    return best_folder


def get_output_dir(ticker: str, create_new: bool = False, mode: str | None = None) -> Path:
    """Get the output directory for a specific ticker.

    Naming convention: TICKER_V#_YYYY-MM-DD[-light]

    Args:
        ticker: Stock ticker symbol
        create_new: If True, always create a new versioned directory.
                   If False, return existing directory for today or create new.
        mode: Pipeline mode ("full" or "light") - if None, uses current global mode.
              Light mode appends "-light" suffix.
    """
    ticker = ticker.upper()
    effective_mode = mode if mode is not None else _current_pipeline_mode
    cache_key = f"{ticker}_{effective_mode}"

    # Return cached directory if available (ensures consistency within a run)
    if cache_key in _output_dir_cache and not create_new:
        return _output_dir_cache[cache_key]

    # Check for existing folder with today's date (handles cache inconsistency across imports)
    if not create_new:
        existing_folder = _find_todays_folder(ticker, effective_mode)
        if existing_folder:
            _output_dir_cache[cache_key] = existing_folder
            return existing_folder

    # Create new versioned folder
    version = _get_next_version(ticker)
    date_str = _get_current_date()
    suffix = "-light" if effective_mode == "light" else ""
    dir_name = f"{ticker}_V{version}_{date_str}{suffix}"
    output_dir = REPORT_OUTPUT / dir_name
    output_dir.mkdir(parents=True, exist_ok=True)
    _output_dir_cache[cache_key] = output_dir

    return output_dir


def get_latest_output_dir(ticker: str) -> Path:
    """Get the most recent output directory for a ticker (if exists).

    Returns the newest versioned directory or creates a new one.
    """
    import re
    ticker = ticker.upper()
    pattern = re.compile(rf"^{ticker}_V(\d+)_")
    latest_dir = None
    max_version = 0

    if REPORT_OUTPUT.exists():
        for folder in REPORT_OUTPUT.iterdir():
            if folder.is_dir():
                match = pattern.match(folder.name)
                if match:
                    version = int(match.group(1))
                    if version > max_version:
                        max_version = version
                        latest_dir = folder

    if latest_dir:
        return latest_dir

    # No existing directory, create new one
    return get_output_dir(ticker, create_new=True)


def get_interim_dir(ticker: str) -> Path:
    """Get the interim reports directory for a specific ticker."""
    interim_dir = get_output_dir(ticker) / "interim"
    interim_dir.mkdir(parents=True, exist_ok=True)
    return interim_dir


def get_source_file_path(ticker: str) -> Path:
    """Get the path to the source file for a specific ticker.

    Now stored in interim/ folder.
    """
    return get_interim_dir(ticker) / f"{ticker}_webSource.json"


def get_pipeline_state_path(ticker: str) -> Path:
    """Get the path to the pipeline state file for a ticker.

    Now stored in interim/ folder.
    """
    return get_interim_dir(ticker) / f"{ticker}_pipeline_state.json"


def get_initial_scout_path(ticker: str) -> Path:
    """Get the path to the genesis/initial source scout report."""
    return get_interim_dir(ticker) / "initial_scout.md"


def get_final_memo_path(ticker: str, lang: str = "EN") -> Path:
    """Get the path to the final memo for a ticker.

    Args:
        ticker: Stock ticker symbol
        lang: Language code ("EN" or "CN")

    Naming convention: TICKER_memo_LANG.md (e.g., AAPL_memo_EN.md)
    """
    ticker = ticker.upper()
    return get_output_dir(ticker) / f"{ticker}_memo_{lang}.md"


def get_final_pdf_path(ticker: str, lang: str = "EN") -> Path:
    """Get the path to the final PDF for a ticker.

    Args:
        ticker: Stock ticker symbol
        lang: Language code ("EN" or "CN")

    Naming convention: TICKER_memo_LANG.pdf (e.g., AAPL_memo_EN.pdf)
    """
    ticker = ticker.upper()
    return get_output_dir(ticker) / f"{ticker}_memo_{lang}.pdf"


def get_source_scout_path(ticker: str, iteration: int) -> Path:
    """Get the path to the source scout report for a specific iteration."""
    return get_interim_dir(ticker) / f"source_scout_v{iteration}.md"


def clear_output_dir_cache() -> None:
    """Clear the output directory cache. Call at start of new pipeline run."""
    global _output_dir_cache
    _output_dir_cache = {}


def migrate_output_folders() -> Dict[str, str]:
    """Migrate existing output folders to new naming convention.

    Converts folders from:
        TICKER/ -> TICKER_V1_YYYY-MM-DD/

    And files from:
        TICKER_memo_vF.md -> TICKER_memo_vF_YYYY-MM-DD.md

    Returns:
        Dict mapping old folder names to new folder names
    """
    import re
    import os
    from datetime import datetime

    migrations = {}
    versioned_pattern = re.compile(r"^[A-Z]+_V\d+_\d{4}-\d{2}-\d{2}$")
    ticker_pattern = re.compile(r"^[A-Z]{1,6}$")  # Simple ticker: 1-6 uppercase letters

    if not REPORT_OUTPUT.exists():
        return migrations

    for folder in list(REPORT_OUTPUT.iterdir()):
        if not folder.is_dir():
            continue

        folder_name = folder.name

        # Skip already migrated folders
        if versioned_pattern.match(folder_name):
            continue

        # Skip non-ticker folders (like 'Other')
        if not ticker_pattern.match(folder_name):
            continue

        ticker = folder_name.upper()

        # Get folder modification date
        try:
            mtime = folder.stat().st_mtime
            date_str = datetime.fromtimestamp(mtime).strftime("%Y-%m-%d")
        except Exception:
            date_str = datetime.now().strftime("%Y-%m-%d")

        # Create new folder name
        new_folder_name = f"{ticker}_V1_{date_str}"
        new_folder_path = REPORT_OUTPUT / new_folder_name

        # Check if new name already exists
        if new_folder_path.exists():
            # Increment version
            version = 2
            while (REPORT_OUTPUT / f"{ticker}_V{version}_{date_str}").exists():
                version += 1
            new_folder_name = f"{ticker}_V{version}_{date_str}"
            new_folder_path = REPORT_OUTPUT / new_folder_name

        # Rename folder
        try:
            folder.rename(new_folder_path)
            migrations[folder_name] = new_folder_name

            # Rename files inside the folder
            _migrate_folder_files(new_folder_path, ticker, date_str)

        except Exception as e:
            print(f"Failed to migrate {folder_name}: {e}")

    return migrations


def _migrate_folder_files(folder: Path, ticker: str, date_str: str) -> None:
    """Migrate files within a folder to new naming convention."""
    import re

    # Pattern for old memo file: TICKER_memo_vF.md
    old_memo_pattern = re.compile(rf"^{ticker}_memo_vF\.md$")

    for file_path in folder.iterdir():
        if not file_path.is_file():
            continue

        # Migrate memo file
        if old_memo_pattern.match(file_path.name):
            new_name = f"{ticker}_memo_vF_{date_str}.md"
            new_path = folder / new_name
            try:
                file_path.rename(new_path)
            except Exception as e:
                print(f"Failed to rename {file_path.name}: {e}")
