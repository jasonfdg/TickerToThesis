"""
Progress Emitter - Thread-safe event emission for dashboard SSE.

Provides a queue-based system for emitting pipeline events that can be
consumed by the SSE endpoint.
"""

import json
import threading
import time
from dataclasses import dataclass, field, asdict
from datetime import datetime
from queue import Queue, Empty
from typing import Any, Dict, Generator, Optional, List


@dataclass
class DashboardEvent:
    """A single event to be sent to the dashboard."""
    type: str
    data: Dict[str, Any]
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_sse(self) -> str:
        """Convert to SSE format."""
        payload = {
            "type": self.type,
            "data": self.data,
            "timestamp": self.timestamp
        }
        return f"data: {json.dumps(payload)}\n\n"


class ProgressEmitter:
    """Thread-safe event emitter for dashboard updates.

    This class provides a bridge between the pipeline execution (which may
    run in any thread) and the SSE endpoint (which serves events to the browser).

    Usage:
        emitter = ProgressEmitter()

        # Emit events from pipeline
        emitter.emit("pipeline_started", {"ticker": "AAPL", "iterations": 5})
        emitter.emit("agent_started", {"role": "analyst", "type_id": 1})

        # Consume events in SSE endpoint
        for event in emitter.events():
            yield event.to_sse()
    """

    def __init__(self, max_queue_size: int = 1000):
        self._queue: Queue[DashboardEvent] = Queue(maxsize=max_queue_size)
        self._lock = threading.Lock()
        self._state = PipelineState()
        self._subscribers: List[Queue] = []
        self._running = True

    def emit(self, event_type: str, data: Dict[str, Any]) -> None:
        """Emit an event to all subscribers.

        Thread-safe. Can be called from any thread.

        Args:
            event_type: Type of event (e.g., "pipeline_started", "agent_completed")
            data: Event payload data
        """
        event = DashboardEvent(type=event_type, data=data)

        # Update internal state
        self._update_state(event)

        # Broadcast to all subscribers
        with self._lock:
            for subscriber_queue in self._subscribers:
                try:
                    subscriber_queue.put_nowait(event)
                except:
                    pass  # Skip if queue is full

    def subscribe(self) -> Queue:
        """Subscribe to events. Returns a queue that will receive events."""
        subscriber_queue: Queue = Queue(maxsize=100)
        with self._lock:
            self._subscribers.append(subscriber_queue)
        return subscriber_queue

    def unsubscribe(self, subscriber_queue: Queue) -> None:
        """Unsubscribe from events."""
        with self._lock:
            if subscriber_queue in self._subscribers:
                self._subscribers.remove(subscriber_queue)

    def events(self, timeout: float = 30.0) -> Generator[DashboardEvent, None, None]:
        """Generator that yields events as they arrive.

        Args:
            timeout: How long to wait for events before yielding a heartbeat

        Yields:
            DashboardEvent objects
        """
        subscriber_queue = self.subscribe()
        try:
            while self._running:
                try:
                    event = subscriber_queue.get(timeout=timeout)
                    yield event
                except Empty:
                    # Send heartbeat to keep connection alive
                    yield DashboardEvent(type="heartbeat", data={})
        finally:
            self.unsubscribe(subscriber_queue)

    def get_state(self) -> "PipelineState":
        """Get current pipeline state snapshot."""
        return self._state

    def _update_state(self, event: DashboardEvent) -> None:
        """Update internal state based on event."""
        state = self._state
        event_type = event.type
        data = event.data

        if event_type == "pipeline_started":
            state.ticker = data.get("ticker", "")
            state.total_iterations = data.get("iterations", 5)
            state.status = "running"
            state.started_at = event.timestamp

        elif event_type == "pipeline_completed":
            state.status = "completed"
            state.completed_at = event.timestamp
            state.final_path = data.get("final_path", "")
            state.pdf_en = data.get("pdf_en", "")
            state.pdf_cn = data.get("pdf_cn", "")

        elif event_type == "pipeline_failed":
            state.status = "failed"
            state.error = data.get("error", "Unknown error")

        elif event_type == "iteration_started":
            state.current_iteration = data.get("iteration", 0)
            state.current_phase = data.get("phase", "")
            state.completed_agents = 0  # Reset agent counter for new iteration/phase

        elif event_type == "iteration_completed":
            iteration = data.get("iteration", 0)
            state.iteration_tokens[iteration] = data.get("tokens", 0)

        elif event_type == "agent_started":
            role = data.get("role", "")
            type_id = data.get("type_id", 0)
            key = f"{role}_{type_id}"
            state.agent_status[key] = "running"

        elif event_type == "agent_completed":
            role = data.get("role", "")
            type_id = data.get("type_id", 0)
            key = f"{role}_{type_id}"
            state.agent_status[key] = "completed" if data.get("success") else "failed"
            state.total_tokens += data.get("tokens", 0)
            # Track agent completion for progress granularity
            if role in ("analyst", "rd_review"):
                state.completed_agents += 1

        elif event_type == "agent_failed":
            role = data.get("role", "")
            type_id = data.get("type_id", 0)
            key = f"{role}_{type_id}"
            state.agent_status[key] = "failed"

        elif event_type == "cost_updated":
            state.cost_claude = data.get("claude_cli", 0.0)
            state.cost_openai = data.get("openai", 0.0)
            state.cost_gemini = data.get("gemini", 0.0)
            state.cost_total = data.get("total", 0.0)

        elif event_type == "thesis_updated":
            state.thesis_summary = data.get("summary", "")

        elif event_type == "source_updated":
            state.source_citations += data.get("new_citations", 0)
            # Transition to rd_reviews phase and reset agent counter
            state.current_phase = "rd_reviews"
            state.completed_agents = 0

    def shutdown(self) -> None:
        """Shutdown the emitter and notify subscribers."""
        self._running = False
        # Emit shutdown event
        self.emit("shutdown", {})


@dataclass
class PipelineState:
    """Current state of the pipeline for dashboard display."""

    # Pipeline metadata
    ticker: str = ""
    status: str = "pending"  # pending, running, completed, failed
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    final_path: str = ""
    pdf_en: str = ""
    pdf_cn: str = ""
    error: str = ""

    # Progress tracking
    current_iteration: int = 0
    total_iterations: int = 5
    current_phase: str = ""
    completed_agents: int = 0  # Counter for agents completed in current phase

    # Agent status: {role_typeId: status}
    agent_status: Dict[str, str] = field(default_factory=dict)

    # Token tracking
    total_tokens: int = 0
    iteration_tokens: Dict[int, int] = field(default_factory=dict)

    # Cost tracking
    cost_claude: float = 0.0
    cost_openai: float = 0.0
    cost_gemini: float = 0.0
    cost_total: float = 0.0

    # Source tracking
    source_citations: int = 0

    # Thesis evolution
    thesis_summary: str = ""

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "ticker": self.ticker,
            "status": self.status,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "final_path": self.final_path,
            "pdf_en": self.pdf_en,
            "pdf_cn": self.pdf_cn,
            "error": self.error,
            "current_iteration": self.current_iteration,
            "total_iterations": self.total_iterations,
            "current_phase": self.current_phase,
            "completed_agents": self.completed_agents,
            "agent_status": self.agent_status,
            "total_tokens": self.total_tokens,
            "iteration_tokens": self.iteration_tokens,
            "cost_claude": self.cost_claude,
            "cost_openai": self.cost_openai,
            "cost_gemini": self.cost_gemini,
            "cost_total": self.cost_total,
            "source_citations": self.source_citations,
            "thesis_summary": self.thesis_summary,
        }


# Activity log for dashboard
class ActivityLog:
    """Maintains a rolling log of recent activity."""

    def __init__(self, max_entries: int = 50):
        self._entries: List[Dict[str, Any]] = []
        self._max_entries = max_entries
        self._lock = threading.Lock()

    def add(self, message: str, level: str = "info") -> None:
        """Add a log entry."""
        entry = {
            "timestamp": datetime.now().strftime("%H:%M:%S"),
            "message": message,
            "level": level
        }
        with self._lock:
            self._entries.append(entry)
            if len(self._entries) > self._max_entries:
                self._entries.pop(0)

    def get_entries(self, limit: int = 20) -> List[Dict[str, Any]]:
        """Get recent log entries."""
        with self._lock:
            return list(self._entries[-limit:])
