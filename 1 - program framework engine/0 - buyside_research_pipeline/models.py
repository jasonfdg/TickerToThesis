"""
Data Models
===========
Data classes for the TickerToThesis pipeline.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional


class AgentRole(Enum):
    """Role of an agent in the pipeline."""

    ANALYST = "analyst"
    RD_REVIEW = "rd_review"
    RD_SYNTHESIS = "rd_synthesis"
    SOURCE_SUMMARY = "source_summary"
    HUMAN_READABLE = "human_readable"
    SOURCE_SCOUT = "source_scout"


@dataclass
class TokenUsage:
    """Tracks token consumption for API calls."""

    input_tokens: int = 0
    output_tokens: int = 0
    cache_creation_input_tokens: int = 0
    cache_read_input_tokens: int = 0

    @property
    def total_tokens(self) -> int:
        """Total tokens used (input + output)."""
        return self.input_tokens + self.output_tokens

    def __add__(self, other: "TokenUsage") -> "TokenUsage":
        """Add two TokenUsage instances together."""
        return TokenUsage(
            input_tokens=self.input_tokens + other.input_tokens,
            output_tokens=self.output_tokens + other.output_tokens,
            cache_creation_input_tokens=self.cache_creation_input_tokens
            + other.cache_creation_input_tokens,
            cache_read_input_tokens=self.cache_read_input_tokens + other.cache_read_input_tokens,
        )

    def to_dict(self) -> Dict[str, int]:
        """Convert to dictionary for serialization."""
        return {
            "input_tokens": self.input_tokens,
            "output_tokens": self.output_tokens,
            "cache_creation_input_tokens": self.cache_creation_input_tokens,
            "cache_read_input_tokens": self.cache_read_input_tokens,
            "total_tokens": self.total_tokens,
        }

    @classmethod
    def from_api_response(cls, usage: dict) -> "TokenUsage":
        """Create TokenUsage from Claude API response usage dict."""
        return cls(
            input_tokens=usage.get("input_tokens", 0),
            output_tokens=usage.get("output_tokens", 0),
            cache_creation_input_tokens=usage.get("cache_creation_input_tokens", 0),
            cache_read_input_tokens=usage.get("cache_read_input_tokens", 0),
        )


@dataclass
class AgentReport:
    """Individual report artifact from an agent."""

    role: AgentRole
    investing_type_id: Optional[int]  # 1-6 for analysts, None for RD
    iteration: int
    content: str
    token_usage: TokenUsage
    timestamp: datetime = field(default_factory=datetime.now)
    error: Optional[str] = None

    @property
    def is_success(self) -> bool:
        """Whether the report was generated successfully."""
        return self.error is None and bool(self.content)

    @property
    def identifier(self) -> str:
        """Unique identifier for this report."""
        if self.investing_type_id is not None:
            return f"{self.role.value}_type_{self.investing_type_id}_v{self.iteration}"
        return f"{self.role.value}_v{self.iteration}"

    def to_dict(self) -> dict:
        """Convert to dictionary for serialization."""
        return {
            "role": self.role.value,
            "investing_type_id": self.investing_type_id,
            "iteration": self.iteration,
            "content_length": len(self.content),
            "token_usage": self.token_usage.to_dict(),
            "timestamp": self.timestamp.isoformat(),
            "error": self.error,
            "is_success": self.is_success,
        }


@dataclass
class IterationState:
    """State of a single iteration in the pipeline."""

    iteration: int
    analyst_reports: Dict[int, AgentReport] = field(default_factory=dict)  # type_id -> report
    rd_reviews: Dict[int, AgentReport] = field(default_factory=dict)  # type_id -> review
    source_scout_report: Optional[AgentReport] = None  # Web research findings for this iteration
    source_updated: bool = False
    completed: bool = False
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

    def mark_started(self):
        """Mark the iteration as started."""
        self.started_at = datetime.now()

    def mark_completed(self):
        """Mark the iteration as completed."""
        self.completed = True
        self.completed_at = datetime.now()

    @property
    def duration_seconds(self) -> Optional[float]:
        """Duration of the iteration in seconds."""
        if self.started_at and self.completed_at:
            return (self.completed_at - self.started_at).total_seconds()
        return None

    @property
    def total_token_usage(self) -> TokenUsage:
        """Total tokens used in this iteration."""
        total = TokenUsage()
        for report in self.analyst_reports.values():
            total = total + report.token_usage
        for review in self.rd_reviews.values():
            total = total + review.token_usage
        if self.source_scout_report:
            total = total + self.source_scout_report.token_usage
        return total

    def to_dict(self) -> dict:
        """Convert to dictionary for serialization."""
        return {
            "iteration": self.iteration,
            "analyst_reports": {k: v.to_dict() for k, v in self.analyst_reports.items()},
            "rd_reviews": {k: v.to_dict() for k, v in self.rd_reviews.items()},
            "source_scout_report": self.source_scout_report.to_dict() if self.source_scout_report else None,
            "source_updated": self.source_updated,
            "completed": self.completed,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "duration_seconds": self.duration_seconds,
            "total_token_usage": self.total_token_usage.to_dict(),
        }


@dataclass
class PipelineState:
    """Complete state of the TickerToThesis pipeline."""

    ticker: str
    preliminary_thinking: str
    iterations: Dict[int, IterationState] = field(default_factory=dict)
    synthesis_report: Optional[AgentReport] = None
    final_report: Optional[AgentReport] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error: Optional[str] = None

    def __post_init__(self):
        """Initialize iteration states if not provided."""
        if not self.iterations:
            for i in range(1, 6):  # 5 iterations
                self.iterations[i] = IterationState(iteration=i)

    def mark_started(self):
        """Mark the pipeline as started."""
        self.started_at = datetime.now()

    def mark_completed(self):
        """Mark the pipeline as completed."""
        self.completed_at = datetime.now()

    def mark_failed(self, error: str):
        """Mark the pipeline as failed."""
        self.error = error
        self.completed_at = datetime.now()

    @property
    def is_complete(self) -> bool:
        """Whether the pipeline has completed successfully."""
        return self.final_report is not None and self.error is None

    @property
    def is_failed(self) -> bool:
        """Whether the pipeline has failed."""
        return self.error is not None

    @property
    def duration_seconds(self) -> Optional[float]:
        """Total duration of the pipeline in seconds."""
        if self.started_at and self.completed_at:
            return (self.completed_at - self.started_at).total_seconds()
        return None

    @property
    def total_token_usage(self) -> TokenUsage:
        """Total tokens used across the entire pipeline."""
        total = TokenUsage()
        for iteration in self.iterations.values():
            total = total + iteration.total_token_usage
        if self.synthesis_report:
            total = total + self.synthesis_report.token_usage
        if self.final_report:
            total = total + self.final_report.token_usage
        return total

    @property
    def current_iteration(self) -> int:
        """Get the current (or most recent) iteration number."""
        for i in range(5, 0, -1):
            if self.iterations[i].started_at is not None:
                return i
        return 1

    def get_latest_analyst_reports(self) -> Dict[int, AgentReport]:
        """Get the most recent analyst reports for each type."""
        latest = {}
        for i in range(self.current_iteration, 0, -1):
            for type_id, report in self.iterations[i].analyst_reports.items():
                if type_id not in latest and report.is_success:
                    latest[type_id] = report
            if len(latest) == 6:
                break
        return latest

    def get_latest_rd_reviews(self) -> Dict[int, AgentReport]:
        """Get the most recent RD reviews for each type."""
        latest = {}
        for i in range(self.current_iteration, 0, -1):
            for type_id, review in self.iterations[i].rd_reviews.items():
                if type_id not in latest and review.is_success:
                    latest[type_id] = review
            if len(latest) == 6:
                break
        return latest

    def to_dict(self) -> dict:
        """Convert to dictionary for serialization."""
        return {
            "ticker": self.ticker,
            "preliminary_thinking": self.preliminary_thinking[:200] + "..."
            if len(self.preliminary_thinking) > 200
            else self.preliminary_thinking,
            "iterations": {k: v.to_dict() for k, v in self.iterations.items()},
            "synthesis_report": self.synthesis_report.to_dict() if self.synthesis_report else None,
            "final_report": self.final_report.to_dict() if self.final_report else None,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "duration_seconds": self.duration_seconds,
            "total_token_usage": self.total_token_usage.to_dict(),
            "is_complete": self.is_complete,
            "error": self.error,
        }
