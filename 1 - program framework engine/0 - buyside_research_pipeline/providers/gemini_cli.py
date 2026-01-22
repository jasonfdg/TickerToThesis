"""
Gemini CLI Provider (Stub)
==========================
Executes Gemini via local CLI instead of API.
Requires: Gemini CLI installed and authenticated.

STATUS: NOT IMPLEMENTED - Using API for now.

Future benefits:
- Google One AI Premium subscription ($20/month)
- No per-token costs
- Access to grounding/search features

Usage (when implemented):
    Set provider to "gemini-cli" in config.py
"""

import asyncio
import logging
from typing import Optional

from .base import BaseProvider, ProviderConfig, ProviderResponse

try:
    from ..models import TokenUsage
except ImportError:
    from models import TokenUsage

logger = logging.getLogger(__name__)


class GeminiCliProvider(BaseProvider):
    """Gemini CLI provider - STUB, not yet implemented."""

    provider_name = "gemini-cli"

    # Model mapping: alias -> CLI model flag
    MODELS = {
        "gemini-2.5-pro": "gemini-2.5-pro",
        "gemini-2.5-flash": "gemini-2.5-flash",
        "gemini-2.0-flash": "gemini-2.0-flash",
        "gemini-1.5-pro": "gemini-1.5-pro",
    }

    def __init__(self, config: Optional[ProviderConfig] = None):
        super().__init__(config)
        self._cli_path = "gemini"  # Assumes in PATH
        logger.warning(
            "GeminiCliProvider is a STUB - not yet implemented. "
            "Use 'gemini' provider for API calls."
        )

    def _resolve_model(self, model: Optional[str]) -> str:
        """Resolve model alias to CLI model name."""
        if model is None:
            model = self.config.model or "gemini-2.5-pro"
        return self.MODELS.get(model, model)

    async def generate(
        self,
        system_prompt: str,
        user_prompt: str,
        model: Optional[str] = None,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
    ) -> ProviderResponse:
        """Generate completion using Gemini CLI.

        NOT IMPLEMENTED - raises NotImplementedError.
        """
        raise NotImplementedError(
            "GeminiCliProvider is not yet implemented. "
            "Use 'gemini' provider with API key instead."
        )

        # TODO: Implementation outline
        # 1. Build combined prompt
        # 2. Execute: gemini --model {model} --prompt "..."
        #    Or use MCP tool: mcp__gemini__chat
        # 3. Parse stdout
        # 4. Return ProviderResponse with estimated tokens
        #
        # Note: Gemini CLI may have different flags - check docs

    async def test_connection(self) -> bool:
        """Test that Gemini CLI is available."""
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
            logger.info(f"Gemini CLI version: {version}")
            return process.returncode == 0
        except FileNotFoundError:
            logger.warning("Gemini CLI not found in PATH")
            return False
        except Exception as e:
            logger.warning(f"Gemini CLI test failed: {e}")
            return False

    def close(self):
        """No persistent connections to close."""
        pass
