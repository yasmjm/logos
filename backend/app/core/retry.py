"""Retry with exponential backoff and full jitter, for transient connection failures.

Only for reads and for getting a connection. Writes are never retried on the server:
the client retries them, and optimistic locking turns a repeated write into a 409
instead of a duplicated effect (docs/adr/0002).
"""

import logging
import random
import time
from collections.abc import Callable

from sqlalchemy.orm import Session

from app.core.db_errors import is_transient_connection_error

logger = logging.getLogger(__name__)

MAX_ATTEMPTS = 3
BASE_DELAY_SECONDS = 0.05


def retry_transient[T](
    operation: Callable[[], T],
    *,
    before_retry: Callable[[], object] | None = None,
    attempts: int = MAX_ATTEMPTS,
    base_delay: float = BASE_DELAY_SECONDS,
    sleep: Callable[[float], object] = time.sleep,
    jitter: Callable[[], float] = random.random,
) -> T:
    for attempt in range(1, attempts + 1):
        try:
            return operation()
        except Exception as exc:
            if attempt == attempts or not is_transient_connection_error(exc):
                raise
            # Full jitter: a random wait up to the exponential cap (50ms, 100ms, ...),
            # so clients that failed together do not retry together.
            delay = jitter() * base_delay * 2 ** (attempt - 1)
            logger.warning(
                "Transient database error, retrying",
                extra={"fields": {"attempt": attempt, "delay_ms": round(delay * 1000, 1)}},
            )
            if before_retry is not None:
                before_retry()
            sleep(delay)
    raise AssertionError("unreachable")


def read_with_retry[T](db: Session, read: Callable[[], T]) -> T:
    """Run a read; on a transient failure roll back (fresh connection) and try again."""
    return retry_transient(read, before_retry=db.rollback)
