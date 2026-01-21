"""
Progress Tracker - Rich progress output for TickerToThesis pipeline.

Provides:
- Progress bars for iterations and phases
- Cost tracking per phase
- Iteration summaries
- Final pipeline summary
"""
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, Optional, Any
from enum import Enum

try:
    from tqdm import tqdm
    TQDM_AVAILABLE = True
except ImportError:
    TQDM_AVAILABLE = False


class PhaseType(Enum):
    GENESIS = "genesis"
    ANALYSTS = "analysts"
    SOURCE_UPDATE = "source_update"
    RD_REVIEWS = "rd_reviews"
    SOURCE_SCOUT = "source_scout"
    SYNTHESIS = "synthesis"


@dataclass
class PhaseStats:
    phase: PhaseType
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    tokens_used: int = 0
    cost_estimate: float = 0.0


class ProgressTracker:
    """Track and display pipeline progress with rich output."""

    def __init__(
        self,
        ticker: str,
        num_iterations: int = 5,
        num_analysts: int = 6,
        provider_factory: Any = None,
        log_file: Optional[str] = None,
    ):
        self.ticker = ticker
        self.num_iterations = num_iterations
        self.num_analysts = num_analysts
        self.provider_factory = provider_factory
        self.log_file = log_file
        self.current_iteration = 0
        self.phases: Dict[str, PhaseStats] = {}
        self.iteration_summaries: list = []
        self.total_cost = 0.0
        self._iteration_bar = None
        self._phase_bar = None

    def start_pipeline(self) -> None:
        """Initialize pipeline progress tracking."""
        if TQDM_AVAILABLE:
            self._iteration_bar = tqdm(
                total=self.num_iterations + 1,  # +1 for genesis scout
                desc=f"{self.ticker} Pipeline",
                unit="iter",
                position=0,
                bar_format="{l_bar}{bar}| {n_fmt}/{total_fmt} [{elapsed}<{remaining}]"
            )
        else:
            print(f"\n{'='*60}")
            print(f"{self.ticker} Pipeline Starting")
            print(f"{'='*60}")

    def end_pipeline(self, state: Any) -> None:
        """Finalize pipeline and print summary."""
        if self._iteration_bar and TQDM_AVAILABLE:
            self._iteration_bar.close()
        self._print_final_summary(state)

    def start_genesis(self) -> None:
        """Mark genesis phase start."""
        self.current_iteration = 0
        self._start_phase(PhaseType.GENESIS, 1)

    def end_genesis(self, tokens: int, cost: float) -> None:
        """Mark genesis phase complete."""
        self._end_phase(PhaseType.GENESIS, tokens, cost)
        if self._iteration_bar and TQDM_AVAILABLE:
            self._iteration_bar.update(1)

    def start_iteration(self, iteration: int) -> None:
        """Mark iteration start."""
        self.current_iteration = iteration
        if self._iteration_bar and TQDM_AVAILABLE:
            self._iteration_bar.set_description(f"{self.ticker} Iter {iteration}")

    def end_iteration(self, iteration_state: Any) -> None:
        """Mark iteration complete and print summary."""
        summary = self._generate_iteration_summary(iteration_state)
        self.iteration_summaries.append(summary)
        print(f"\n{summary}\n")
        if self._iteration_bar and TQDM_AVAILABLE:
            self._iteration_bar.update(1)

    def start_phase(self, phase: PhaseType, total_agents: int) -> None:
        """Start tracking a phase."""
        self._start_phase(phase, total_agents)

    def end_phase(self, phase: PhaseType, tokens: int, cost: float) -> None:
        """End tracking a phase."""
        self._end_phase(phase, tokens, cost)

    def _start_phase(self, phase: PhaseType, total_agents: int) -> None:
        """Internal: start phase tracking."""
        phase_key = f"{self.current_iteration}_{phase.value}"
        self.phases[phase_key] = PhaseStats(phase=phase, started_at=datetime.now())

        if self._phase_bar and TQDM_AVAILABLE:
            self._phase_bar.close()

        phase_names = {
            PhaseType.GENESIS: "Genesis Scout",
            PhaseType.ANALYSTS: f"Analysts (Iter {self.current_iteration})",
            PhaseType.RD_REVIEWS: f"RD Reviews (Iter {self.current_iteration})",
            PhaseType.SOURCE_SCOUT: f"Source Scout (Iter {self.current_iteration})",
            PhaseType.SOURCE_UPDATE: f"Source Update (Iter {self.current_iteration})",
            PhaseType.SYNTHESIS: "Final Synthesis",
        }

        if TQDM_AVAILABLE:
            self._phase_bar = tqdm(
                total=total_agents,
                desc=f"  {phase_names.get(phase, phase.value)}",
                unit="agent",
                position=1,
                leave=False,
            )

    def _end_phase(self, phase: PhaseType, tokens: int, cost: float) -> None:
        """Internal: end phase tracking."""
        phase_key = f"{self.current_iteration}_{phase.value}"

        if phase_key in self.phases:
            self.phases[phase_key].completed_at = datetime.now()
            self.phases[phase_key].tokens_used = tokens
            self.phases[phase_key].cost_estimate = cost

        self.total_cost += cost

        # Calculate duration
        duration = 0.0
        if phase_key in self.phases and self.phases[phase_key].started_at:
            if self.phases[phase_key].completed_at:
                duration = (
                    self.phases[phase_key].completed_at -
                    self.phases[phase_key].started_at
                ).total_seconds()

        print(
            f"  {phase.value}: {tokens:,} tokens | "
            f"${cost:.2f} | {duration:.1f}s | "
            f"Total: ${self.total_cost:.2f}"
        )

        if self._phase_bar and TQDM_AVAILABLE:
            self._phase_bar.close()
            self._phase_bar = None

    def update_phase_progress(self, completed: int = 1) -> None:
        """Update phase progress bar."""
        if self._phase_bar and TQDM_AVAILABLE:
            self._phase_bar.update(completed)

    def _generate_iteration_summary(self, state: Any) -> str:
        """Generate 1-paragraph summary of iteration."""
        num_analysts_success = sum(
            1 for r in state.analyst_reports.values() if r.is_success
        )
        num_rd_success = sum(
            1 for r in state.rd_reviews.values() if r.is_success
        )
        total_tokens = state.total_token_usage.total_tokens
        duration = state.duration_seconds or 0

        parts = [
            f"Iteration {state.iteration} completed in {duration:.0f}s.",
            f"{num_analysts_success}/6 analysts and {num_rd_success}/6 RD reviews succeeded.",
            f"Tokens: {total_tokens:,}.",
        ]

        if state.source_scout_report and state.source_scout_report.is_success:
            parts.append("Source Scout found new evidence.")

        return " ".join(parts)

    def _print_final_summary(self, state: Any) -> None:
        """Print final pipeline summary."""
        print("\n" + "=" * 60)
        print("PIPELINE COMPLETE")
        print("=" * 60)
        print(f"Ticker: {self.ticker}")

        if hasattr(state, 'duration_seconds') and state.duration_seconds:
            print(f"Duration: {state.duration_seconds:.0f}s")

        if hasattr(state, 'total_token_usage'):
            print(f"Total Tokens: {state.total_token_usage.total_tokens:,}")

        print(f"Estimated Cost: ${self.total_cost:.2f}")
        print("=" * 60)

        # Log to file if configured
        if self.log_file:
            self._write_log_file(state)

    def _write_log_file(self, state: Any) -> None:
        """Write progress log to file."""
        try:
            with open(self.log_file, 'w') as f:
                f.write(f"Pipeline Progress Log: {self.ticker}\n")
                f.write(f"{'='*60}\n\n")

                f.write("Phase Summary:\n")
                for phase_key, stats in self.phases.items():
                    duration = 0.0
                    if stats.started_at and stats.completed_at:
                        duration = (stats.completed_at - stats.started_at).total_seconds()
                    f.write(
                        f"  {phase_key}: {stats.tokens_used:,} tokens, "
                        f"${stats.cost_estimate:.2f}, {duration:.1f}s\n"
                    )

                f.write(f"\nIteration Summaries:\n")
                for summary in self.iteration_summaries:
                    f.write(f"  {summary}\n")

                f.write(f"\nTotal Cost: ${self.total_cost:.2f}\n")
        except Exception as e:
            print(f"Warning: Could not write progress log: {e}")
