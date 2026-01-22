"""
Dashboard Server - FastAPI server with SSE for real-time updates.

Provides:
- SSE endpoint for streaming pipeline events
- Static file serving for the dashboard UI
- State endpoint for initial page load
- Reports endpoint for serving PDF files
"""

import asyncio
import socket
import threading
import webbrowser
from pathlib import Path
from typing import Optional
from urllib.parse import unquote

from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import HTMLResponse, StreamingResponse, JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles

from .emitter import ProgressEmitter

# Path to static files
STATIC_DIR = Path(__file__).parent / "static"

# Path to report output directory (two levels up from dashboard)
REPORT_OUTPUT_DIR = Path(__file__).parent.parent.parent.parent / "2 - report output"


def find_available_port(start_port: int = 8765, max_tries: int = 100) -> int:
    """Find an available port starting from start_port.

    Args:
        start_port: First port to try
        max_tries: Maximum number of ports to check

    Returns:
        An available port number

    Raises:
        RuntimeError: If no available port found in range
    """
    for port in range(start_port, start_port + max_tries):
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.bind(('127.0.0.1', port))
                return port
        except OSError:
            continue
    raise RuntimeError(f"No available ports in range {start_port}-{start_port + max_tries}")


def create_app(emitter: Optional[ProgressEmitter] = None) -> FastAPI:
    """Create FastAPI application with dashboard routes.

    Args:
        emitter: ProgressEmitter instance to stream events from.
                If None, creates a new one.

    Returns:
        Configured FastAPI application
    """
    app = FastAPI(
        title="TTT Pipeline Dashboard",
        description="Bloomberg Terminal style progress monitor",
        version="1.0.0"
    )

    # Store emitter in app state
    if emitter is None:
        emitter = ProgressEmitter()
    app.state.emitter = emitter

    # Mount static files
    if STATIC_DIR.exists():
        app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

    @app.get("/", response_class=HTMLResponse)
    async def root():
        """Serve the main dashboard page."""
        index_path = STATIC_DIR / "index.html"
        if index_path.exists():
            return HTMLResponse(content=index_path.read_text(), status_code=200)
        return HTMLResponse(
            content="<h1>Dashboard not found</h1><p>Static files missing.</p>",
            status_code=404
        )

    @app.get("/events")
    async def events(request: Request):
        """SSE endpoint for streaming pipeline events."""
        emitter: ProgressEmitter = request.app.state.emitter

        async def event_generator():
            """Generate SSE events from emitter."""
            subscriber_queue = emitter.subscribe()
            try:
                while True:
                    # Check if client disconnected
                    if await request.is_disconnected():
                        break

                    try:
                        # Non-blocking check with small timeout
                        event = await asyncio.get_event_loop().run_in_executor(
                            None,
                            lambda: subscriber_queue.get(timeout=1.0)
                        )
                        yield event.to_sse()

                        # Exit on shutdown event
                        if event.type == "shutdown":
                            break

                    except Exception:
                        # Send heartbeat to keep connection alive
                        yield "data: {\"type\": \"heartbeat\", \"data\": {}}\n\n"

            finally:
                emitter.unsubscribe(subscriber_queue)

        return StreamingResponse(
            event_generator(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",  # Disable nginx buffering
            }
        )

    @app.get("/state")
    async def get_state(request: Request):
        """Get current pipeline state."""
        emitter: ProgressEmitter = request.app.state.emitter
        return JSONResponse(content=emitter.get_state().to_dict())

    @app.get("/health")
    async def health():
        """Health check endpoint."""
        return JSONResponse(content={"status": "ok"})

    @app.get("/reports/{file_path:path}")
    async def serve_report(file_path: str):
        """Serve PDF report files from the report output directory.

        Args:
            file_path: Path to the PDF file (e.g., "INTC_V1_2026-01-21/INTC_memo_EN.pdf")

        Returns:
            PDF file response
        """
        # Decode URL-encoded path
        decoded_path = unquote(file_path)

        # Construct full path and validate it's within report output dir
        full_path = REPORT_OUTPUT_DIR / decoded_path
        full_path = full_path.resolve()

        # Security check: ensure path is within report output directory
        if not str(full_path).startswith(str(REPORT_OUTPUT_DIR.resolve())):
            raise HTTPException(status_code=403, detail="Access denied")

        if not full_path.exists():
            raise HTTPException(status_code=404, detail="Report not found")

        if not full_path.suffix.lower() == ".pdf":
            raise HTTPException(status_code=400, detail="Only PDF files are served")

        return FileResponse(
            path=full_path,
            filename=full_path.name,
            media_type="application/pdf"
        )

    return app


class DashboardServer:
    """Manages the dashboard server lifecycle."""

    def __init__(
        self,
        emitter: ProgressEmitter,
        host: str = "127.0.0.1",
        port: int = 8765,
        auto_port: bool = True
    ):
        self.emitter = emitter
        self.host = host
        # Auto-assign an available port to support concurrent pipelines
        self.port = find_available_port(port) if auto_port else port
        self._server_thread: Optional[threading.Thread] = None
        self._shutdown_event = threading.Event()

    def start(self, open_browser: bool = True) -> None:
        """Start the dashboard server in a background thread.

        Args:
            open_browser: If True, opens the dashboard in default browser
        """
        def run_server():
            import uvicorn
            app = create_app(self.emitter)

            config = uvicorn.Config(
                app,
                host=self.host,
                port=self.port,
                log_level="warning",  # Reduce noise
                access_log=False,
            )
            server = uvicorn.Server(config)

            # Run until shutdown event
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                loop.run_until_complete(server.serve())
            finally:
                loop.close()

        self._server_thread = threading.Thread(target=run_server, daemon=True)
        self._server_thread.start()

        # Give server time to start
        import time
        time.sleep(0.5)

        if open_browser:
            self.open_browser()

    def open_browser(self) -> None:
        """Open the dashboard in the default browser."""
        url = f"http://{self.host}:{self.port}"
        webbrowser.open(url)

    def stop(self) -> None:
        """Stop the dashboard server."""
        self._shutdown_event.set()
        self.emitter.shutdown()


def start_dashboard_server(
    emitter: ProgressEmitter,
    host: str = "127.0.0.1",
    port: int = 8765,
    open_browser: bool = True,
    auto_port: bool = True
) -> DashboardServer:
    """Convenience function to start the dashboard server.

    Args:
        emitter: ProgressEmitter instance
        host: Host to bind to
        port: Port to listen on (starting port if auto_port=True)
        open_browser: Whether to open browser automatically
        auto_port: If True, find an available port starting from `port`

    Returns:
        DashboardServer instance
    """
    server = DashboardServer(emitter, host, port, auto_port=auto_port)
    server.start(open_browser=open_browser)
    return server
