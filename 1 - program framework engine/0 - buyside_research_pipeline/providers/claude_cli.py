"""
Claude Code CLI Provider
========================
Executes Claude via local CLI instead of API.
Requires: Claude Code CLI installed and authenticated (Max subscription).

Benefits:
- Unlimited usage with Max subscription ($100/month)
- No per-token costs
- Same model quality as API

Usage:
    export PROVIDER_MODE=cli
    python TickerToThesis.py AAPL "..."
"""

import asyncio
import logging
import tempfile
from pathlib import Path
from typing import Optional

from .base import BaseProvider, ProviderConfig, ProviderResponse

try:
    from ..models import TokenUsage
except ImportError:
    from models import TokenUsage

logger = logging.getLogger(__name__)


class ClaudeCliProvider(BaseProvider):
    """Claude Code CLI provider - uses local CLI instead of API."""

    provider_name = "claude-cli"

    # Model mapping: alias -> CLI model flag
    MODELS = {
        "sonnet": "sonnet",
        "opus": "opus",
        "haiku": "haiku",
    }

    def __init__(self, config: Optional[ProviderConfig] = None):
        super().__init__(config)
        self._cli_path = "claude"  # Assumes in PATH

    def _resolve_model(self, model: Optional[str]) -> str:
        """Resolve model alias to CLI model name."""
        if model is None:
            model = self.config.model or "sonnet"
        return self.MODELS.get(model, model)

    async def generate(
        self,
        system_prompt: str,
        user_prompt: str,
        model: Optional[str] = None,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
    ) -> ProviderResponse:
        """Generate completion using Claude Code CLI."""
        resolved_model = self._resolve_model(model)

        # Build combined prompt (CLI doesn't have separate system/user)
        full_prompt = f"{system_prompt}\n\n---\n\n{user_prompt}"

        # Write prompt to temp file (handles large prompts better than stdin)
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".txt", delete=False, encoding="utf-8"
        ) as f:
            f.write(full_prompt)
            prompt_file = f.name

        try:
            # Build CLI command
            # --print: Non-interactive, print response only
            # --model: Specify model (sonnet, opus, haiku)
            cmd = [
                self._cli_path,
                "--print",
                "--model", resolved_model,
            ]

            # Add max tokens if specified
            if max_tokens:
                cmd.extend(["--max-tokens", str(max_tokens)])

            # Read prompt from file
            with open(prompt_file, "r", encoding="utf-8") as pf:
                prompt_content = pf.read()

            logger.debug(f"CLI command: {' '.join(cmd)} (prompt: {len(prompt_content):,} chars)")

            # Execute CLI
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )

            stdout, stderr = await asyncio.wait_for(
                process.communicate(input=prompt_content.encode("utf-8")),
                timeout=self.config.timeout,
            )

            if process.returncode != 0:
                error_msg = stderr.decode("utf-8", errors="replace")
                logger.error(f"Claude CLI error (code {process.returncode}): {error_msg}")
                raise RuntimeError(f"Claude CLI failed: {error_msg}")

            content = stdout.decode("utf-8", errors="replace").strip()

            # CLI doesn't provide token counts - estimate
            # Rough estimate: ~4 chars per token (conservative)
            estimated_input = len(full_prompt) // 4
            estimated_output = len(content) // 4

            usage = TokenUsage(
                input_tokens=estimated_input,
                output_tokens=estimated_output,
                cache_creation_input_tokens=0,
                cache_read_input_tokens=0,
            )

            logger.info(
                f"CLI response: ~{estimated_output:,} tokens (estimated) "
                f"via {resolved_model}"
            )

            return ProviderResponse(
                content=content,
                token_usage=usage,
                model=resolved_model,
                provider=self.provider_name,
            )

        finally:
            # Cleanup temp file
            Path(prompt_file).unlink(missing_ok=True)

    async def test_connection(self) -> bool:
        """Test that Claude CLI is available and authenticated."""
        try:
            process = await asyncio.create_subprocess_exec(
                self._cli_path, "--version",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, _ = await asyncio.wait_for(
                process.communicate(),
                timeout=10.0,
            )
            version = stdout.decode("utf-8", errors="replace").strip()
            logger.info(f"Claude CLI version: {version}")
            return process.returncode == 0
        except FileNotFoundError:
            logger.error("Claude CLI not found. Install with: npm install -g @anthropic-ai/claude-code")
            return False
        except Exception as e:
            logger.error(f"Claude CLI test failed: {e}")
            return False

    def close(self):
        """No persistent connections to close."""
        pass
