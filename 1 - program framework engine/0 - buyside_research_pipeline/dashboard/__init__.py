"""
TTT Pipeline Dashboard
=====================
Bloomberg Terminal style browser-based progress dashboard.

Provides real-time visualization of pipeline progress via SSE.
"""

from .emitter import ProgressEmitter
from .server import create_app, start_dashboard_server

__all__ = ["ProgressEmitter", "create_app", "start_dashboard_server"]
