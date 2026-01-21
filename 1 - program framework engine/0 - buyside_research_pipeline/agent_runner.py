"""
Agent Runner
============
Multi-provider async API wrapper with parallel execution and retry logic.

Supports:
- Claude (Sonnet, Opus, Haiku)
- OpenAI (GPT-4o)
- Google Gemini (1.5 Pro)
- Perplexity (Sonar for web search)
"""

import asyncio
import logging
import random
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple

import anthropic

try:
    from .config import (
        PipelineConfig, ANALYST_PROVIDER_CONFIG, ROLE_PROVIDER_CONFIG,
        COMPONENT_OVERRIDES, get_effective_provider
    )
    from .models import AgentReport, AgentRole, TokenUsage
    from .providers import ProviderFactory, ProviderResponse
    from .providers.base import ProviderRateLimitError
except ImportError:
    from config import (
        PipelineConfig, ANALYST_PROVIDER_CONFIG, ROLE_PROVIDER_CONFIG,
        COMPONENT_OVERRIDES, get_effective_provider
    )
    from models import AgentReport, AgentRole, TokenUsage
    from providers import ProviderFactory, ProviderResponse
    from providers.base import ProviderRateLimitError

logger = logging.getLogger(__name__)


@dataclass
class AgentCall:
    """Configuration for a single agent API call."""

    role: AgentRole
    system_prompt: str
    user_prompt: str
    investing_type_id: Optional[int] = None
    iteration: int = 1
    identifier: str = ""
    # Multi-provider fields
    provider: Optional[str] = None  # 'claude', 'openai', 'gemini', 'perplexity'
    model: Optional[str] = None     # Provider-specific model name

    def __post_init__(self):
        if not self.identifier:
            if self.investing_type_id is not None:
                self.identifier = f"{self.role.value}_type_{self.investing_type_id}_v{self.iteration}"
            else:
                self.identifier = f"{self.role.value}_v{self.iteration}"

        # Auto-assign provider/model based on role and type
        if self.provider is None or self.model is None:
            self._assign_provider_model()

    def _assign_provider_model(self):
        """Auto-assign provider and model based on role configuration.

        Priority order:
        1. Explicit provider/model set on AgentCall
        2. COMPONENT_OVERRIDES in config.py
        3. PROVIDER_MODE substitution (api->cli for Claude)
        4. Default routing from ANALYST_PROVIDER_CONFIG / ROLE_PROVIDER_CONFIG
        """
        # Build component identifier for override lookup
        if self.role == AgentRole.ANALYST and self.investing_type_id is not None:
            component = f"analyst_{self.investing_type_id}"
        elif self.role == AgentRole.RD_REVIEW and self.investing_type_id is not None:
            component = f"rd_review_{self.investing_type_id}"
        else:
            component = self.role.value  # e.g., "rd_synthesis", "source_scout"

        # Check for override (respects COMPONENT_OVERRIDES and PROVIDER_MODE)
        if component in COMPONENT_OVERRIDES:
            override = COMPONENT_OVERRIDES[component]
            self.provider = self.provider or override["provider"]
            self.model = self.model or override["model"]
            return

        # Use get_effective_provider which handles mode substitution
        effective_provider, effective_model = get_effective_provider(component, self.iteration)
        self.provider = self.provider or effective_provider
        self.model = self.model or effective_model


@dataclass
class ProviderHealth:
    """Tracks health state for a single provider."""

    is_rate_limited: bool = False
    rate_limit_until: Optional[datetime] = None
    consecutive_failures: int = 0

    def mark_rate_limited(self, cooldown_seconds: float = 60.0):
        """Mark provider as rate-limited with a cooldown period."""
        self.is_rate_limited = True
        self.rate_limit_until = datetime.now() + timedelta(seconds=cooldown_seconds)

    def is_available(self) -> bool:
        """Check if provider is available (not rate-limited or cooldown expired)."""
        if not self.is_rate_limited:
            return True
        if self.rate_limit_until and datetime.now() > self.rate_limit_until:
            self.is_rate_limited = False
            return True
        return False


class ProviderHealthTracker:
    """Tracks provider health and suggests fallbacks.

    Manages rate limit cooldowns and provides intelligent fallback
    suggestions when providers become unavailable.

    Fallback strategy:
    - Claude CLI is the primary fallback for ALL providers (unlimited with Max subscription)
    - Claude API is the last resort (only when CLI fails)
    - OpenAI/Gemini are NOT fallbacks for each other
    """

    # Fallback priority: CLI first (unlimited), then Claude API as last resort
    # OpenAI and Gemini are intentionally excluded - they fall back to Claude CLI only
    FALLBACK_CHAIN = ["claude", "claude-cli"]

    def __init__(self):
        self._health: Dict[str, ProviderHealth] = defaultdict(ProviderHealth)

    def mark_rate_limited(self, provider: str, retry_after: Optional[float] = None):
        """Mark a provider as rate-limited with optional cooldown from API."""
        cooldown = retry_after or 60.0
        self._health[provider].mark_rate_limited(cooldown)
        logger.warning(f"Provider {provider} rate-limited, cooldown {cooldown:.0f}s")

    def mark_success(self, provider: str):
        """Mark a successful call - resets failure counter."""
        self._health[provider].consecutive_failures = 0

    def mark_failure(self, provider: str):
        """Mark a failed call (non-rate-limit error)."""
        self._health[provider].consecutive_failures += 1

    def get_fallback(self, failed_provider: str, model: str) -> Optional[Tuple[str, str]]:
        """Get next available fallback provider and mapped model.

        Args:
            failed_provider: The provider that just failed
            model: The original model being used

        Returns:
            Tuple of (fallback_provider, fallback_model) or None if exhausted
        """
        for provider in self.FALLBACK_CHAIN:
            if provider == failed_provider:
                continue
            if self._health[provider].is_available():
                fallback_model = self._map_model(provider, model)
                return provider, fallback_model
        return None

    def _map_model(self, provider: str, original_model: str) -> str:
        """Map original model to equivalent for fallback provider.

        Args:
            provider: Target fallback provider
            original_model: Original model name/alias

        Returns:
            Equivalent model for the fallback provider
        """
        # Claude CLI uses same model names as Claude API
        if provider == "claude-cli":
            if "sonnet" in original_model.lower():
                return "sonnet"
            if "opus" in original_model.lower():
                return "opus"
            if "haiku" in original_model.lower():
                return "haiku"
            return "sonnet"  # default

        # Claude API
        if provider == "claude":
            if "gpt" in original_model.lower() or "gemini" in original_model.lower():
                return "sonnet"  # Map other providers to sonnet
            return original_model

        # OpenAI
        if provider == "openai":
            return "gpt-4o"

        # Gemini
        if provider == "gemini":
            return "gemini-2.5-pro"

        return original_model

    def get_shortest_cooldown(self) -> Optional[float]:
        """Get shortest remaining cooldown across all rate-limited providers.

        Returns:
            Seconds until first provider becomes available, or None if all available
        """
        now = datetime.now()
        cooldowns = []
        for provider, health in self._health.items():
            if health.is_rate_limited and health.rate_limit_until:
                remaining = (health.rate_limit_until - now).total_seconds()
                if remaining > 0:
                    cooldowns.append(remaining)
        return min(cooldowns) if cooldowns else None

    def get_status_summary(self) -> Dict[str, str]:
        """Get a summary of provider health status for logging."""
        now = datetime.now()
        summary = {}
        for provider in self.FALLBACK_CHAIN:
            health = self._health[provider]
            if health.is_rate_limited and health.rate_limit_until:
                remaining = (health.rate_limit_until - now).total_seconds()
                if remaining > 0:
                    summary[provider] = f"rate-limited ({remaining:.0f}s)"
                else:
                    summary[provider] = "available"
            else:
                summary[provider] = "available"
        return summary


class AgentRunner:
    """
    Async runner for Claude API calls with parallel execution support.

    Features:
    - Parallel execution via asyncio.gather()
    - Exponential backoff retry for rate limits
    - Token usage tracking
    - Configurable timeouts
    """

    def __init__(self, config: Optional[PipelineConfig] = None):
        self.config = config or PipelineConfig()
        self.client = anthropic.AsyncAnthropic()
        self._semaphore = asyncio.Semaphore(self.config.rate_limit_rpm // 2)

    async def _make_api_call(self, call: AgentCall) -> Tuple[str, TokenUsage]:
        """
        Make a single API call with retry logic.

        Returns:
            Tuple of (response_content, token_usage)
        """
        last_error = None

        for attempt in range(self.config.max_retries):
            try:
                async with self._semaphore:
                    response = await asyncio.wait_for(
                        self.client.messages.create(
                            model=self.config.model,
                            max_tokens=self.config.max_tokens,
                            temperature=self.config.temperature,
                            system=call.system_prompt,
                            messages=[{"role": "user", "content": call.user_prompt}],
                        ),
                        timeout=self.config.single_call_timeout,
                    )

                # Extract content
                content = ""
                for block in response.content:
                    if hasattr(block, "text"):
                        content += block.text

                # Extract token usage
                usage = TokenUsage.from_api_response(
                    {
                        "input_tokens": response.usage.input_tokens,
                        "output_tokens": response.usage.output_tokens,
                        "cache_creation_input_tokens": getattr(
                            response.usage, "cache_creation_input_tokens", 0
                        ),
                        "cache_read_input_tokens": getattr(
                            response.usage, "cache_read_input_tokens", 0
                        ),
                    }
                )

                logger.debug(
                    f"API call {call.identifier} completed: "
                    f"{usage.input_tokens} in, {usage.output_tokens} out"
                )

                return content, usage

            except anthropic.RateLimitError as e:
                last_error = e
                delay = min(
                    self.config.retry_base_delay * (2**attempt) + random.uniform(0, 1),
                    self.config.retry_max_delay,
                )
                logger.warning(
                    f"Rate limit hit for {call.identifier}, "
                    f"retrying in {delay:.1f}s (attempt {attempt + 1}/{self.config.max_retries})"
                )
                await asyncio.sleep(delay)

            except asyncio.TimeoutError as e:
                last_error = e
                logger.warning(
                    f"Timeout for {call.identifier} "
                    f"(attempt {attempt + 1}/{self.config.max_retries})"
                )
                if attempt < self.config.max_retries - 1:
                    await asyncio.sleep(self.config.retry_base_delay)

            except anthropic.APIError as e:
                last_error = e
                logger.error(f"API error for {call.identifier}: {e}")
                if attempt < self.config.max_retries - 1:
                    delay = self.config.retry_base_delay * (2**attempt)
                    await asyncio.sleep(delay)

        raise RuntimeError(
            f"Failed after {self.config.max_retries} attempts for {call.identifier}: {last_error}"
        )

    async def run_single(self, call: AgentCall) -> AgentReport:
        """
        Run a single agent call.

        Args:
            call: The AgentCall configuration

        Returns:
            AgentReport with the results
        """
        try:
            content, usage = await self._make_api_call(call)
            return AgentReport(
                role=call.role,
                investing_type_id=call.investing_type_id,
                iteration=call.iteration,
                content=content,
                token_usage=usage,
                timestamp=datetime.now(),
            )
        except Exception as e:
            logger.error(f"Error in {call.identifier}: {e}")
            return AgentReport(
                role=call.role,
                investing_type_id=call.investing_type_id,
                iteration=call.iteration,
                content="",
                token_usage=TokenUsage(),
                timestamp=datetime.now(),
                error=str(e),
            )

    async def run_parallel(self, calls: List[AgentCall]) -> Dict[str, AgentReport]:
        """
        Run multiple agent calls in parallel.

        Args:
            calls: List of AgentCall configurations

        Returns:
            Dict mapping call identifiers to AgentReports
        """
        if not calls:
            return {}

        logger.info(f"Running {len(calls)} calls in parallel")

        async def run_with_id(call: AgentCall) -> Tuple[str, AgentReport]:
            report = await self.run_single(call)
            return call.identifier, report

        try:
            results = await asyncio.wait_for(
                asyncio.gather(*[run_with_id(call) for call in calls], return_exceptions=True),
                timeout=self.config.parallel_batch_timeout,
            )
        except asyncio.TimeoutError:
            logger.error("Parallel batch timed out")
            results = []
            for call in calls:
                results.append(
                    (
                        call.identifier,
                        AgentReport(
                            role=call.role,
                            investing_type_id=call.investing_type_id,
                            iteration=call.iteration,
                            content="",
                            token_usage=TokenUsage(),
                            timestamp=datetime.now(),
                            error="Batch timeout",
                        ),
                    )
                )

        # Process results
        reports = {}
        for result in results:
            if isinstance(result, Exception):
                logger.error(f"Parallel call failed: {result}")
                continue
            identifier, report = result
            reports[identifier] = report

        # Log summary
        successes = sum(1 for r in reports.values() if r.is_success)
        total_tokens = sum(r.token_usage.total_tokens for r in reports.values())
        logger.info(
            f"Parallel batch complete: {successes}/{len(calls)} succeeded, "
            f"{total_tokens:,} total tokens"
        )

        return reports

    async def run_sequential(
        self,
        calls: List[AgentCall],
        delay_between: float = 5.0,
    ) -> Dict[str, AgentReport]:
        """
        Run multiple agent calls sequentially with delay between each.

        This is used when rate limits prevent parallel execution.

        Args:
            calls: List of AgentCall configurations
            delay_between: Seconds to wait between calls (default 5s)

        Returns:
            Dict mapping call identifiers to AgentReports
        """
        if not calls:
            return {}

        logger.info(f"Running {len(calls)} calls sequentially (rate limit safe)")

        reports = {}
        for i, call in enumerate(calls):
            logger.info(f"  [{i+1}/{len(calls)}] {call.identifier}...")
            report = await self.run_single(call)
            reports[call.identifier] = report

            if report.is_success:
                logger.info(f"    Done: {report.token_usage.total_tokens:,} tokens")
            else:
                logger.warning(f"    Failed: {report.error}")

            # Wait between calls to avoid rate limits (skip after last call)
            if i < len(calls) - 1:
                await asyncio.sleep(delay_between)

        # Log summary
        successes = sum(1 for r in reports.values() if r.is_success)
        total_tokens = sum(r.token_usage.total_tokens for r in reports.values())
        logger.info(
            f"Sequential batch complete: {successes}/{len(calls)} succeeded, "
            f"{total_tokens:,} total tokens"
        )

        return reports

    async def run_analyst_batch(
        self,
        calls: List[AgentCall],
    ) -> Dict[int, AgentReport]:
        """
        Run a batch of analyst calls (one per investing type).

        Args:
            calls: List of 6 AgentCalls (one per investing type)

        Returns:
            Dict mapping investing_type_id to AgentReport
        """
        # Use sequential execution to avoid rate limits
        # 30s delay needed for ~17K token calls at 10K tokens/min limit
        results = await self.run_sequential(calls, delay_between=30.0)

        # Convert to type_id -> report mapping
        by_type: Dict[int, AgentReport] = {}
        for identifier, report in results.items():
            if report.investing_type_id is not None:
                by_type[report.investing_type_id] = report

        return by_type

    async def run_rd_review_batch(
        self,
        calls: List[AgentCall],
    ) -> Dict[int, AgentReport]:
        """
        Run a batch of RD review calls (one per investing type).

        Args:
            calls: List of 6 AgentCalls (one per investing type)

        Returns:
            Dict mapping investing_type_id to AgentReport
        """
        # Same implementation as analyst batch
        return await self.run_analyst_batch(calls)

    def close(self):
        """Close the API client."""
        # AsyncAnthropic doesn't need explicit closing, but keeping for interface
        pass


def run_sync(coro):
    """Helper to run async code synchronously."""
    try:
        loop = asyncio.get_running_loop()
        # We're in an async context, can't use run()
        raise RuntimeError("Cannot run synchronously from async context")
    except RuntimeError:
        # No running loop, safe to use run()
        return asyncio.run(coro)


class MultiProviderRunner:
    """
    Multi-provider runner with true parallel execution.

    Routes calls to the appropriate provider based on agent type/role:
    - Analysts 1-2: Claude Sonnet
    - Analysts 3-4: GPT-4o
    - Analysts 5-6: Gemini 1.5 Pro
    - RD Reviews: Claude Sonnet
    - Synthesis: Claude Opus
    - Source Scout: Perplexity
    - Source Summary/Polish: Claude Haiku
    """

    def __init__(self, config: Optional[PipelineConfig] = None):
        self.config = config or PipelineConfig()
        self.provider_factory = ProviderFactory()
        self._semaphores: Dict[str, asyncio.Semaphore] = {}
        self._health_tracker = ProviderHealthTracker()

    def _get_semaphore(self, provider: str) -> asyncio.Semaphore:
        """Get or create a rate-limiting semaphore for a provider."""
        if provider not in self._semaphores:
            rpm = self.config.provider_rate_limits.get(provider, 50)
            # Allow concurrent requests up to half the rate limit
            self._semaphores[provider] = asyncio.Semaphore(max(1, rpm // 2))
        return self._semaphores[provider]

    async def _make_api_call(self, call: AgentCall) -> Tuple[str, TokenUsage]:
        """Make API call with automatic fallback on rate limits.

        Never gives up - if all providers are rate-limited, waits and retries
        until something works. This ensures the pipeline always completes.

        Fallback chain: Primary Provider → Claude CLI → Other APIs → Wait → Retry
        """
        provider = call.provider or "claude"
        model = call.model or "sonnet"
        original_provider, original_model = provider, model

        while True:  # Persistent retry loop - never give up
            providers_tried: set = set()
            current_provider, current_model = original_provider, original_model

            while True:  # Inner loop: try all available providers
                # Skip if already tried this provider in current round
                if current_provider in providers_tried:
                    fallback = self._health_tracker.get_fallback(current_provider, current_model)
                    if fallback and fallback[0] not in providers_tried:
                        current_provider, current_model = fallback
                        continue
                    else:
                        break  # Exhausted all options this round

                providers_tried.add(current_provider)

                # Check if provider is currently rate-limited
                if not self._health_tracker._health[current_provider].is_available():
                    logger.debug(f"Skipping {current_provider} (cooldown active)")
                    fallback = self._health_tracker.get_fallback(current_provider, current_model)
                    if fallback and fallback[0] not in providers_tried:
                        current_provider, current_model = fallback
                        continue
                    else:
                        break

                try:
                    semaphore = self._get_semaphore(current_provider)
                    async with semaphore:
                        response = await asyncio.wait_for(
                            self.provider_factory.generate(
                                provider_type=current_provider,
                                model=current_model,
                                system_prompt=call.system_prompt,
                                user_prompt=call.user_prompt,
                                max_tokens=self.config.max_tokens,
                                temperature=self.config.temperature,
                            ),
                            timeout=self.config.single_call_timeout,
                        )

                    self._health_tracker.mark_success(current_provider)
                    logger.info(
                        f"✓ {call.identifier} via {current_provider}/{current_model} "
                        f"({response.token_usage.input_tokens} in, {response.token_usage.output_tokens} out)"
                    )
                    return response.content, response.token_usage

                except ProviderRateLimitError as e:
                    self._health_tracker.mark_rate_limited(e.provider, e.retry_after)
                    logger.warning(f"⚠ {e.provider} rate-limited, trying fallback...")

                    fallback = self._health_tracker.get_fallback(current_provider, current_model)
                    if fallback and fallback[0] not in providers_tried:
                        current_provider, current_model = fallback
                        logger.info(f"↻ Falling back to {current_provider}/{current_model}")
                        continue
                    else:
                        break  # No more fallbacks, will retry after wait

                except asyncio.TimeoutError as e:
                    self._health_tracker.mark_failure(current_provider)
                    logger.warning(f"✗ {current_provider} timeout for {call.identifier}")

                    fallback = self._health_tracker.get_fallback(current_provider, current_model)
                    if fallback and fallback[0] not in providers_tried:
                        current_provider, current_model = fallback
                        logger.info(f"↻ Falling back to {current_provider}/{current_model}")
                        continue
                    else:
                        break

                except Exception as e:
                    # Non-rate-limit error: mark failure but continue trying
                    self._health_tracker.mark_failure(current_provider)
                    logger.warning(f"✗ {current_provider} error: {e}")

                    fallback = self._health_tracker.get_fallback(current_provider, current_model)
                    if fallback and fallback[0] not in providers_tried:
                        current_provider, current_model = fallback
                        logger.info(f"↻ Falling back to {current_provider}/{current_model}")
                        continue
                    else:
                        break

            # All providers exhausted this round - wait and retry
            wait_time = self._health_tracker.get_shortest_cooldown() or 30.0
            status = self._health_tracker.get_status_summary()
            logger.warning(
                f"⏳ All providers exhausted for {call.identifier}. "
                f"Status: {status}. Waiting {wait_time:.0f}s before retry..."
            )
            await asyncio.sleep(wait_time)
            # Loop continues - will retry all providers

    async def run_single(self, call: AgentCall) -> AgentReport:
        """Run a single agent call using the appropriate provider."""
        try:
            content, usage = await self._make_api_call(call)
            return AgentReport(
                role=call.role,
                investing_type_id=call.investing_type_id,
                iteration=call.iteration,
                content=content,
                token_usage=usage,
                timestamp=datetime.now(),
            )
        except Exception as e:
            logger.error(f"Error in {call.identifier}: {e}")
            return AgentReport(
                role=call.role,
                investing_type_id=call.investing_type_id,
                iteration=call.iteration,
                content="",
                token_usage=TokenUsage(),
                timestamp=datetime.now(),
                error=str(e),
            )

    async def run_parallel(self, calls: List[AgentCall]) -> Dict[str, AgentReport]:
        """
        Run multiple calls in TRUE parallel across providers.

        Since each provider has its own rate limit, we can run
        Claude, OpenAI, and Gemini calls simultaneously.
        """
        if not calls:
            return {}

        # Group calls by provider for logging
        by_provider: Dict[str, List[AgentCall]] = {}
        for call in calls:
            provider = call.provider or "claude"
            by_provider.setdefault(provider, []).append(call)

        provider_summary = ", ".join(f"{p}:{len(c)}" for p, c in by_provider.items())
        logger.info(f"Running {len(calls)} calls in parallel ({provider_summary})")

        async def run_with_id(call: AgentCall) -> Tuple[str, AgentReport]:
            report = await self.run_single(call)
            return call.identifier, report

        try:
            results = await asyncio.wait_for(
                asyncio.gather(*[run_with_id(call) for call in calls], return_exceptions=True),
                timeout=self.config.parallel_batch_timeout,
            )
        except asyncio.TimeoutError:
            logger.error("Parallel batch timed out")
            results = []
            for call in calls:
                results.append(
                    (
                        call.identifier,
                        AgentReport(
                            role=call.role,
                            investing_type_id=call.investing_type_id,
                            iteration=call.iteration,
                            content="",
                            token_usage=TokenUsage(),
                            timestamp=datetime.now(),
                            error="Batch timeout",
                        ),
                    )
                )

        # Process results
        reports = {}
        for result in results:
            if isinstance(result, Exception):
                logger.error(f"Parallel call failed: {result}")
                continue
            identifier, report = result
            reports[identifier] = report

        # Log summary
        successes = sum(1 for r in reports.values() if r.is_success)
        total_tokens = sum(r.token_usage.total_tokens for r in reports.values())
        logger.info(
            f"Parallel batch complete: {successes}/{len(calls)} succeeded, "
            f"{total_tokens:,} total tokens"
        )

        return reports

    async def run_analyst_batch(
        self,
        calls: List[AgentCall],
    ) -> Dict[int, AgentReport]:
        """
        Run a batch of analyst calls with true multi-provider parallelism.

        Groups calls by provider, then runs all provider groups in parallel.
        Within each group, calls are staggered by 2s to avoid rate limits.

        Example with 6 analysts across 3 providers:
        - Claude (analysts 1-2): Start at 0s, 2s
        - OpenAI (analysts 3-4): Start at 0s, 2s (parallel with Claude)
        - Gemini (analysts 5-6): Start at 0s, 2s (parallel with Claude+OpenAI)

        Total startup: ~4s (vs 150s sequential)
        """
        if not calls:
            return {}

        if self.config.parallel_execution:
            # Group calls by provider
            by_provider: Dict[str, List[AgentCall]] = defaultdict(list)
            for call in calls:
                provider = call.provider or "claude"
                by_provider[provider].append(call)

            provider_summary = ", ".join(f"{p}:{len(c)}" for p, c in by_provider.items())
            logger.info(f"Running {len(calls)} analysts in parallel ({provider_summary})")

            # Run each provider group with internal staggering
            async def run_provider_group(
                provider: str, provider_calls: List[AgentCall]
            ) -> List[Tuple[str, AgentReport]]:
                """Run calls for one provider with 2s stagger between each."""
                results = []
                for i, call in enumerate(provider_calls):
                    if i > 0:
                        await asyncio.sleep(2.0)  # Stagger within provider
                    report = await self.run_single(call)
                    results.append((call.identifier, report))
                return results

            # Run all provider groups in parallel
            provider_tasks = [
                run_provider_group(provider, provider_calls)
                for provider, provider_calls in by_provider.items()
            ]

            try:
                all_results = await asyncio.wait_for(
                    asyncio.gather(*provider_tasks, return_exceptions=True),
                    timeout=self.config.parallel_batch_timeout,
                )
            except asyncio.TimeoutError:
                logger.error("Analyst batch timed out")
                all_results = []

            # Flatten results
            results = {}
            for group_result in all_results:
                if isinstance(group_result, Exception):
                    logger.error(f"Provider group failed: {group_result}")
                    continue
                for identifier, report in group_result:
                    results[identifier] = report
        else:
            # Sequential fallback
            results = await self._run_sequential(calls, delay_between=30.0)

        # Convert to type_id -> report mapping
        by_type: Dict[int, AgentReport] = {}
        for identifier, report in results.items():
            if report.investing_type_id is not None:
                by_type[report.investing_type_id] = report

        return by_type

    async def _run_with_delay(
        self,
        call: AgentCall,
        delay: float,
    ) -> Tuple[str, AgentReport]:
        """Run a single call after a delay (for staggered parallelism)."""
        if delay > 0:
            await asyncio.sleep(delay)
        report = await self.run_single(call)
        return call.identifier, report

    async def run_rd_review_batch(
        self,
        calls: List[AgentCall],
    ) -> Dict[int, AgentReport]:
        """Run a batch of RD review calls with staggered parallel execution.

        All 6 RD reviews run in parallel with 2s stagger between starts.
        This smooths rate limit impact while maximizing parallelism.
        Total startup spread: ~10s for 6 calls.
        """
        if not calls:
            return {}

        if self.config.parallel_execution:
            # Staggered parallel: all 6 in parallel with 2s delay between starts
            # This avoids burst rate limits while being much faster than batching
            stagger_delay = 2.0  # seconds between each call start

            logger.info(
                f"Running {len(calls)} RD reviews in staggered parallel "
                f"({stagger_delay}s stagger)"
            )

            tasks = []
            for i, call in enumerate(calls):
                delay = i * stagger_delay
                tasks.append(self._run_with_delay(call, delay))

            try:
                raw_results = await asyncio.wait_for(
                    asyncio.gather(*tasks, return_exceptions=True),
                    timeout=self.config.parallel_batch_timeout,
                )
            except asyncio.TimeoutError:
                logger.error("RD review batch timed out")
                raw_results = []

            # Process results
            results = {}
            for result in raw_results:
                if isinstance(result, Exception):
                    logger.error(f"RD review call failed: {result}")
                    continue
                identifier, report = result
                results[identifier] = report
        else:
            results = await self._run_sequential(calls, delay_between=30.0)

        # Convert to type_id -> report mapping
        by_type: Dict[int, AgentReport] = {}
        for identifier, report in results.items():
            if report.investing_type_id is not None:
                by_type[report.investing_type_id] = report

        return by_type

    async def _run_sequential(
        self,
        calls: List[AgentCall],
        delay_between: float = 5.0,
    ) -> Dict[str, AgentReport]:
        """Run calls sequentially (fallback for rate-limited scenarios)."""
        if not calls:
            return {}

        logger.info(f"Running {len(calls)} calls sequentially")

        reports = {}
        for i, call in enumerate(calls):
            logger.info(f"  [{i+1}/{len(calls)}] {call.identifier} ({call.provider}/{call.model})...")
            report = await self.run_single(call)
            reports[call.identifier] = report

            if report.is_success:
                logger.info(f"    Done: {report.token_usage.total_tokens:,} tokens")
            else:
                logger.warning(f"    Failed: {report.error}")

            if i < len(calls) - 1:
                await asyncio.sleep(delay_between)

        return reports

    def get_provider_stats(self) -> Dict[str, dict]:
        """Get usage statistics from all providers."""
        return {
            provider: {
                "calls": stats.calls,
                "input_tokens": stats.total_input_tokens,
                "output_tokens": stats.total_output_tokens,
                "errors": stats.errors,
            }
            for provider, stats in self.provider_factory.get_stats().items()
        }

    def get_cost_estimate(self) -> Dict[str, float]:
        """Get estimated costs by provider."""
        return self.provider_factory.get_cost_estimate()

    def close(self):
        """Close all provider connections."""
        self.provider_factory.close_all()
