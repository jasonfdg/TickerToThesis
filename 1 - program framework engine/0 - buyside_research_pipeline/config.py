"""
Pipeline Configuration
======================
Paths, constants, and settings for the TickerToThesis pipeline.
"""

from dataclasses import dataclass, field
import os
from pathlib import Path
from typing import Dict, List, Tuple, Optional

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
HUMAN_READABLE_DIR = FRAMEWORK_ENGINE / "5 - final_readable_touch-up md prompt"
SOURCE_SCOUT_AGENT_DIR = FRAMEWORK_ENGINE / "6 - source_scout_agent md prompt"

# Prompt file paths
ANALYST_ROLE_PATH = AGENT_ROLE_DIR / "analyst_prompt.md"
RD_REVIEW_ROLE_PATH = AGENT_ROLE_DIR / "rd_review_prompt.md"
RD_SYNTHESIS_ROLE_PATH = AGENT_ROLE_DIR / "rd_synthesis_prompt_v2.md"  # Merged synthesis+polish
MEMO_ENGINE_PATH = SYNTHESIS_ENGINE_DIR / "buyside_memo_engine_v1.3.0.md"
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

# Disable specific analyst types by ID. Disabled analysts are skipped entirely.
# Set via CLI: --disable-analysts 5,6
DISABLED_ANALYSTS: set = set()


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
    # Light mode uses Gemini Flash + Claude Sonnet API for most agents
    pipeline_mode: str = "full"

    # Pipeline settings
    num_iterations: int = 5  # Full debate cycle
    num_analysts: int = 6

    # Timeout settings (seconds)
    single_call_timeout: float = 1800.0   # 30 minutes per call
    parallel_batch_timeout: float = 3600.0  # 60 minutes for batch (6x claude-cli)

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
        "gemini": 60,
        "openrouter": 60,
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
# All 6 analysts: Claude CLI Sonnet (Max subscription, no API cost)
ANALYST_PROVIDER_CONFIG: Dict[int, Dict[str, str]] = {
    1: {"provider": "claude-cli", "model": "sonnet"},  # Quality Compounders
    2: {"provider": "claude-cli", "model": "sonnet"},  # Imaginative Growth
    3: {"provider": "claude-cli", "model": "sonnet"},  # Fundamental L/S
    4: {"provider": "claude-cli", "model": "sonnet"},  # Deep Value
    5: {"provider": "claude-cli", "model": "sonnet"},  # Event-Driven
    6: {"provider": "claude-cli", "model": "sonnet"},  # Macro-Tactical
}

# Iteration 1 analyst routing: all Claude CLI Sonnet
ITERATION_1_ANALYST_CONFIG: Dict[int, Dict[str, str]] = {
    1: {"provider": "claude-cli", "model": "sonnet"},
    2: {"provider": "claude-cli", "model": "sonnet"},
    3: {"provider": "claude-cli", "model": "sonnet"},
    4: {"provider": "claude-cli", "model": "sonnet"},
    5: {"provider": "claude-cli", "model": "sonnet"},
    6: {"provider": "claude-cli", "model": "sonnet"},
}

# RD Review routing by analyst type
# Types 1-3: Claude CLI Sonnet (consistency with analyst provider)
# Types 4-6: Gemini 2.5 Pro (independent adversarial voice via different model)
# Mixed providers enable 2x throughput via parallel rate limits
RD_REVIEW_PROVIDER_CONFIG: Dict[int, Dict[str, str]] = {
    1: {"provider": "openrouter", "model": "moonshotai/kimi-k2"},   # Quality Compounders
    2: {"provider": "openrouter", "model": "moonshotai/kimi-k2"},   # Imaginative Growth
    3: {"provider": "openrouter", "model": "moonshotai/kimi-k2"},   # Fundamental L/S
    4: {"provider": "openrouter", "model": "moonshotai/kimi-k2"},   # Deep Value
    5: {"provider": "openrouter", "model": "moonshotai/kimi-k2"},   # Event-Driven
    6: {"provider": "openrouter", "model": "moonshotai/kimi-k2"},   # Macro-Tactical
}

# Role -> (provider, model) mapping for non-analyst calls
ROLE_PROVIDER_CONFIG: Dict[str, Dict[str, str]] = {
    "rd_review": {"provider": "openrouter", "model": "moonshotai/kimi-k2"},  # Kimi K2 for cross-model RD critique
    "rd_synthesis": {"provider": "claude-cli", "model": "sonnet"},           # Claude Sonnet via CLI for synthesis
    "source_summary": {"provider": "claude-cli", "model": "sonnet"},         # Claude Sonnet for JSON extraction
    "human_readable": {"provider": "claude", "model": "sonnet"},             # Preserve depth
    "source_scout": {"provider": "openrouter", "model": "perplexity/sonar"}, # Perplexity Sonar via OpenRouter
}

# Light mode: Split across 2 fast providers for parallel execution
# Gemini Flash (1-3) + Claude Sonnet API (4-6)
# Cost kept low by preferring Gemini Flash (1-3) and Claude Sonnet API (4-6)
LIGHT_MODE_ANALYST_CONFIG: Dict[int, Dict[str, str]] = {
    1: {"provider": "gemini", "model": "gemini-2.5-flash"},
    2: {"provider": "gemini", "model": "gemini-2.5-flash"},
    3: {"provider": "gemini", "model": "gemini-2.5-flash"},
    4: {"provider": "claude", "model": "sonnet"},
    5: {"provider": "claude", "model": "sonnet"},
    6: {"provider": "claude", "model": "sonnet"},
}

LIGHT_MODE_RD_REVIEW_CONFIG: Dict[int, Dict[str, str]] = {
    1: {"provider": "gemini", "model": "gemini-2.5-flash"},
    2: {"provider": "gemini", "model": "gemini-2.5-flash"},
    3: {"provider": "gemini", "model": "gemini-2.5-flash"},
    4: {"provider": "claude", "model": "sonnet"},
    5: {"provider": "claude", "model": "sonnet"},
    6: {"provider": "claude", "model": "sonnet"},
}

# Keep role-based config for non-analyst/RD components
LIGHT_MODE_PROVIDER_CONFIG: Dict[str, Dict[str, str]] = {
    "source_summary": {"provider": "claude-cli", "model": "sonnet"},
    "human_readable": {"provider": "gemini", "model": "gemini-2.5-flash"},
    "source_scout": {"provider": "openrouter", "model": "perplexity/sonar"},
    "rd_synthesis": {"provider": "claude-cli", "model": "sonnet"},
}

# Light mode fallback chain (used when primary provider is rate-limited)
# Loops back with increasing backoff: 15s → 30s → 60s
LIGHT_MODE_FALLBACK_CHAIN: List[Tuple[str, str]] = [
    ("gemini", "gemini-2.5-flash"),
    ("claude", "sonnet"),  # Claude Sonnet API as fallback (paid, pay-per-token)
]

# Light mode timing optimizations (faster providers need less delay)
LIGHT_MODE_DELAYS: Dict[str, float] = {
    "stagger_delay": 0.5,      # Seconds between parallel calls (vs 2.0s full mode)
    "loop_wait_base": 15.0,    # Base wait when all providers rate-limited (vs 30s)
    "loop_wait_max": 60.0,     # Max wait during fallback loop (vs 120s)
    "sequential_delay": 2.0,   # Delay between sequential calls (vs 5.0s)
}


# =============================================================================
# Randomized 2-2-2 Provider Assignment
# =============================================================================

# Full mode models for randomization (all 6 = claude-cli/sonnet)
FULL_MODE_PROVIDERS: List[Tuple[str, str]] = [
    ("claude-cli", "sonnet"),
    ("claude-cli", "sonnet"),
    ("claude-cli", "sonnet"),
    ("claude-cli", "sonnet"),
    ("claude-cli", "sonnet"),
    ("claude-cli", "sonnet"),
]

# Light mode models for randomization (all 6 = claude-cli/sonnet)
LIGHT_MODE_PROVIDERS: List[Tuple[str, str]] = [
    ("claude-cli", "sonnet"),
    ("claude-cli", "sonnet"),
    ("claude-cli", "sonnet"),
    ("claude-cli", "sonnet"),
    ("claude-cli", "sonnet"),
    ("claude-cli", "sonnet"),
]

# Fallback chain order (full mode): claude-cli sonnet → claude API sonnet
FALLBACK_CHAIN_FULL: List[Tuple[str, str]] = [
    ("claude-cli", "sonnet"),
    ("claude", "sonnet"),  # Claude Sonnet API as last resort (paid, pay-per-token)
]

# Fallback chain order (light mode): claude-cli → gemini flash → claude API sonnet
FALLBACK_CHAIN_LIGHT: List[Tuple[str, str]] = [
    ("claude-cli", "sonnet"),
    ("gemini", "gemini-2.5-flash"),
    ("claude", "sonnet"),  # Claude Sonnet API as last resort (paid, pay-per-token)
]


def generate_random_assignment(
    iteration: int,
    role: str = "analyst",
    pipeline_mode: str = "full",
    seed: Optional[int] = None
) -> Dict[int, Dict[str, str]]:
    """Generate a random 2-2-2 provider assignment for an iteration.

    Args:
        iteration: Iteration number (used as part of seed for reproducibility)
        role: "analyst" or "rd_review" (different shuffles)
        pipeline_mode: "full" or "light"
        seed: Optional seed override for testing

    Returns:
        Dict mapping type_id (1-6) to {"provider": str, "model": str}
    """
    import random as rand

    # Create deterministic but different seed for each iteration/role combo
    # This ensures reproducibility while giving different shuffles
    effective_seed = seed if seed is not None else hash((iteration, role)) % (2**31)
    rand.seed(effective_seed)

    providers = FULL_MODE_PROVIDERS if pipeline_mode == "full" else LIGHT_MODE_PROVIDERS
    shuffled = providers.copy()
    rand.shuffle(shuffled)

    return {
        i + 1: {"provider": shuffled[i][0], "model": shuffled[i][1]}
        for i in range(6)
    }


# Cache for iteration assignments (cleared on new pipeline run)
_iteration_assignments: Dict[Tuple[int, str, str], Dict[int, Dict[str, str]]] = {}


def get_randomized_provider(
    type_id: int,
    iteration: int,
    role: str = "analyst",
    pipeline_mode: Optional[str] = None
) -> Tuple[str, str]:
    """Get provider/model for a type_id using randomized 2-2-2 assignment.

    Args:
        type_id: Analyst/RD type (1-6)
        iteration: Pipeline iteration number
        role: "analyst" or "rd_review"
        pipeline_mode: "full" or "light" (defaults to global mode)

    Returns:
        Tuple of (provider, model)
    """
    mode = pipeline_mode or get_pipeline_mode()
    cache_key = (iteration, role, mode)

    if cache_key not in _iteration_assignments:
        _iteration_assignments[cache_key] = generate_random_assignment(
            iteration, role, mode
        )

    assignment = _iteration_assignments[cache_key][type_id]
    return assignment["provider"], assignment["model"]


def clear_iteration_assignments() -> None:
    """Clear cached assignments. Call at start of new pipeline run."""
    global _iteration_assignments
    _iteration_assignments = {}


def get_fallback_chain(pipeline_mode: Optional[str] = None) -> List[Tuple[str, str]]:
    """Get the fallback chain for the current pipeline mode."""
    mode = pipeline_mode or get_pipeline_mode()
    return FALLBACK_CHAIN_LIGHT if mode == "light" else FALLBACK_CHAIN_FULL


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
                       Light mode uses Gemini Flash + Claude Sonnet API for most agents.

    Returns:
        Tuple of (provider_type, model)
    """
    mode = os.getenv("PROVIDER_MODE", PROVIDER_MODE)
    effective_pipeline_mode = pipeline_mode if pipeline_mode is not None else _current_pipeline_mode

    # 1. Check for explicit override
    if component in COMPONENT_OVERRIDES:
        override = COMPONENT_OVERRIDES[component]
        return override["provider"], override["model"]

    # 2. Light mode: use per-type configs for analysts/RD reviews
    if effective_pipeline_mode == "light":
        if component.startswith("analyst_"):
            type_id = int(component.split("_")[1])
            config = LIGHT_MODE_ANALYST_CONFIG.get(type_id)
            if config:
                return config["provider"], config["model"]
        elif component.startswith("rd_review_"):
            type_id = int(component.split("_")[2])
            config = LIGHT_MODE_RD_REVIEW_CONFIG.get(type_id)
            if config:
                return config["provider"], config["model"]
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
        # Iteration 1 uses split providers for parallelism
        if iteration == 1:
            config = ITERATION_1_ANALYST_CONFIG.get(type_id, {})
            default_provider = config.get("provider", "gemini")
            default_model = config.get("model", "gemini-2.5-flash-lite")
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
    """Find the next available version number for a ticker.

    Scans REPORT_OUTPUT/{TICKER}/ for V{n}_{date} subfolders.
    """
    import re
    pattern = re.compile(r"^V(\d+)_")
    max_version = 0

    ticker_root = REPORT_OUTPUT / ticker
    if ticker_root.exists():
        for folder in ticker_root.iterdir():
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
    Scans REPORT_OUTPUT/{TICKER}/ for V{n}_{date}[-light] subfolders.

    Args:
        ticker: Stock ticker symbol
        mode: Pipeline mode ("full" or "light") - light mode folders have "-light" suffix
    """
    import re
    date_str = _get_current_date()
    suffix = "-light" if mode == "light" else ""
    pattern = re.compile(rf"^V(\d+)_{date_str}{suffix}$")

    ticker_root = REPORT_OUTPUT / ticker
    if not ticker_root.exists():
        return None

    # Find highest version folder for today
    best_folder = None
    best_version = 0

    for folder in ticker_root.iterdir():
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

    # Create new versioned folder nested inside ticker folder:
    # REPORT_OUTPUT/{TICKER}/V{n}_{date}[-light]/
    version = _get_next_version(ticker)
    date_str = _get_current_date()
    suffix = "-light" if effective_mode == "light" else ""
    dir_name = f"V{version}_{date_str}{suffix}"
    output_dir = REPORT_OUTPUT / ticker / dir_name
    output_dir.mkdir(parents=True, exist_ok=True)
    _output_dir_cache[cache_key] = output_dir

    return output_dir


def get_latest_output_dir(ticker: str) -> Path:
    """Get the most recent output directory for a ticker (if exists).

    Returns the newest versioned directory (nested under REPORT_OUTPUT/{TICKER}/)
    or creates a new one.
    """
    import re
    ticker = ticker.upper()
    pattern = re.compile(r"^V(\d+)_")
    latest_dir = None
    max_version = 0

    ticker_root = REPORT_OUTPUT / ticker
    if ticker_root.exists():
        for folder in ticker_root.iterdir():
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


def get_materials_dir(ticker: str) -> Path:
    """Get the shared materials directory for external PDF documents.

    Materials live at ticker level: REPORT_OUTPUT/{TICKER}/materials/
    Shared across all versions of the ticker's output folder.
    """
    materials_dir = REPORT_OUTPUT / ticker.upper() / "materials"
    materials_dir.mkdir(parents=True, exist_ok=True)
    return materials_dir
