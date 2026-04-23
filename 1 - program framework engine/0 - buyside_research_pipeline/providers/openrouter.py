"""
OpenRouter Provider
===================
OpenRouter API wrapper. Routes requests to any upstream model (Kimi K2,
Perplexity Sonar, Gemini, etc.) via OpenRouter's OpenAI-compatible
chat/completions endpoint.

Model strings pass through verbatim in `provider/model` form, e.g.
``moonshotai/kimi-k2`` or ``perplexity/sonar``.

Auth: reads ``OPENROUTER_KIMI_KEY`` (the machine-level env var used by this
project), falling back to ``OPENROUTER_API_KEY`` for portability.
"""

import asyncio
import logging
import os
from typing import Optional

import httpx

from .base import BaseProvider, ProviderConfig, ProviderResponse, ProviderRateLimitError

try:
    from ..models import TokenUsage
except ImportError:
    from models import TokenUsage

logger = logging.getLogger(__name__)


class OpenRouterProvider(BaseProvider):
    """OpenRouter provider — OpenAI-compatible chat completions gateway."""

    provider_name = "openrouter"

    API_URL = "https://openrouter.ai/api/v1/chat/completions"

    # Identifies this client on OpenRouter's dashboards.
    DEFAULT_REFERER = "https://tickertothesis.com"
    DEFAULT_TITLE = "TickerToThesis"

    def __init__(self, config: Optional[ProviderConfig] = None):
        super().__init__(config)
        self.api_key = (
            self.config.api_key
            or os.getenv("OPENROUTER_KIMI_KEY")
            or os.getenv("OPENROUTER_API_KEY")
        )
        self._client = None

    @property
    def client(self) -> httpx.AsyncClient:
        """Lazy-init async client."""
        if self._client is None:
            if not self.api_key:
                raise RuntimeError(
                    "OpenRouter API key missing. Set OPENROUTER_KIMI_KEY "
                    "(or OPENROUTER_API_KEY) in the environment."
                )
            self._client = httpx.AsyncClient(
                timeout=self.config.timeout,
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                    "HTTP-Referer": self.DEFAULT_REFERER,
                    "X-Title": self.DEFAULT_TITLE,
                },
            )
        return self._client

    def _resolve_model(self, model: Optional[str]) -> str:
        """Resolve model name. OpenRouter uses ``vendor/model`` strings verbatim."""
        if model is None:
            model = self.config.model or "moonshotai/kimi-k2"
        return model

    async def generate(
        self,
        system_prompt: str,
        user_prompt: str,
        model: Optional[str] = None,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
    ) -> ProviderResponse:
        """Generate completion via OpenRouter."""
        resolved_model = self._resolve_model(model)
        max_tok = max_tokens or self.config.max_tokens
        temp = temperature if temperature is not None else self.config.temperature

        payload = {
            "model": resolved_model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "max_tokens": max_tok,
            "temperature": temp,
        }

        try:
            response = await self.client.post(self.API_URL, json=payload)
            response.raise_for_status()
            data = response.json()

            message = data["choices"][0]["message"]
            content = message.get("content", "") or ""

            # Perplexity Sonar (and other search-capable models) return citations
            # under message.annotations[].url_citation per OpenAI's web_search
            # format. Also accept a top-level `citations` list (Sonar sometimes
            # echoes its native shape through). Append both to the content so
            # downstream source extraction can find the URLs.
            citation_urls = []
            for ann in message.get("annotations") or []:
                url = (ann.get("url_citation") or {}).get("url")
                if url:
                    citation_urls.append(url)
            for cite in data.get("citations") or []:
                url = cite if isinstance(cite, str) else cite.get("url")
                if url and url not in citation_urls:
                    citation_urls.append(url)

            if citation_urls:
                content += "\n\n## Sources\n"
                for i, url in enumerate(citation_urls, 1):
                    content += f"{i}. {url}\n"

            usage_data = data.get("usage", {}) or {}
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
            if e.response.status_code == 429:
                logger.warning(f"OpenRouter rate limit: {e}")
                retry_after = e.response.headers.get("retry-after")
                retry_seconds = float(retry_after) if retry_after else None
                raise ProviderRateLimitError("openrouter", str(e), retry_after=retry_seconds)
            logger.error(
                f"OpenRouter HTTP error: {e.response.status_code} - {e.response.text}"
            )
            raise

    async def test_connection(self) -> bool:
        """Test OpenRouter connection with a minimal Kimi K2 request."""
        try:
            response = await self.generate(
                system_prompt="You are a helpful assistant.",
                user_prompt="What is 2+2?",
                model="moonshotai/kimi-k2",
                max_tokens=50,
            )
            return bool(response.content)
        except Exception as e:
            logger.error(f"OpenRouter connection test failed: {e}")
            return False

    def close(self):
        """Close the HTTP client."""
        if self._client:
            asyncio.create_task(self._client.aclose())
            self._client = None
