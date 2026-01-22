"""
Perplexity CLI Provider (Stub)
==============================
Executes Perplexity via local CLI instead of API.
Requires: Perplexity CLI installed and authenticated.

STATUS: NOT IMPLEMENTED - Using API for now.

Future benefits:
- Perplexity Pro subscription ($20/month)
- No per-token costs
- Real-time web search with citations

Usage (when implemented):
    Set provider to "perplexity-cli" in config.py
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


class PerplexityCliProvider(BaseProvider):
    """Perplexity CLI provider - STUB, not yet implemented."""

    provider_name = "perplexity-cli"

    # Model mapping: alias -> CLI model flag
    MODELS = {
        "sonar": "sonar",
        "sonar-pro": "sonar-pro",
        "sonar-reasoning": "sonar-reasoning",
    }

    def __init__(self, config: Optional[ProviderConfig] = None):
        super().__init__(config)
        self._cli_path = "perplexity"  # Assumes in PATH - verify actual CLI name
        logger.warning(
            "PerplexityCliProvider is a STUB - not yet implemented. "
            "Use 'perplexity' provider for API calls."
        )

    def _resolve_model(self, model: Optional[str]) -> str:
        """Resolve model alias to CLI model name."""
        if model is None:
            model = self.config.model or "sonar"
        return self.MODELS.get(model, model)

    async def generate(
        self,
        system_prompt: str,
        user_prompt: str,
        model: Optional[str] = None,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
    ) -> ProviderResponse:
        """Generate completion using Perplexity CLI.

        NOT IMPLEMENTED - raises NotImplementedError.
        """
        raise NotImplementedError(
            "PerplexityCliProvider is not yet implemented. "
            "Use 'perplexity' provider with API key instead."
        )

        # TODO: Implementation outline
        # 1. Build search query from prompts
        # 2. Execute CLI with web search enabled
        #    Or use MCP tool: mcp__perplexity__perplexity_ask
        # 3. Parse response with citations
        # 4. Return ProviderResponse
        #
        # Note: Perplexity's value is web search - preserve citations

    async def test_connection(self) -> bool:
        """Test that Perplexity CLI is available."""
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
            logger.info(f"Perplexity CLI version: {version}")
            return process.returncode == 0
        except FileNotFoundError:
            logger.warning("Perplexity CLI not found in PATH")
            return False
        except Exception as e:
            logger.warning(f"Perplexity CLI test failed: {e}")
            return False

    def close(self):
        """No persistent connections to close."""
        pass
