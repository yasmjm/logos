from contextvars import ContextVar

# Set per request by RequestContextMiddleware; read by logs and error bodies.
request_id_var: ContextVar[str | None] = ContextVar("request_id", default=None)


def current_request_id() -> str | None:
    return request_id_var.get()
