FROM python:3.12-slim-bookworm AS builder

COPY --from=ghcr.io/astral-sh/uv:0.12.14 /uv /usr/local/bin/uv

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=never

WORKDIR /app

# Dependencies are resolved before the source is copied so that a code change
# does not invalidate the dependency layer.
COPY pyproject.toml uv.lock ./
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-install-project --no-dev \
    --extra db --extra exchange --extra azure --extra telemetry

COPY src ./src
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev \
    --extra db --extra exchange --extra azure --extra telemetry


FROM python:3.12-slim-bookworm AS runtime

# Base images are rebuilt on their own schedule and lag behind Debian security
# updates, so a freshly pulled tag can still carry vulnerabilities that upstream
# has already fixed. The Trivy gate in CI is what makes that visible; this is
# the answer to it.
RUN apt-get update \
    && apt-get upgrade -y --no-install-recommends \
    && rm -rf /var/lib/apt/lists/*

# The build tools and the uv binary stay in the builder stage: the runtime image
# ships the virtualenv and nothing that could compile or fetch code.
RUN groupadd --system --gid 1001 bot \
    && useradd --system --uid 1001 --gid bot --no-create-home bot

ENV PATH="/app/.venv/bin:${PATH}" \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

WORKDIR /app

COPY --from=builder --chown=bot:bot /app/.venv /app/.venv
COPY --chown=bot:bot src ./src
COPY --chown=bot:bot migrations ./migrations
COPY --chown=bot:bot alembic.ini ./alembic.ini

USER bot

ENTRYPOINT ["python", "-m", "trading_bot"]
