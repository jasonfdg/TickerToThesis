"""
Pipeline Configuration
======================
Paths, constants, and settings for the TickerToThesis pipeline.
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List

# Base paths
PROJECT_ROOT = Path("/Users/chaukam/developer/Analyst_framework_buildout")
FRAMEWORK_ENGINE = PROJECT_ROOT / "1 - program framework engine"
REPORT_OUTPUT = PROJECT_ROOT / "2 - report output"

# Prompt directories
AGENT_ROLE_DIR = FRAMEWORK_ENGINE / "1 - agent_role md prompt"
INVESTING_TYPE_DIR = FRAMEWORK_ENGINE / "2 - agent_investing_type md prompt" / "analyst_investing_type"
SYNTHESIS_ENGINE_DIR = FRAMEWORK_ENGINE / "3 - agent synthesis engine md prompt"
SOURCE_AGENT_DIR = FRAMEWORK_ENGINE / "4 - source_summary_agent md prompt"
HUMAN_READABLE_DIR = FRAMEWORK_ENGINE / "5 - final_readable_touch-up md prompt"

# Prompt file paths
ANALYST_ROLE_PATH = AGENT_ROLE_DIR / "analyst_prompt.md"
RD_REVIEW_ROLE_PATH = AGENT_ROLE_DIR / "rd_review_prompt.md"
RD_SYNTHESIS_ROLE_PATH = AGENT_ROLE_DIR / "rd_synthesis_prompt.md"
MEMO_ENGINE_PATH = SYNTHESIS_ENGINE_DIR / "buyside_memo_engine_v1.2.0.md"
SOURCE_SUMMARY_AGENT_PATH = SOURCE_AGENT_DIR / "source_summary_agent.md"
HUMAN_READABLE_ENGINE_PATH = HUMAN_READABLE_DIR / "human_readable_output_engine.md"

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

    # Model settings
    model: str = "claude-sonnet-4-20250514"
    max_tokens: int = 16000
    temperature: float = 0.7

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

    # Rate limiting (requests per minute)
    rate_limit_rpm: int = 50

    def __post_init__(self):
        """Create necessary directories if they don't exist."""
        self.log_dir.mkdir(parents=True, exist_ok=True)

    @classmethod
    def from_dict(cls, config_dict: dict) -> "PipelineConfig":
        """Create a PipelineConfig from a dictionary."""
        return cls(**{k: v for k, v in config_dict.items() if k in cls.__dataclass_fields__})


def get_output_dir(ticker: str) -> Path:
    """Get the output directory for a specific ticker."""
    output_dir = REPORT_OUTPUT / ticker
    output_dir.mkdir(parents=True, exist_ok=True)
    return output_dir


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
    """Get the path to the final polished memo for a ticker."""
    return get_output_dir(ticker) / f"{ticker}_memo_vF.md"
