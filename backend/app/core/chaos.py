"""Chaos mode for the resilience demo: latency and simulated 503s on /incidents.

Off unless CHAOS_ENABLED=true. Every configuration expires on its own after
CHAOS_TTL, so nobody can leave the system broken for the next person (docs/adr/0002).
"""

import asyncio
import random
import threading
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from starlette.types import ASGIApp, Receive, Scope, Send

from app.core.errors import problem_response, with_request_id

CHAOS_TTL = timedelta(minutes=3)
CHAOS_RETRY_AFTER_SECONDS = 1
TARGET_PREFIX = "/incidents"


@dataclass(frozen=True)
class ChaosSnapshot:
    latency_ms: int
    failure_rate: float
    expires_at: datetime | None

    @property
    def active(self) -> bool:
        return self.expires_at is not None


_OFF = ChaosSnapshot(latency_ms=0, failure_rate=0.0, expires_at=None)


class ChaosController:
    def __init__(
        self,
        clock: Callable[[], datetime] = lambda: datetime.now(UTC),
        rng: random.Random | None = None,
    ) -> None:
        self.clock = clock
        self.rng = rng or random.Random()
        self._state = _OFF
        self._lock = threading.Lock()

    def configure(self, latency_ms: int, failure_rate: float) -> ChaosSnapshot:
        with self._lock:
            if latency_ms == 0 and failure_rate == 0:
                self._state = _OFF
            else:
                # Every change renews the deadline; it never lasts longer than CHAOS_TTL.
                self._state = ChaosSnapshot(latency_ms, failure_rate, self.clock() + CHAOS_TTL)
            return self._state

    def snapshot(self) -> ChaosSnapshot:
        with self._lock:
            if self._state.active and self.clock() >= self._state.expires_at:
                self._state = _OFF  # expired: back to normal by itself
            return self._state

    def should_fail(self, failure_rate: float) -> bool:
        return failure_rate > 0 and self.rng.random() < failure_rate


def _is_target(scope: Scope) -> bool:
    path = scope["path"]
    return (
        scope["type"] == "http"
        and scope["method"] != "OPTIONS"  # never break CORS preflights
        and (path == TARGET_PREFIX or path.startswith(TARGET_PREFIX + "/"))
    )


class ChaosMiddleware:
    """Only touches /incidents; /health, /ready, /auth and /chaos are never affected."""

    def __init__(self, app: ASGIApp, controller: ChaosController) -> None:
        self.app = app
        self.controller = controller

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if not _is_target(scope):
            await self.app(scope, receive, send)
            return

        chaos = self.controller.snapshot()
        if chaos.active:
            if chaos.latency_ms:
                await asyncio.sleep(chaos.latency_ms / 1000)
            if self.controller.should_fail(chaos.failure_rate):
                response = problem_response(
                    503,
                    "Chaos mode: simulated failure. Please try again.",
                    **with_request_id(),
                )
                response.headers["Retry-After"] = str(CHAOS_RETRY_AFTER_SECONDS)
                await response(scope, receive, send)
                return
        await self.app(scope, receive, send)
