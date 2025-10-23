"""Resilience utilities combining retries, backoff, and circuit breaking."""

from __future__ import annotations

import logging
import math
import random
import time
from dataclasses import dataclass
from datetime import timedelta
from threading import RLock
from typing import Any, Awaitable, Callable, Dict, Generic, Optional, TypeVar

from aiobreaker import CircuitBreaker, CircuitBreakerError, CircuitBreakerListener
from tenacity import AsyncRetrying, RetryCallState, stop_after_attempt, stop_after_delay
try:
    from tenacity.wait import WaitBaseStrategy
except ImportError:  # tenacity<9.0
    from tenacity.wait import wait_base as WaitBaseStrategy  # type: ignore[assignment]

from services.shared.config import ConfigurationError, get_settings

logger = logging.getLogger(__name__)

T = TypeVar("T")


class SlowCallError(RuntimeError):
    """Raised when an operation exceeds the configured slow-call threshold."""

    def __init__(self, operation: str, duration_seconds: float) -> None:
        super().__init__(f"Operation '{operation}' exceeded slow-call threshold: {duration_seconds:.3f}s")
        self.operation = operation
        self.duration_seconds = duration_seconds


class ConfiguredExponentialBackoff(WaitBaseStrategy):
    """Tenacity wait strategy honouring configuration-driven backoff parameters."""

    def __init__(
        self,
        *,
        initial: float,
        multiplier: float,
        max_interval: float,
        jitter_ratio: float,
    ) -> None:
        self._initial = max(initial, 0.0)
        self._multiplier = max(multiplier, 1.0)
        self._max_interval = max(max_interval, self._initial)
        self._jitter_ratio = max(jitter_ratio, 0.0)

    def __call__(self, retry_state: RetryCallState) -> float:  # pragma: no cover - exercised via Tenacity
        attempt = max(retry_state.attempt_number - 1, 0)
        base_delay = self._initial * math.pow(self._multiplier, attempt)
        delay = min(base_delay, self._max_interval)
        if self._jitter_ratio > 0.0:
            jitter_bounds = delay * self._jitter_ratio
            delay += random.uniform(-jitter_bounds, jitter_bounds)
            delay = max(delay, 0.0)
        return delay


class ResilienceListener(CircuitBreakerListener):
    """Circuit breaker listener emitting structured logs for observability."""

    def state_change(self, cb: CircuitBreaker, old_state: str, new_state: str) -> None:
        logger.warning(
            "Circuit breaker state change",
            extra={"breaker": cb.name, "old_state": old_state, "new_state": new_state},
        )

    def failure(self, cb: CircuitBreaker, exc: BaseException) -> None:  # pragma: no cover - logging shim
        logger.error(
            "Circuit breaker recorded failure",
            extra={"breaker": cb.name, "exception": exc.__class__.__name__},
        )

    def success(self, cb: CircuitBreaker) -> None:  # pragma: no cover - logging shim
        logger.debug("Circuit breaker success", extra={"breaker": cb.name})


FallbackCallable = Callable[[], Awaitable[T]]
OperationCallable = Callable[..., Awaitable[T]]


@dataclass
class CircuitContext:
    breaker: CircuitBreaker
    slow_call_threshold: float


class ResilienceOrchestrator(Generic[T]):
    """Coordinates retry policies and circuit breakers for outbound operations."""

    def __init__(self) -> None:
        self._breakers: Dict[str, CircuitContext] = {}
        self._lock = RLock()

    def _get_context(self, name: str) -> CircuitContext:
        with self._lock:
            context = self._breakers.get(name)
            if context is not None:
                return context

            cfg = get_settings().circuit_breaker
            fail_max = max(1, math.ceil(cfg.minimum_number_of_calls * cfg.failure_rate_threshold))
            breaker = CircuitBreaker(
                fail_max=fail_max,
                timeout_duration=timedelta(seconds=cfg.wait_duration_in_open_state_seconds),
                listeners=[ResilienceListener()],
                name=name,
            )
            context = CircuitContext(
                breaker=breaker,
                slow_call_threshold=cfg.slow_call_duration_threshold_seconds,
            )
            self._breakers[name] = context
            return context

    def _retrying(self) -> Optional[AsyncRetrying]:
        try:
            policy = get_settings().retry
        except ConfigurationError:
            return None

        if not policy.enabled:
            return None

        wait_strategy = ConfiguredExponentialBackoff(
            initial=policy.initial_interval_seconds,
            multiplier=policy.multiplier,
            max_interval=policy.max_interval_seconds,
            jitter_ratio=policy.randomization_factor,
        )

        stop_policy = stop_after_attempt(policy.max_retries) | stop_after_delay(
            policy.max_elapsed_time_seconds
        )

        return AsyncRetrying(wait=wait_strategy, stop=stop_policy, reraise=True)

    async def _invoke(
        self,
        name: str,
        operation: OperationCallable[T],
        *args: Any,
        **kwargs: Any,
    ) -> T:
        context = self._get_context(name)
        start_time = time.perf_counter()
        result = await context.breaker.call_async(operation, *args, **kwargs)
        latency = time.perf_counter() - start_time
        if latency >= context.slow_call_threshold:
            raise SlowCallError(name, latency)
        return result

    async def execute(
        self,
        name: str,
        operation: OperationCallable[T],
        *args: Any,
        fallback: Optional[FallbackCallable[T]] = None,
        **kwargs: Any,
    ) -> T:
        retrying = self._retrying()

        async def _attempt() -> T:
            return await self._invoke(name, operation, *args, **kwargs)

        try:
            if retrying is None:
                return await _attempt()

            async for attempt in retrying:
                with attempt:
                    return await _attempt()
        except (CircuitBreakerError, SlowCallError) as exc:
            logger.warning("Resilience fallback triggered", extra={"breaker": name, "reason": str(exc)})
            if fallback is not None:
                return await fallback()
            raise

        # Should not be reachable because attempt returns a value
        raise RuntimeError("Resilience execution ended without returning a result")


resilience: ResilienceOrchestrator[Any] = ResilienceOrchestrator()


async def execute_with_resilience(
    name: str,
    operation: OperationCallable[T],
    *args: Any,
    fallback: Optional[FallbackCallable[T]] = None,
    **kwargs: Any,
) -> T:
    """Convenience wrapper to execute an async operation using the shared orchestrator."""

    return await resilience.execute(name, operation, *args, fallback=fallback, **kwargs)


__all__ = [
    "ConfiguredExponentialBackoff",
    "ResilienceOrchestrator",
    "SlowCallError",
    "execute_with_resilience",
    "resilience",
]
