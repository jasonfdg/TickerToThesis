"""
OpenAI CLI Provider (Stub)
==========================
Executes ChatGPT via local CLI instead of API.
Requires: ChatGPT CLI installed and authenticated.

STATUS: NOT IMPLEMENTED - Using API for now.

Future benefits:
- Subscription-based pricing (if available)
- No per-token costs
- CLI-specific features

Usage (when implemented):
    Set provider to "openai-cli" in config.py
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


class OpenAICliProvider(BaseProvider):
    """OpenAI CLI provider - STUB, not yet implemented."""

    provider_name = "openai-cli"

    # Model mapping: alias -> CLI model flag
    MODELS = {
        "gpt-4o": "gpt-4o",
        "gpt-4o-mini": "gpt-4o-mini",
        "o1-preview": "o1-preview",
        "o1-mini": "o1-mini",
    }

    def __init__(self, config: Optional[ProviderConfig] = None):
        super().__init__(config)
        self._cli_path = "chatgpt"  # kardolus/chatgpt-cli via Homebrew
        logger.warning(
            "OpenAICliProvider is a STUB - not yet implemented. "
            "Use 'openai' provider for API calls."
        )

    def _resolve_model(self, model: Optional[str]) -> str:
        """Resolve model alias to CLI model name."""
        if model is None:
            model = self.config.model or "gpt-4o"
        return self.MODELS.get(model, model)

    async def generate(
        self,
        system_prompt: str,
        user_prompt: str,
        model: Optional[str] = None,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
    ) -> ProviderResponse:
        """Generate completion using ChatGPT CLI.

        NOT IMPLEMENTED - raises NotImplementedError.
        """
        raise NotImplementedError(
            "OpenAICliProvider is not yet implemented. "
            "Use 'openai' provider with API key instead."
        )

        # TODO: Implementation outline (similar to claude_cli.py)
        # 1. Build combined prompt
        # 2. Write to temp file
        # 3. Execute: chatgpt --model {model} < prompt.txt
        # 4. Parse stdout
        # 5. Return ProviderResponse with estimated tokens

    async def test_connection(self) -> bool:
        """Test that ChatGPT CLI is available."""
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
            logger.info(f"ChatGPT CLI version: {version}")
            return process.returncode == 0
        except FileNotFoundError:
            logger.warning("ChatGPT CLI not found in PATH")
            return False
        except Exception as e:
            logger.warning(f"ChatGPT CLI test failed: {e}")
            return False

    def close(self):
        """No persistent connections to close."""
        pass
