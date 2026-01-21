"""
Claude Provider
===============
Anthropic Claude API wrapper.
"""

import asyncio
import logging
import os
from typing import Optional

import anthropic

from .base import BaseProvider, ProviderConfig, ProviderResponse, ProviderRateLimitError

try:
    from ..models import TokenUsage
except ImportError:
    from models import TokenUsage

logger = logging.getLogger(__name__)


class ClaudeProvider(BaseProvider):
    """Anthropic Claude provider implementation."""

    provider_name = "claude"

    # Model aliases for convenience
    MODELS = {
        "sonnet": "claude-sonnet-4-20250514",
        "opus": "claude-opus-4-20250514",
        "haiku": "claude-3-haiku-20240307",  # Use Claude 3 Haiku (stable)
    }

    # Model-specific max output token limits
    MODEL_MAX_TOKENS = {
        "claude-3-haiku-20240307": 4096,
        "claude-sonnet-4-20250514": 16000,
        "claude-opus-4-20250514": 16000,
    }

    # Models that require streaming for long operations
    STREAMING_REQUIRED_MODELS = {
        "claude-opus-4-20250514",  # Opus requires streaming for operations >10 min
    }

    def __init__(self, config: Optional[ProviderConfig] = None):
        super().__init__(config)
        api_key = self.config.api_key or os.getenv("ANTHROPIC_API_KEY")
        self.client = anthropic.AsyncAnthropic(api_key=api_key)

    def _resolve_model(self, model: Optional[str]) -> str:
        """Resolve model alias to full model name."""
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
        """Generate completion using Claude."""
        resolved_model = self._resolve_model(model)
        max_tok = max_tokens or self.config.max_tokens
        temp = temperature if temperature is not None else self.config.temperature

        # Enforce model-specific max token limits
        model_limit = self.MODEL_MAX_TOKENS.get(resolved_model, 16000)
        if max_tok > model_limit:
            logger.debug(f"Capping max_tokens from {max_tok} to {model_limit} for {resolved_model}")
            max_tok = model_limit

        # Use streaming for models that require it (e.g., Opus for long operations)
        use_streaming = resolved_model in self.STREAMING_REQUIRED_MODELS

        try:
            if use_streaming:
                return await self._generate_streaming(
                    resolved_model, max_tok, temp, system_prompt, user_prompt
                )
            else:
                return await self._generate_non_streaming(
                    resolved_model, max_tok, temp, system_prompt, user_prompt
                )

        except anthropic.RateLimitError as e:
            logger.warning(f"Claude rate limit: {e}")
            # Extract retry_after if available from response headers
            retry_after = getattr(e, 'retry_after', None)
            raise ProviderRateLimitError("claude", str(e), retry_after=retry_after)
        except anthropic.APIError as e:
            logger.error(f"Claude API error: {e}")
            raise

    async def _generate_non_streaming(
        self,
        model: str,
        max_tokens: int,
        temperature: float,
        system_prompt: str,
        user_prompt: str,
    ) -> ProviderResponse:
        """Non-streaming generation for faster models."""
        # Use structured system prompt with cache_control for prompt caching
        # This allows Anthropic to cache repeated system prompts across calls
        response = await asyncio.wait_for(
            self.client.messages.create(
                model=model,
                max_tokens=max_tokens,
                temperature=temperature,
                system=[{
                    "type": "text",
                    "text": system_prompt,
                    "cache_control": {"type": "ephemeral"}
                }],
                messages=[{"role": "user", "content": user_prompt}],
            ),
            timeout=self.config.timeout,
        )

        # Extract content
        content = ""
        for block in response.content:
            if hasattr(block, "text"):
                content += block.text

        # Extract token usage
        usage = TokenUsage(
            input_tokens=response.usage.input_tokens,
            output_tokens=response.usage.output_tokens,
            cache_creation_input_tokens=getattr(
                response.usage, "cache_creation_input_tokens", 0
            ),
            cache_read_input_tokens=getattr(
                response.usage, "cache_read_input_tokens", 0
            ),
        )

        # Log cache metrics for visibility
        if usage.cache_read_input_tokens > 0:
            logger.info(
                f"Cache HIT: {usage.cache_read_input_tokens:,} tokens read from cache "
                f"({model})"
            )
        if usage.cache_creation_input_tokens > 0:
            logger.debug(
                f"Cache WRITE: {usage.cache_creation_input_tokens:,} tokens cached "
                f"({model})"
            )

        return ProviderResponse(
            content=content,
            token_usage=usage,
            model=model,
            provider=self.provider_name,
        )

    async def _generate_streaming(
        self,
        model: str,
        max_tokens: int,
        temperature: float,
        system_prompt: str,
        user_prompt: str,
    ) -> ProviderResponse:
        """Streaming generation for slow models like Opus."""
        logger.debug(f"Using streaming for {model}")

        content_parts = []
        input_tokens = 0
        output_tokens = 0
        cache_creation_tokens = 0
        cache_read_tokens = 0

        # Use structured system prompt with cache_control for prompt caching
        async with self.client.messages.stream(
            model=model,
            max_tokens=max_tokens,
            temperature=temperature,
            system=[{
                "type": "text",
                "text": system_prompt,
                "cache_control": {"type": "ephemeral"}
            }],
            messages=[{"role": "user", "content": user_prompt}],
        ) as stream:
            async for text in stream.text_stream:
                content_parts.append(text)

            # Get final message for usage stats
            final_message = await stream.get_final_message()
            input_tokens = final_message.usage.input_tokens
            output_tokens = final_message.usage.output_tokens
            cache_creation_tokens = getattr(
                final_message.usage, "cache_creation_input_tokens", 0
            )
            cache_read_tokens = getattr(
                final_message.usage, "cache_read_input_tokens", 0
            )

        content = "".join(content_parts)

        usage = TokenUsage(
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cache_creation_input_tokens=cache_creation_tokens,
            cache_read_input_tokens=cache_read_tokens,
        )

        # Log cache metrics for visibility
        if usage.cache_read_input_tokens > 0:
            logger.info(
                f"Cache HIT: {usage.cache_read_input_tokens:,} tokens read from cache "
                f"({model})"
            )
        if usage.cache_creation_input_tokens > 0:
            logger.debug(
                f"Cache WRITE: {usage.cache_creation_input_tokens:,} tokens cached "
                f"({model})"
            )

        return ProviderResponse(
            content=content,
            token_usage=usage,
            model=model,
            provider=self.provider_name,
        )

    async def test_connection(self) -> bool:
        """Test Claude connection with a minimal request."""
        try:
            response = await self.client.messages.create(
                model="claude-3-haiku-20240307",
                max_tokens=10,
                messages=[{"role": "user", "content": "Hi"}],
            )
            return bool(response.content)
        except Exception as e:
            logger.error(f"Claude connection test failed: {e}")
            return False
