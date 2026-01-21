"""
OpenAI Provider
===============
OpenAI GPT API wrapper.
"""

import asyncio
import logging
import os
from typing import Optional

import openai

from .base import BaseProvider, ProviderConfig, ProviderResponse

try:
    from ..models import TokenUsage
except ImportError:
    from models import TokenUsage

logger = logging.getLogger(__name__)


class OpenAIProvider(BaseProvider):
    """OpenAI GPT provider implementation."""

    provider_name = "openai"

    # Model aliases
    MODELS = {
        "gpt4o": "gpt-4o",
        "gpt-4o": "gpt-4o",
        "gpt4o-mini": "gpt-4o-mini",
        "gpt-4o-mini": "gpt-4o-mini",
        "o1": "o1-preview",
        "o1-mini": "o1-mini",
    }

    def __init__(self, config: Optional[ProviderConfig] = None):
        super().__init__(config)
        api_key = self.config.api_key or os.getenv("OPENAI_API_KEY")
        self.client = openai.AsyncOpenAI(api_key=api_key)

    def _resolve_model(self, model: Optional[str]) -> str:
        """Resolve model alias to full model name."""
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
        """Generate completion using OpenAI."""
        resolved_model = self._resolve_model(model)
        max_tok = max_tokens or self.config.max_tokens
        temp = temperature if temperature is not None else self.config.temperature

        try:
            response = await asyncio.wait_for(
                self.client.chat.completions.create(
                    model=resolved_model,
                    max_tokens=max_tok,
                    temperature=temp,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt},
                    ],
                ),
                timeout=self.config.timeout,
            )

            # Extract content
            content = response.choices[0].message.content or ""

            # Extract token usage
            usage = TokenUsage(
                input_tokens=response.usage.prompt_tokens if response.usage else 0,
                output_tokens=response.usage.completion_tokens if response.usage else 0,
            )

            return ProviderResponse(
                content=content,
                token_usage=usage,
                model=resolved_model,
                provider=self.provider_name,
            )

        except openai.RateLimitError as e:
            logger.warning(f"OpenAI rate limit: {e}")
            raise
        except openai.APIError as e:
            logger.error(f"OpenAI API error: {e}")
            raise

    async def test_connection(self) -> bool:
        """Test OpenAI connection with a minimal request."""
        try:
            response = await self.client.chat.completions.create(
                model="gpt-4o-mini",
                max_tokens=10,
                messages=[{"role": "user", "content": "Hi"}],
            )
            return bool(response.choices[0].message.content)
        except Exception as e:
            logger.error(f"OpenAI connection test failed: {e}")
            return False
