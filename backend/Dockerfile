# syntax=docker/dockerfile:1

# --- build: resolve production dependencies with uv -----------------------------------
FROM python:3.12-slim AS build

COPY --from=ghcr.io/astral-sh/uv:0.13.4 /uv /bin/uv

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=never \
    UV_PROJECT_ENVIRONMENT=/app/.venv

WORKDIR /app

# Dependencies first, so code changes reuse this layer.
COPY pyproject.toml uv.lock ./
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --locked --no-dev --no-install-project

COPY alembic.ini ./
COPY alembic ./alembic
COPY app ./app
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --locked --no-dev

# --- runtime: only the virtualenv and the code, as a non-root user ---------------------
FROM python:3.12-slim AS runtime

RUN groupadd --system app && useradd --system --gid app --home-dir /app --no-create-home app

WORKDIR /app
COPY --from=build --chown=app:app /app /app

ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PORT=8000

USER app
EXPOSE 8000

# No --proxy-headers: with --forwarded-allow-ips='*' uvicorn takes the LEFTMOST
# X-Forwarded-For entry, which the client can forge. The app reads the entry added by
# the platform proxy instead (TRUSTED_PROXY_HOPS, app/core/client_ip.py, ADR 0001).
# Access logs come from our JSON middleware, so uvicorn's own are off.
CMD ["sh", "-c", "exec uvicorn app.main:app --host 0.0.0.0 --port \"$PORT\" --no-proxy-headers --no-access-log"]
