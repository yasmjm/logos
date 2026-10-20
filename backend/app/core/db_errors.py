"""Classifies database errors: which are transient (safe to retry a read) and which
mean the database is unavailable (answer 503 instead of 500)."""

from sqlalchemy.exc import DBAPIError, InterfaceError, OperationalError
from sqlalchemy.exc import TimeoutError as PoolTimeoutError

# Connection exceptions (class 08) and server shutdown/restart (57P01-57P03).
_TRANSIENT_SQLSTATE_CLASS = "08"
_TRANSIENT_SQLSTATES = {"57P01", "57P02", "57P03"}
STATEMENT_TIMEOUT_SQLSTATE = "57014"


def sqlstate(exc: BaseException) -> str | None:
    return getattr(getattr(exc, "orig", None), "sqlstate", None)


def is_transient_connection_error(exc: BaseException) -> bool:
    """Lost or refused connection: a new connection may succeed. Never a slow query."""
    if isinstance(exc, DBAPIError) and exc.connection_invalidated:
        return True
    if isinstance(exc, OperationalError | InterfaceError):
        state = sqlstate(exc)
        if state is None:  # the server never answered: refused, unreachable, DNS
            return True
        return state.startswith(_TRANSIENT_SQLSTATE_CLASS) or state in _TRANSIENT_SQLSTATES
    return False


def is_statement_timeout(exc: BaseException) -> bool:
    return sqlstate(exc) == STATEMENT_TIMEOUT_SQLSTATE


# Everything the handler answers with 503 (pool exhausted, connection errors, timeouts).
DATABASE_UNAVAILABLE_ERRORS = (OperationalError, InterfaceError, PoolTimeoutError)
