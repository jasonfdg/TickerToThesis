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
from typing import Dict, List, Optional, Set, Tuple

import anthropic

try:
    from .config import (
        PipelineConfig, ANALYST_PROVIDER_CONFIG, ROLE_PROVIDER_CONFIG,
        COMPONENT_OVERRIDES, get_effective_provider, get_pipeline_mode,
        LIGHT_MODE_FALLBACK_CHAIN, LIGHT_MODE_DELAYS,
        get_randomized_provider, get_fallback_chain,
    )
    from .models import AgentReport, AgentRole, TokenUsage
    from .providers import ProviderFactory, ProviderResponse
    from .providers.base import ProviderRateLimitError
except ImportError:
    from config import (
        PipelineConfig, ANALYST_PROVIDER_CONFIG, ROLE_PROVIDER_CONFIG,
        COMPONENT_OVERRIDES, get_effective_provider, get_pipeline_mode,
        LIGHT_MODE_FALLBACK_CHAIN, LIGHT_MODE_DELAYS,
        get_randomized_provider, get_fallback_chain,
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
        """Auto-assign provider and model using randomized 2-2-2 assignment.

        Priority order:
        1. Explicit provider/model set on AgentCall
        2. COMPONENT_OVERRIDES in config.py
        3. Randomized 2-2-2 assignment for analysts and RD reviews
        4. Default routing from ROLE_PROVIDER_CONFIG for other roles
        """
        # Build component identifier for override lookup
        if self.role == AgentRole.ANALYST and self.investing_type_id is not None:
            component = f"analyst_{self.investing_type_id}"
        elif self.role == AgentRole.RD_REVIEW and self.investing_type_id is not None:
            component = f"rd_review_{self.investing_type_id}"
        else:
            component = self.role.value  # e.g., "rd_synthesis", "source_scout"

        # Check for explicit override first
        if component in COMPONENT_OVERRIDES:
            override = COMPONENT_OVERRIDES[component]
            self.provider = self.provider or override["provider"]
            self.model = self.model or override["model"]
            return

        # Use randomized assignment for analysts
        if self.role == AgentRole.ANALYST and self.investing_type_id is not None:
            provider, model = get_randomized_provider(
                self.investing_type_id, self.iteration, "analyst"
            )
            self.provider = self.provider or provider
            self.model = self.model or model
            return

        # Use randomized assignment for RD reviews
        if self.role == AgentRole.RD_REVIEW and self.investing_type_id is not None:
            provider, model = get_randomized_provider(
                self.investing_type_id, self.iteration, "rd_review"
            )
            self.provider = self.provider or provider
            self.model = self.model or model
            return

        # Fallback to role-based config for other roles
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
    """Circular fallback with configurable chain from config.py.

    Fallback strategy (full mode):
    - Chain: claude-cli → gemini 3 pro → gpt-4o → claude API
    - After 3 complete loops, falls back to Claude API (Sonnet) as last resort
    - This maximizes use of free/cheap providers before expensive Claude API

    Fallback strategy (light mode):
    - Chain: claude-cli → gemini flash → gpt-4o-mini → claude API
    - Faster providers with shorter backoff delays
    - Falls back to Claude API (Haiku) as last resort after 3 loops

    Preserved routing (not part of circular chain):
    - Perplexity for source_scout (web search)
    - GPT-4o-mini for source_summary (best JSON validity)
    """

    MAX_LOOPS = 3

    def __init__(self, pipeline_mode: Optional[str] = None):
        self._health: Dict[str, ProviderHealth] = defaultdict(ProviderHealth)
        self._loop_counts: Dict[str, int] = defaultdict(int)  # Per-call loop tracking
        self._pipeline_mode = pipeline_mode or get_pipeline_mode()
        self._fallback_chain = get_fallback_chain(self._pipeline_mode)

    @property
    def CIRCULAR_CHAIN(self) -> List[str]:
        """Get providers from fallback chain (excluding last resort)."""
        return [p[0] for p in self._fallback_chain[:-1]]

    @property
    def LAST_RESORT(self) -> Tuple[str, str]:
        """Get last resort provider/model."""
        return self._fallback_chain[-1]

    def get_loop_wait_time(self, loop_count: int) -> float:
        """Get wait time for a fallback loop, respecting light mode optimization.

        Light mode uses shorter delays since providers are faster.
        """
        if self._pipeline_mode == "light":
            base = LIGHT_MODE_DELAYS.get("loop_wait_base", 15.0)
            max_wait = LIGHT_MODE_DELAYS.get("loop_wait_max", 60.0)
        else:
            base = 30.0
            max_wait = 120.0

        # Exponential backoff: base * 2^loop_count, capped at max
        wait_time = min(base * (2 ** loop_count), max_wait)
        return wait_time

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

    def get_next_provider(
        self,
        call_id: str,
        current_provider: str,
        current_model: str,
        providers_tried: Set[str],
    ) -> Tuple[str, str, bool, bool]:
        """Get next provider in circular chain.

        Args:
            call_id: Unique identifier for this call (for loop tracking)
            current_provider: Provider that just failed
            current_model: Model that was being used
            providers_tried: Set of providers already tried this loop

        Returns:
            Tuple of (provider, model, is_last_resort, is_new_loop)
        """
        # Handle providers in the circular chain
        if current_provider in self.CIRCULAR_CHAIN:
            idx = self.CIRCULAR_CHAIN.index(current_provider)
            next_idx = (idx + 1) % len(self.CIRCULAR_CHAIN)
            next_provider = self.CIRCULAR_CHAIN[next_idx]

            # Check if we've completed a full loop (next provider already tried)
            if next_provider in providers_tried:
                self._loop_counts[call_id] += 1

                if self._loop_counts[call_id] >= self.MAX_LOOPS:
                    # 3 loops exhausted → last resort
                    return self.LAST_RESORT[0], self.LAST_RESORT[1], True, False

                # Signal new loop starting (caller should wait and clear providers_tried)
                return next_provider, self._map_model(next_provider, current_model), False, True

            return next_provider, self._map_model(next_provider, current_model), False, False

        # Non-circular provider (perplexity, 4o-mini) → go to first in chain
        return self.CIRCULAR_CHAIN[0], self._map_model(self.CIRCULAR_CHAIN[0], current_model), False, False

    def reset_loop_count(self, call_id: str):
        """Reset loop counter after successful call."""
        self._loop_counts.pop(call_id, None)

    def get_loop_count(self, call_id: str) -> int:
        """Get current loop count for a call."""
        return self._loop_counts.get(call_id, 0)

    def _map_model(self, provider: str, original_model: str) -> str:
        """Map to correct model from fallback chain.

        First checks fallback chain for the target provider, then falls back
        to tier matching if provider isn't in chain.
        """
        # First, try to get model from fallback chain
        for p, m in self._fallback_chain:
            if p == provider:
                return m

        # Fallback to tier matching for providers not in chain
        original_lower = original_model.lower()
        is_mini = "mini" in original_lower or "flash" in original_lower or "haiku" in original_lower

        if provider == "claude-cli":
            return "haiku" if is_mini else "sonnet"
        elif provider == "gemini":
            return "gemini-2.5-flash" if is_mini else "gemini-3-pro-preview"
        elif provider == "openai":
            return "gpt-4o-mini" if is_mini else "gpt-4o"
        elif provider == "claude":
            return "haiku" if is_mini else "sonnet"

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
        for provider in self.CIRCULAR_CHAIN + [self.LAST_RESORT[0]]:
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
        # Pass pipeline mode to health tracker for light mode optimization
        self._health_tracker = ProviderHealthTracker(pipeline_mode=self.config.pipeline_mode)

    def _get_semaphore(self, provider: str) -> asyncio.Semaphore:
        """Get or create a rate-limiting semaphore for a provider."""
        if provider not in self._semaphores:
            rpm = self.config.provider_rate_limits.get(provider, 50)
            # Allow concurrent requests up to half the rate limit
            self._semaphores[provider] = asyncio.Semaphore(max(1, rpm // 2))
        return self._semaphores[provider]

    def _get_stagger_delay(self) -> float:
        """Get the stagger delay for parallel calls based on pipeline mode.

        Light mode uses shorter delays since providers are faster.
        """
        if self.config.pipeline_mode == "light":
            return LIGHT_MODE_DELAYS.get("stagger_delay", 0.5)
        return 2.0

    def _get_sequential_delay(self) -> float:
        """Get the delay between sequential calls based on pipeline mode.

        Light mode uses shorter delays since providers are faster.
        """
        if self.config.pipeline_mode == "light":
            return LIGHT_MODE_DELAYS.get("sequential_delay", 2.0)
        return 5.0

    async def _make_api_call(self, call: AgentCall) -> Tuple[str, TokenUsage]:
        """Make API call with circular fallback on rate limits.

        Never gives up - cycles through providers in a circular chain:
        claude-cli → gemini → openai → claude-cli → ...

        After 3 complete loops, falls back to Claude API (Sonnet) as last resort.
        This maximizes use of free/cheap providers before expensive API calls.
        """
        provider = call.provider or "claude-cli"
        model = call.model or "sonnet"
        call_id = call.identifier or str(id(call))

        providers_tried_this_loop: Set[str] = set()
        current_provider, current_model = provider, model

        while True:  # Persistent retry loop - never give up
            providers_tried_this_loop.add(current_provider)

            # Skip if provider is in cooldown
            if not self._health_tracker._health[current_provider].is_available():
                logger.debug(f"Skipping {current_provider} (cooldown active)")
                next_provider, next_model, is_last_resort, is_new_loop = self._health_tracker.get_next_provider(
                    call_id, current_provider, current_model, providers_tried_this_loop
                )

                if is_new_loop:
                    loop_num = self._health_tracker.get_loop_count(call_id) + 1
                    # Use mode-aware wait time (shorter for light mode)
                    wait_time = self._health_tracker.get_shortest_cooldown() or \
                                self._health_tracker.get_loop_wait_time(loop_num)
                    logger.info(f"⏳ Starting loop {loop_num}/{self._health_tracker.MAX_LOOPS}, waiting {wait_time:.0f}s")
                    await asyncio.sleep(wait_time)
                    providers_tried_this_loop.clear()

                current_provider, current_model = next_provider, next_model
                continue

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

                # Check for empty response (Gemini sometimes returns 0 tokens)
                if not response.content or response.token_usage.output_tokens == 0:
                    logger.warning(
                        f"⚠ {call.identifier} via {current_provider}/{current_model} returned empty response, "
                        f"trying next provider"
                    )
                    self._health_tracker.mark_failure(current_provider)

                    next_provider, next_model, is_last_resort, is_new_loop = self._health_tracker.get_next_provider(
                        call_id, current_provider, current_model, providers_tried_this_loop
                    )

                    if is_last_resort:
                        logger.warning(f"⚠ 3 loops exhausted for {call.identifier}, using Claude API (last resort)")
                    elif is_new_loop:
                        loop_num = self._health_tracker.get_loop_count(call_id) + 1
                        wait_time = self._health_tracker.get_shortest_cooldown() or \
                                    self._health_tracker.get_loop_wait_time(loop_num)
                        logger.info(f"⏳ Starting loop {loop_num}/{self._health_tracker.MAX_LOOPS}, waiting {wait_time:.0f}s")
                        await asyncio.sleep(wait_time)
                        providers_tried_this_loop.clear()
                    else:
                        logger.info(f"↻ {current_provider} empty response, trying {next_provider}")

                    current_provider, current_model = next_provider, next_model
                    continue

                # Success - reset loop counter and mark success
                self._health_tracker.reset_loop_count(call_id)
                self._health_tracker.mark_success(current_provider)
                logger.info(
                    f"✓ {call.identifier} via {current_provider}/{current_model} "
                    f"({response.token_usage.input_tokens} in, {response.token_usage.output_tokens} out)"
                )
                return response.content, response.token_usage

            except ProviderRateLimitError as e:
                self._health_tracker.mark_rate_limited(e.provider, e.retry_after)

                next_provider, next_model, is_last_resort, is_new_loop = self._health_tracker.get_next_provider(
                    call_id, current_provider, current_model, providers_tried_this_loop
                )

                if is_last_resort:
                    logger.warning(f"⚠ 3 loops exhausted for {call.identifier}, using Claude API (last resort)")
                elif is_new_loop:
                    loop_num = self._health_tracker.get_loop_count(call_id) + 1
                    wait_time = self._health_tracker.get_shortest_cooldown() or \
                                self._health_tracker.get_loop_wait_time(loop_num)
                    logger.info(f"⏳ Starting loop {loop_num}/{self._health_tracker.MAX_LOOPS}, waiting {wait_time:.0f}s")
                    await asyncio.sleep(wait_time)
                    providers_tried_this_loop.clear()
                else:
                    logger.info(f"↻ {current_provider} rate-limited, trying {next_provider}")

                current_provider, current_model = next_provider, next_model

            except asyncio.TimeoutError:
                self._health_tracker.mark_failure(current_provider)
                logger.warning(f"✗ {current_provider} timeout for {call.identifier}")

                next_provider, next_model, is_last_resort, is_new_loop = self._health_tracker.get_next_provider(
                    call_id, current_provider, current_model, providers_tried_this_loop
                )

                if is_last_resort:
                    logger.warning(f"⚠ 3 loops exhausted for {call.identifier}, using Claude API (last resort)")
                elif is_new_loop:
                    loop_num = self._health_tracker.get_loop_count(call_id) + 1
                    wait_time = self._health_tracker.get_shortest_cooldown() or \
                                self._health_tracker.get_loop_wait_time(loop_num)
                    logger.info(f"⏳ Starting loop {loop_num}/{self._health_tracker.MAX_LOOPS}, waiting {wait_time:.0f}s")
                    await asyncio.sleep(wait_time)
                    providers_tried_this_loop.clear()
                else:
                    logger.info(f"↻ {current_provider} timeout, trying {next_provider}")

                current_provider, current_model = next_provider, next_model

            except Exception as e:
                # Non-rate-limit error: mark failure but continue trying
                self._health_tracker.mark_failure(current_provider)
                logger.warning(f"✗ {current_provider} error: {e}")

                next_provider, next_model, is_last_resort, is_new_loop = self._health_tracker.get_next_provider(
                    call_id, current_provider, current_model, providers_tried_this_loop
                )

                if is_last_resort:
                    logger.warning(f"⚠ 3 loops exhausted for {call.identifier}, using Claude API (last resort)")
                elif is_new_loop:
                    loop_num = self._health_tracker.get_loop_count(call_id) + 1
                    wait_time = self._health_tracker.get_shortest_cooldown() or \
                                self._health_tracker.get_loop_wait_time(loop_num)
                    logger.info(f"⏳ Starting loop {loop_num}/{self._health_tracker.MAX_LOOPS}, waiting {wait_time:.0f}s")
                    await asyncio.sleep(wait_time)
                    providers_tried_this_loop.clear()
                else:
                    logger.info(f"↻ {current_provider} error, trying {next_provider}")

                current_provider, current_model = next_provider, next_model

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
            stagger = self._get_stagger_delay()

            async def run_provider_group(
                provider: str, provider_calls: List[AgentCall]
            ) -> List[Tuple[str, AgentReport]]:
                """Run calls for one provider with stagger between each."""
                results = []
                for i, call in enumerate(provider_calls):
                    if i > 0:
                        await asyncio.sleep(stagger)  # Stagger within provider
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
            # Sequential fallback - use mode-aware delay
            seq_delay = self._get_sequential_delay()
            results = await self._run_sequential(calls, delay_between=seq_delay)

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
            # Staggered parallel: all 6 in parallel with delay between starts
            # This avoids burst rate limits while being much faster than batching
            stagger_delay = self._get_stagger_delay()

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
            # Sequential fallback - use mode-aware delay
            seq_delay = self._get_sequential_delay()
            results = await self._run_sequential(calls, delay_between=seq_delay)

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
