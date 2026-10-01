# syntax=docker/dockerfile:1
# ---------------------------------------------------------------------------
# CRM backend: FastAPI + uvicorn, serving the API only.
# The frontend is a separate service (see frontend/Dockerfile).
# ---------------------------------------------------------------------------
FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# Build tools are needed for any wheel without a prebuilt manylinux build, then
# removed in the same layer so they never reach the runtime image.
RUN apt-get update \
 && apt-get install -y --no-install-recommends build-essential curl \
 && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Run as an unprivileged user.
RUN useradd --create-home --shell /bin/bash crm \
 && chown -R crm:crm /app
USER crm

EXPOSE 8000

# Container health: the endpoint pings MongoDB, so a green result means the API can
# actually serve traffic, not merely that the process is alive.
HEALTHCHECK --interval=30s --timeout=5s --start-period=40s --retries=3 \
  CMD curl -fsS http://127.0.0.1:8000/health || exit 1

# Production process. Never `uvicorn --reload`, and never the dev server.
CMD ["uvicorn", "server:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "2", "--proxy-headers", "--forwarded-allow-ips", "*"]