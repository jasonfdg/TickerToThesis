"""
TickerToThesis Pipeline
========================
Orchestrates 6 parallel analyst agents through 5 debate iterations
with a Research Director to produce institutional-quality buyside memos.
"""

from .config import PipelineConfig, INVESTING_TYPES
from .models import (
    AgentRole,
    TokenUsage,
    AgentReport,
    IterationState,
    PipelineState,
)
from .prompt_loader import PromptLoader
from .agent_runner import AgentRunner, AgentCall
from .source_manager import SourceManager
from .report_saver import ReportSaver
from .TickerToThesis import TickerToThesisPipeline

__all__ = [
    "PipelineConfig",
    "INVESTING_TYPES",
    "AgentRole",
    "TokenUsage",
    "AgentReport",
    "IterationState",
    "PipelineState",
    "PromptLoader",
    "AgentRunner",
    "AgentCall",
    "SourceManager",
    "ReportSaver",
    "TickerToThesisPipeline",
]

__version__ = "1.0.0"
