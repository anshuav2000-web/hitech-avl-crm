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

# First boot: create the schema and import the backup before the API accepts traffic.
# Re-running is safe (CREATE TABLE IF NOT EXISTS, and rows are skipped by _id), so a
# redeploy refreshes nothing but tops up anything missing.
RUN printf '%s\n' \
  '#!/bin/sh' \
  'set -e' \
  'echo "Preparing the PostgreSQL schema..."' \
  'python -m pgbootstrap || echo "WARNING: schema bootstrap failed; the API will report the error"' \
  'exec "$@"' \
  > /entrypoint.sh && chmod +x /entrypoint.sh

ENTRYPOINT ["/entrypoint.sh"]

# Production process. Never `uvicorn --reload`, and never the dev server.
CMD ["uvicorn", "server:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "2", "--proxy-headers", "--forwarded-allow-ips", "*"]