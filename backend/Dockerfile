FROM python:3.12.16-slim-trixie@sha256:5e2bdb1b0d542d5039cffb8181c65930093949194a65c365dfb1b0fe13a4fa5b

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_COMPILE_BYTECODE=0 \
    UV_LINK_MODE=copy \
    UV_PROJECT_ENVIRONMENT=/opt/venv \
    PATH="/opt/venv/bin:$PATH"

COPY --from=ghcr.io/astral-sh/uv:0.10.5 /uv /usr/local/bin/uv

# System libraries: the only app-specific block of this file.
# zlib1g is upgraded explicitly: the pinned base image lags behind Debian security fixes.
RUN apt-get update && apt-get install -y --no-install-recommends ffmpeg \
    && apt-get install -y --no-install-recommends --only-upgrade zlib1g \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Dependencies first (cached layer), exact versions from uv.lock
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev

COPY app ./app

# /data holds the sessions database (volume), owned by the unprivileged user
RUN useradd --uid 10001 --create-home --shell /usr/sbin/nologin app \
    && mkdir /data && chown app /data
USER app

EXPOSE 8000
VOLUME /data

# Workers: WEB_CONCURRENCY. Client scheme/address come from the proxy in front
# (--proxy-headers, trusted through FORWARDED_ALLOW_IPS: see docker-compose.yml).
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--timeout-keep-alive", "30", "--proxy-headers"]
