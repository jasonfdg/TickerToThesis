"""
Agent Runner
============
Async Claude API wrapper with parallel execution and retry logic.
"""

import asyncio
import logging
import random
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional, Tuple

import anthropic

try:
    from .config import PipelineConfig
    from .models import AgentReport, AgentRole, TokenUsage
except ImportError:
    from config import PipelineConfig
    from models import AgentReport, AgentRole, TokenUsage

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

    def __post_init__(self):
        if not self.identifier:
            if self.investing_type_id is not None:
                self.identifier = f"{self.role.value}_type_{self.investing_type_id}_v{self.iteration}"
            else:
                self.identifier = f"{self.role.value}_v{self.iteration}"


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
