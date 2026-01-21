"""
Perplexity Provider
==================
Perplexity API wrapper for web search capabilities.
"""

import asyncio
import logging
import os
from typing import Optional

import httpx

from .base import BaseProvider, ProviderConfig, ProviderResponse

try:
    from ..models import TokenUsage
except ImportError:
    from models import TokenUsage

logger = logging.getLogger(__name__)


class PerplexityProvider(BaseProvider):
    """Perplexity provider implementation for web search."""

    provider_name = "perplexity"

    # Model aliases
    MODELS = {
        "sonar": "sonar",
        "sonar-pro": "sonar-pro",
        "sonar-reasoning": "sonar-reasoning-pro",
    }

    API_URL = "https://api.perplexity.ai/chat/completions"

    def __init__(self, config: Optional[ProviderConfig] = None):
        super().__init__(config)
        self.api_key = self.config.api_key or os.getenv("PERPLEXITY_API_KEY")
        self._client = None

    @property
    def client(self) -> httpx.AsyncClient:
        """Lazy-init async client."""
        if self._client is None:
            self._client = httpx.AsyncClient(
                timeout=self.config.timeout,
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
            )
        return self._client

    def _resolve_model(self, model: Optional[str]) -> str:
        """Resolve model alias to full model name."""
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
        """Generate completion using Perplexity with web search."""
        resolved_model = self._resolve_model(model)
        max_tok = max_tokens or self.config.max_tokens
        temp = temperature if temperature is not None else self.config.temperature

        try:
            payload = {
                "model": resolved_model,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                "max_tokens": max_tok,
                "temperature": temp,
                "return_citations": True,
                "return_related_questions": False,
            }

            response = await self.client.post(self.API_URL, json=payload)
            response.raise_for_status()
            data = response.json()

            # Extract content
            content = data["choices"][0]["message"]["content"]

            # Append citations if available
            if "citations" in data:
                citations = data["citations"]
                if citations:
                    content += "\n\n## Sources\n"
                    for i, citation in enumerate(citations, 1):
                        content += f"{i}. {citation}\n"

            # Extract token usage
            usage_data = data.get("usage", {})
            usage = TokenUsage(
                input_tokens=usage_data.get("prompt_tokens", 0),
                output_tokens=usage_data.get("completion_tokens", 0),
            )

            return ProviderResponse(
                content=content,
                token_usage=usage,
                model=resolved_model,
                provider=self.provider_name,
                raw_response=data,
            )

        except httpx.HTTPStatusError as e:
            logger.error(f"Perplexity HTTP error: {e.response.status_code} - {e.response.text}")
            raise
        except Exception as e:
            logger.error(f"Perplexity API error: {e}")
            raise

    async def search(
        self,
        query: str,
        max_results: int = 10,
    ) -> ProviderResponse:
        """
        Perform a web search using Perplexity.

        This is a convenience method that wraps generate() with
        search-optimized prompts.
        """
        system_prompt = (
            "You are a research assistant. Search the web and provide "
            "comprehensive, factual information with citations. "
            "Focus on primary sources when available."
        )

        return await self.generate(
            system_prompt=system_prompt,
            user_prompt=query,
            model="sonar",
            temperature=0.3,  # Lower temp for factual search
        )

    async def test_connection(self) -> bool:
        """Test Perplexity connection with a minimal request."""
        try:
            response = await self.generate(
                system_prompt="You are a helpful assistant.",
                user_prompt="What is 2+2?",
                model="sonar",
                max_tokens=50,
            )
            return bool(response.content)
        except Exception as e:
            logger.error(f"Perplexity connection test failed: {e}")
            return False

    def close(self):
        """Close the HTTP client."""
        if self._client:
            asyncio.create_task(self._client.aclose())
            self._client = None
