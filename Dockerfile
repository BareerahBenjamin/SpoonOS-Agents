FROM node:22-bookworm-slim AS frontend
WORKDIR /build
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci --no-audit --no-fund
COPY frontend/index.html frontend/tsconfig.json frontend/vite.config.ts ./
COPY frontend/src ./src
RUN npm run build

FROM python:3.12-slim-bookworm AS dependencies
WORKDIR /app
ENV UV_PYTHON_DOWNLOADS=never \
    UV_LINK_MODE=copy \
    UV_CONCURRENT_DOWNLOADS=8
RUN python -m pip install --no-cache-dir uv==0.11.32
COPY pyproject.toml uv.lock ./
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --locked --no-default-groups --extra api --no-install-project

FROM python:3.12-slim-bookworm AS runtime
WORKDIR /app
ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    DEMO_MODE=true \
    RESEARCH_DB_PATH=/data/research.sqlite3
RUN groupadd --gid 10001 spoonos \
    && useradd --uid 10001 --gid 10001 --no-create-home spoonos \
    && install -d -o spoonos -g spoonos /data
COPY --from=dependencies /app/.venv ./.venv
COPY agents ./agents
COPY service ./service
COPY tools ./tools
COPY --from=frontend /build/dist ./frontend/dist
USER spoonos
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s \
    CMD ["python", "-c", "from urllib.request import urlopen; urlopen('http://127.0.0.1:8000/health', timeout=3).close()"]
CMD ["uvicorn", "service.app:create_app", "--factory", "--host", "0.0.0.0", "--port", "8000", "--workers", "1", "--timeout-graceful-shutdown", "10"]
