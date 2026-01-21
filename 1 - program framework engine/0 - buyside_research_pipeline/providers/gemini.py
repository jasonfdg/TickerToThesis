"""
Gemini Provider
===============
Google Gemini API wrapper using the new google-genai package.
"""

import asyncio
import logging
import os
from typing import Optional

from google import genai

from .base import BaseProvider, ProviderConfig, ProviderResponse

try:
    from ..models import TokenUsage
except ImportError:
    from models import TokenUsage

logger = logging.getLogger(__name__)


class GeminiProvider(BaseProvider):
    """Google Gemini provider implementation using google-genai."""

    provider_name = "gemini"

    # Model aliases - using latest available models
    MODELS = {
        "gemini-pro": "gemini-pro-latest",
        "gemini-1.5-pro": "gemini-2.5-pro",  # Map 1.5 requests to 2.5
        "gemini-2.5-pro": "gemini-2.5-pro",
        "gemini-flash": "gemini-2.5-flash",
        "gemini-1.5-flash": "gemini-2.5-flash",
        "gemini-2.5-flash": "gemini-2.5-flash",
        "gemini-2.0-flash": "gemini-2.0-flash",
    }

    def __init__(self, config: Optional[ProviderConfig] = None):
        super().__init__(config)
        api_key = self.config.api_key or os.getenv("GOOGLE_API_KEY")
        self.client = genai.Client(api_key=api_key)

    def _resolve_model(self, model: Optional[str]) -> str:
        """Resolve model alias to full model name."""
        if model is None:
            model = self.config.model or "gemini-2.5-pro"
        resolved = self.MODELS.get(model, model)
        # Ensure model has correct prefix
        if not resolved.startswith("models/"):
            resolved = f"models/{resolved}"
        return resolved

    async def generate(
        self,
        system_prompt: str,
        user_prompt: str,
        model: Optional[str] = None,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
    ) -> ProviderResponse:
        """Generate completion using Gemini."""
        resolved_model = self._resolve_model(model)
        max_tok = max_tokens or self.config.max_tokens
        temp = temperature if temperature is not None else self.config.temperature

        try:
            # Combine system prompt and user prompt
            full_prompt = f"{system_prompt}\n\n---\n\n{user_prompt}"

            # Create generation config
            gen_config = genai.types.GenerateContentConfig(
                max_output_tokens=max_tok,
                temperature=temp,
            )

            # Run in executor since genai client is synchronous
            loop = asyncio.get_event_loop()
            response = await asyncio.wait_for(
                loop.run_in_executor(
                    None,
                    lambda: self.client.models.generate_content(
                        model=resolved_model,
                        contents=full_prompt,
                        config=gen_config,
                    ),
                ),
                timeout=self.config.timeout,
            )

            # Extract content
            content = response.text if response.text else ""

            # Extract token usage
            input_tokens = 0
            output_tokens = 0
            if hasattr(response, "usage_metadata") and response.usage_metadata:
                input_tokens = getattr(response.usage_metadata, "prompt_token_count", 0) or 0
                output_tokens = getattr(response.usage_metadata, "candidates_token_count", 0) or 0

            usage = TokenUsage(
                input_tokens=input_tokens,
                output_tokens=output_tokens,
            )

            return ProviderResponse(
                content=content,
                token_usage=usage,
                model=resolved_model,
                provider=self.provider_name,
            )

        except Exception as e:
            logger.error(f"Gemini API error: {e}")
            raise

    async def test_connection(self) -> bool:
        """Test Gemini connection with a minimal request."""
        try:
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None,
                lambda: self.client.models.generate_content(
                    model="models/gemini-2.5-flash",
                    contents="Hi",
                ),
            )
            return bool(response.text)
        except Exception as e:
            logger.error(f"Gemini connection test failed: {e}")
            return False
