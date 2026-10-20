"""In-memory sliding-window rate limiting.

Good enough for a single-instance MVP. Limitations (see docs/adr/0001): state lives in
the process, so it is not shared between instances or workers and resets on restart.
"""

import math
import threading
import time
from collections import deque


class RateLimiter:
    def __init__(self, limit: int, window_seconds: float) -> None:
        self.limit = limit
        self.window = window_seconds
        self._hits: dict[str, deque[float]] = {}
        self._lock = threading.Lock()

    def hit(self, key: str) -> int | None:
        """Count one request for key. Returns seconds to wait if over the limit, else None."""
        now = time.monotonic()
        with self._lock:
            hits = self._hits.setdefault(key, deque())
            while hits and hits[0] <= now - self.window:
                hits.popleft()
            if len(hits) >= self.limit:
                return max(1, math.ceil(hits[0] + self.window - now))
            hits.append(now)
            self._forget_idle_keys(now)
            return None

    def reset(self) -> None:
        with self._lock:
            self._hits.clear()

    def _forget_idle_keys(self, now: float) -> None:
        # Keeps memory bounded when many distinct keys (e.g. IPs) show up once.
        if len(self._hits) > 10_000:
            idle = [k for k, h in self._hits.items() if not h or h[-1] <= now - self.window]
            for key in idle:
                del self._hits[key]


LOGIN_LIMITER = RateLimiter(limit=5, window_seconds=60)  # brute force, per IP
INGEST_LIMITER = RateLimiter(limit=120, window_seconds=60)  # per API key
DEMO_RESET_LIMITER = RateLimiter(limit=1, window_seconds=60)  # global
DEMO_SIMULATE_LIMITER = RateLimiter(limit=10, window_seconds=60)  # per analyst
ALL_LIMITERS = (LOGIN_LIMITER, INGEST_LIMITER, DEMO_RESET_LIMITER, DEMO_SIMULATE_LIMITER)
