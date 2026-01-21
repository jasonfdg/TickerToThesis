"""
Providers Module
================
Multi-provider AI abstraction for the TickerToThesis pipeline.

Architecture:
- Analysts 1-2: Claude Sonnet (nuanced reasoning, creative thesis)
- Analysts 3-4: GPT-4o (quantitative analysis, contrarian thinking)
- Analysts 5-6: Gemini 1.5 Pro (large context, catalyst analysis)
- RD Reviews: Claude Sonnet (consistent critique quality)
- Source Scout: Perplexity (real web search)
- Source Summary: Claude Haiku (fast JSON extraction)
- Synthesis: Claude Opus (highest quality judgment)
- Polish: Claude Haiku (mechanical text editing)
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
from .gemini import GeminiProvider
from .perplexity import PerplexityProvider

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
    "ClaudeProvider",
    "ClaudeCliProvider",
    "OpenAIProvider",
    "GeminiProvider",
    "PerplexityProvider",
    "ANALYST_PROVIDERS",
    "ROLE_PROVIDERS",
]


class ProviderType(Enum):
    """Available provider types."""
    CLAUDE = "claude"
    CLAUDE_CLI = "claude-cli"  # CLI-based execution (Max subscription)
    OPENAI = "openai"
    GEMINI = "gemini"
    PERPLEXITY = "perplexity"


# Analyst type -> (provider, model) mapping
# Types 1-3: Claude Sonnet (nuanced, creative)
# Types 4-6: GPT-4o (quantitative, contrarian)
# Gemini excluded from analyst roles (used for synthesis only)
ANALYST_PROVIDERS: Dict[int, Tuple[str, str]] = {
    1: ("claude", "sonnet"),           # Quality Compounders - nuanced reasoning
    2: ("claude", "sonnet"),           # Imaginative Growth - creative thesis
    3: ("claude", "sonnet"),           # Fundamental L/S - nuanced analysis
    4: ("openai", "gpt-4o"),           # Deep Value - contrarian
    5: ("openai", "gpt-4o"),           # Event-Driven - catalyst analysis
    6: ("openai", "gpt-4o"),           # Macro-Tactical - quantitative
}


# Role -> (provider, model) mapping for non-analyst roles
# NOTE: These should match ROLE_PROVIDER_CONFIG in config.py
ROLE_PROVIDERS: Dict[AgentRole, Tuple[str, str]] = {
    AgentRole.RD_REVIEW: ("claude", "sonnet"),           # Default for non-typed RD calls (see RD_REVIEW_PROVIDER_CONFIG)
    AgentRole.RD_SYNTHESIS: ("gemini", "gemini-2.5-pro"),  # Gemini for synthesis (1-step, no polish)
    AgentRole.SOURCE_SUMMARY: ("openai", "gpt-4o-mini"),   # Best JSON validity from benchmark
    AgentRole.HUMAN_READABLE: ("claude", "sonnet"),      # (Deprecated - synthesis includes polish)
    AgentRole.SOURCE_SCOUT: ("perplexity", "sonar"),     # Real web search
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
            provider_type: One of 'claude', 'openai', 'gemini', 'perplexity'

        Returns:
            Provider instance
        """
        if provider_type not in self._providers:
            config = self._get_config(provider_type)

            if provider_type == "claude":
                self._providers[provider_type] = ClaudeProvider(config)
            elif provider_type == "claude-cli":
                self._providers[provider_type] = ClaudeCliProvider(config)
            elif provider_type == "openai":
                self._providers[provider_type] = OpenAIProvider(config)
            elif provider_type == "gemini":
                self._providers[provider_type] = GeminiProvider(config)
            elif provider_type == "perplexity":
                self._providers[provider_type] = PerplexityProvider(config)
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
