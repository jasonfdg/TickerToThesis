"""
Base Provider
=============
Abstract base class for AI provider implementations.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional, Tuple

try:
    from ..models import TokenUsage
except ImportError:
    from models import TokenUsage


class ProviderRateLimitError(Exception):
    """Unified rate limit exception across all providers.

    Raised when any provider hits a rate limit, allowing the caller
    to implement consistent fallback behavior.
    """

    def __init__(
        self,
        provider: str,
        message: str,
        retry_after: Optional[float] = None
    ):
        """
        Args:
            provider: Name of the provider that hit the rate limit
            message: Error message from the provider
            retry_after: Seconds until retry (if known from response headers)
        """
        self.provider = provider
        self.retry_after = retry_after
        super().__init__(f"{provider} rate limit: {message}")


@dataclass
class ProviderConfig:
    """Configuration for a provider."""

    api_key: Optional[str] = None
    model: str = ""
    max_tokens: int = 16000
    temperature: float = 0.7
    timeout: float = 300.0


@dataclass
class ProviderResponse:
    """Normalized response from any provider."""

    content: str
    token_usage: TokenUsage
    model: str
    provider: str
    raw_response: Optional[dict] = None


class BaseProvider(ABC):
    """Abstract base class for AI providers."""

    provider_name: str = "base"

    def __init__(self, config: Optional[ProviderConfig] = None):
        self.config = config or ProviderConfig()

    @abstractmethod
    async def generate(
        self,
        system_prompt: str,
        user_prompt: str,
        model: Optional[str] = None,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
    ) -> ProviderResponse:
        """
        Generate a completion from the provider.

        Args:
            system_prompt: System instructions
            user_prompt: User message
            model: Override default model
            max_tokens: Override default max tokens
            temperature: Override default temperature

        Returns:
            ProviderResponse with content and usage
        """
        pass

    @abstractmethod
    async def test_connection(self) -> bool:
        """Test that the provider is configured correctly."""
        pass

    def close(self):
        """Clean up resources."""
        pass
