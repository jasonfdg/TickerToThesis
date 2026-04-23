"""
Providers Module
================
Multi-provider AI abstraction for the TickerToThesis pipeline.

Architecture:
- Analysts 1-6: Claude CLI Sonnet (Max subscription, consistent reasoning)
- RD Reviews 1-6: Kimi K2 via OpenRouter (adversarial cross-model voice)
- Source Scout: Perplexity Sonar via OpenRouter (real web search)
- Source Summary: Claude CLI Sonnet (JSON extraction)
- Synthesis: Claude CLI Sonnet (merged synthesis + polish)
- Human Readable: Claude Sonnet (legacy polish step, preserves depth)
"""

import asyncio
import logging
from dataclasses import dataclass
from enum import Enum
from typing import Dict, List, Optional, Tuple

from .base import BaseProvider, ProviderConfig, ProviderResponse, ProviderRateLimitError
from .claude import ClaudeProvider
from .claude_cli import ClaudeCliProvider
from .openai_provider import OpenAIProvider
from .openai_cli import OpenAICliProvider
from .gemini import GeminiProvider
from .gemini_cli import GeminiCliProvider
from .perplexity import PerplexityProvider
from .perplexity_cli import PerplexityCliProvider
from .openrouter import OpenRouterProvider

try:
    from ..models import AgentRole, TokenUsage
except ImportError:
    from models import AgentRole, TokenUsage

logger = logging.getLogger(__name__)

__all__ = [
    "ProviderFactory",
    "ProviderConfig",
    "ProviderResponse",
    "ProviderRateLimitError",
    "BaseProvider",
    # API providers
    "ClaudeProvider",
    "OpenAIProvider",
    "GeminiProvider",
    "PerplexityProvider",
    "OpenRouterProvider",
    # CLI providers (stubs - not yet implemented except Claude)
    "ClaudeCliProvider",
    "OpenAICliProvider",
    "GeminiCliProvider",
    "PerplexityCliProvider",
    # Routing configs
    "ANALYST_PROVIDERS",
    "ROLE_PROVIDERS",
]


class ProviderType(Enum):
    """Available provider types."""
    # API-based providers
    CLAUDE = "claude"
    OPENAI = "openai"
    GEMINI = "gemini"
    PERPLEXITY = "perplexity"
    OPENROUTER = "openrouter"      # Gateway to Kimi K2, Perplexity Sonar, etc.
    # CLI-based providers (subscription, no per-token costs)
    CLAUDE_CLI = "claude-cli"      # Implemented - Max subscription
    OPENAI_CLI = "openai-cli"      # Stub - not yet implemented
    GEMINI_CLI = "gemini-cli"      # Stub - not yet implemented
    PERPLEXITY_CLI = "perplexity-cli"  # Stub - not yet implemented


# Analyst type -> (provider, model) mapping
# All 6 analysts: Claude CLI Sonnet (Max subscription, no API cost)
ANALYST_PROVIDERS: Dict[int, Tuple[str, str]] = {
    1: ("claude-cli", "sonnet"),       # Quality Compounders
    2: ("claude-cli", "sonnet"),       # Imaginative Growth
    3: ("claude-cli", "sonnet"),       # Fundamental L/S
    4: ("claude-cli", "sonnet"),       # Deep Value
    5: ("claude-cli", "sonnet"),       # Event-Driven
    6: ("claude-cli", "sonnet"),       # Macro-Tactical
}


# Role -> (provider, model) mapping for non-analyst roles.
# These defaults are consulted when an AgentCall is built without an explicit
# provider. They must stay in sync with ROLE_PROVIDER_CONFIG / RD_REVIEW_PROVIDER_CONFIG
# in config.py, which is the authoritative source for runtime routing.
ROLE_PROVIDERS: Dict[AgentRole, Tuple[str, str]] = {
    AgentRole.RD_REVIEW: ("openrouter", "moonshotai/kimi-k2"),  # Kimi K2 via OpenRouter
    AgentRole.RD_SYNTHESIS: ("claude-cli", "sonnet"),           # Claude Sonnet via CLI
    AgentRole.SOURCE_SUMMARY: ("claude-cli", "sonnet"),         # Claude Sonnet for JSON extraction
    AgentRole.HUMAN_READABLE: ("claude", "sonnet"),             # Legacy polish step
    AgentRole.SOURCE_SCOUT: ("openrouter", "perplexity/sonar"), # Perplexity Sonar via OpenRouter
}


@dataclass
class ProviderStats:
    """Statistics for a provider's usage."""
    calls: int = 0
    total_input_tokens: int = 0
    total_output_tokens: int = 0
    errors: int = 0

    @property
    def total_tokens(self) -> int:
        return self.total_input_tokens + self.total_output_tokens


class ProviderFactory:
    """
    Factory for creating and managing AI providers.

    Handles provider instantiation, caching, and routing based on
    analyst type and role configurations.
    """

    def __init__(self, configs: Optional[Dict[str, ProviderConfig]] = None):
        """
        Initialize the factory.

        Args:
            configs: Optional dict of provider-specific configs
        """
        self._configs = configs or {}
        self._providers: Dict[str, BaseProvider] = {}
        self._stats: Dict[str, ProviderStats] = {}

    def _get_config(self, provider_type: str) -> ProviderConfig:
        """Get config for a provider, using defaults if not specified."""
        return self._configs.get(provider_type, ProviderConfig())

    def get_provider(self, provider_type: str) -> BaseProvider:
        """
        Get or create a provider instance.

        Args:
            provider_type: One of 'claude', 'openai', 'gemini', 'perplexity', 'openrouter'

        Returns:
            Provider instance
        """
        if provider_type not in self._providers:
            config = self._get_config(provider_type)

            # API providers
            if provider_type == "claude":
                self._providers[provider_type] = ClaudeProvider(config)
            elif provider_type == "openai":
                self._providers[provider_type] = OpenAIProvider(config)
            elif provider_type == "gemini":
                self._providers[provider_type] = GeminiProvider(config)
            elif provider_type == "perplexity":
                self._providers[provider_type] = PerplexityProvider(config)
            elif provider_type == "openrouter":
                self._providers[provider_type] = OpenRouterProvider(config)
            # CLI providers
            elif provider_type == "claude-cli":
                self._providers[provider_type] = ClaudeCliProvider(config)
            elif provider_type == "openai-cli":
                self._providers[provider_type] = OpenAICliProvider(config)
            elif provider_type == "gemini-cli":
                self._providers[provider_type] = GeminiCliProvider(config)
            elif provider_type == "perplexity-cli":
                self._providers[provider_type] = PerplexityCliProvider(config)
            else:
                raise ValueError(f"Unknown provider type: {provider_type}")

            self._stats[provider_type] = ProviderStats()

        return self._providers[provider_type]

    def get_analyst_provider(self, investing_type_id: int) -> Tuple[BaseProvider, str]:
        """
        Get the provider and model for an analyst type.

        Args:
            investing_type_id: 1-6 analyst type

        Returns:
            Tuple of (provider, model_name)
        """
        if investing_type_id not in ANALYST_PROVIDERS:
            raise ValueError(f"Invalid investing type: {investing_type_id}")

        provider_type, model = ANALYST_PROVIDERS[investing_type_id]
        return self.get_provider(provider_type), model

    def get_role_provider(self, role: AgentRole) -> Tuple[BaseProvider, str]:
        """
        Get the provider and model for a role.

        Args:
            role: Agent role

        Returns:
            Tuple of (provider, model_name)
        """
        if role == AgentRole.ANALYST:
            raise ValueError("Use get_analyst_provider for analysts")

        if role not in ROLE_PROVIDERS:
            # Default to Claude Sonnet for unknown roles
            return self.get_provider("claude"), "sonnet"

        provider_type, model = ROLE_PROVIDERS[role]
        return self.get_provider(provider_type), model

    async def generate(
        self,
        provider_type: str,
        model: str,
        system_prompt: str,
        user_prompt: str,
        **kwargs,
    ) -> ProviderResponse:
        """
        Generate a completion using the specified provider.

        Args:
            provider_type: Provider to use
            model: Model name/alias
            system_prompt: System instructions
            user_prompt: User message
            **kwargs: Additional arguments passed to provider

        Returns:
            ProviderResponse
        """
        provider = self.get_provider(provider_type)

        try:
            response = await provider.generate(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                model=model,
                **kwargs,
            )

            # Update stats
            if provider_type in self._stats:
                self._stats[provider_type].calls += 1
                self._stats[provider_type].total_input_tokens += response.token_usage.input_tokens
                self._stats[provider_type].total_output_tokens += response.token_usage.output_tokens

            return response

        except Exception as e:
            if provider_type in self._stats:
                self._stats[provider_type].errors += 1
            raise

    async def generate_for_analyst(
        self,
        investing_type_id: int,
        system_prompt: str,
        user_prompt: str,
        **kwargs,
    ) -> ProviderResponse:
        """
        Generate a completion for an analyst type.

        Automatically routes to the correct provider based on type.
        """
        provider_type, model = ANALYST_PROVIDERS[investing_type_id]
        return await self.generate(
            provider_type=provider_type,
            model=model,
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            **kwargs,
        )

    async def generate_for_role(
        self,
        role: AgentRole,
        system_prompt: str,
        user_prompt: str,
        **kwargs,
    ) -> ProviderResponse:
        """
        Generate a completion for a specific role.

        Automatically routes to the correct provider based on role.
        """
        provider_type, model = ROLE_PROVIDERS.get(
            role, ("claude", "sonnet")
        )
        return await self.generate(
            provider_type=provider_type,
            model=model,
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            **kwargs,
        )

    async def test_all_connections(self) -> Dict[str, bool]:
        """Test connections to all providers."""
        results = {}

        for provider_type in ["claude", "openai", "gemini", "perplexity"]:
            try:
                provider = self.get_provider(provider_type)
                results[provider_type] = await provider.test_connection()
            except Exception as e:
                logger.error(f"Failed to test {provider_type}: {e}")
                results[provider_type] = False

        return results

    def get_stats(self) -> Dict[str, ProviderStats]:
        """Get usage statistics for all providers."""
        return dict(self._stats)

    def get_cost_estimate(self) -> Dict[str, float]:
        """
        Estimate costs based on token usage.

        Approximate pricing (per 1M tokens):
        - Claude Sonnet: $3 input, $15 output
        - Claude Opus: $15 input, $75 output
        - Claude Haiku: $0.25 input, $1.25 output
        - GPT-4o: $2.50 input, $10 output
        - Gemini 1.5 Pro: $3.50 input, $10.50 output
        - Perplexity Sonar: $5 input, $5 output
        """
        # Simplified cost calculation (uses Sonnet rates for Claude by default)
        COSTS = {
            "claude": (3.0, 15.0),      # input, output per 1M
            "openai": (2.5, 10.0),
            "gemini": (3.5, 10.5),
            "perplexity": (5.0, 5.0),
        }

        costs = {}
        for provider_type, stats in self._stats.items():
            input_rate, output_rate = COSTS.get(provider_type, (3.0, 15.0))
            input_cost = (stats.total_input_tokens / 1_000_000) * input_rate
            output_cost = (stats.total_output_tokens / 1_000_000) * output_rate
            costs[provider_type] = input_cost + output_cost

        costs["total"] = sum(costs.values())
        return costs

    def close_all(self):
        """Close all provider connections."""
        for provider in self._providers.values():
            provider.close()
        self._providers.clear()
