"""
Pipeline Configuration
======================
Paths, constants, and settings for the TickerToThesis pipeline.
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List

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
ANALYST_PROVIDER_CONFIG: Dict[int, Dict[str, str]] = {
    1: {"provider": "claude", "model": "sonnet"},      # Quality Compounders
    2: {"provider": "claude", "model": "sonnet"},      # Imaginative Growth
    3: {"provider": "openai", "model": "gpt-4o"},      # Fundamental L/S
    4: {"provider": "openai", "model": "gpt-4o"},      # Deep Value
    5: {"provider": "gemini", "model": "gemini-2.5-pro"},  # Event-Driven
    6: {"provider": "gemini", "model": "gemini-2.5-pro"},  # Macro-Tactical
}

# Role -> (provider, model) mapping for non-analyst calls
ROLE_PROVIDER_CONFIG: Dict[str, Dict[str, str]] = {
    "rd_review": {"provider": "claude", "model": "sonnet"},       # Consistent critique
    "rd_synthesis": {"provider": "gemini", "model": "gemini-2.5-pro"},  # Better synthesis quality
    "source_summary": {"provider": "claude", "model": "haiku"},   # Fast, cheap
    "human_readable": {"provider": "claude", "model": "sonnet"},  # Preserve depth
    "source_scout": {"provider": "perplexity", "model": "sonar"}, # Real web search
}


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


def get_output_dir(ticker: str, create_new: bool = False) -> Path:
    """Get the output directory for a specific ticker.

    Naming convention: TICKER_V#_YYYY-MM-DD

    Args:
        ticker: Stock ticker symbol
        create_new: If True, always create a new versioned directory.
                   If False, return the most recent existing directory or create new.
    """
    ticker = ticker.upper()

    # Return cached directory if available (ensures consistency within a run)
    if ticker in _output_dir_cache and not create_new:
        return _output_dir_cache[ticker]

    if create_new or ticker not in _output_dir_cache:
        version = _get_next_version(ticker)
        date_str = _get_current_date()
        dir_name = f"{ticker}_V{version}_{date_str}"
        output_dir = REPORT_OUTPUT / dir_name
        output_dir.mkdir(parents=True, exist_ok=True)
        _output_dir_cache[ticker] = output_dir
    else:
        output_dir = _output_dir_cache[ticker]

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
    """Get the path to the source file for a specific ticker."""
    return get_output_dir(ticker) / f"{ticker}_webSource.json"


def get_synthesis_raw_path(ticker: str) -> Path:
    """Get the path to the raw synthesis output for a ticker."""
    return get_output_dir(ticker) / f"{ticker}_synthesis_raw.md"


def get_final_memo_path(ticker: str) -> Path:
    """Get the path to the final polished memo for a ticker.

    Naming convention: TICKER_memo_vF_YYYY-MM-DD.md
    """
    date_str = _get_current_date()
    return get_output_dir(ticker) / f"{ticker}_memo_vF_{date_str}.md"


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
